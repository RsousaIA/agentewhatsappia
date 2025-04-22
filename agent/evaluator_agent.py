import os
import json
import time
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
import threading
import queue
from queue import Queue, PriorityQueue
from loguru import logger
from dotenv import load_dotenv
from contextlib import contextmanager
import pytz
import traceback

from database.firebase_db import (
    init_firebase,
    get_firestore_db,
    get_conversation,
    get_messages_by_conversation,
    get_solicitacoes_by_status,
    save_evaluation,
    save_consolidated_attendance,
    update_conversation_status,
    get_conversations,
    update_conversation,
    get_conversations_by_tag,
    get_conversations_by_status
)
from .conversation_processor import ConversationProcessor
from .priority_manager import PriorityManager
from .evaluation_manager import EvaluationManager
from .prompts_library import PromptLibrary
from .ollama_integration import OllamaIntegration

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
VERIFICATION_INTERVAL_MINUTES = int(os.getenv("VERIFICATION_INTERVAL_MINUTES", "10"))
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
EVALUATION_INTERVAL = int(os.getenv("EVALUATION_INTERVAL", "3600"))  # 1 hora em segundos

# Configuração de logs específica para o agente avaliador
logger.add(
    "logs/evaluator_agent.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    filter=lambda record: "evaluator_agent" in record["extra"]
)

class EvaluatorAgent:
    """
    Agente responsável por avaliar a qualidade do atendimento
    com base nas conversas coletadas pelo Agente Coletor.
    """
    
    def __init__(self, notification_queue: Optional[Queue] = None):
        """
        Inicializa o agente avaliador.
        
        Args:
            notification_queue: Fila opcional para receber notificações de conversas encerradas
        """
        # Inicializa o Firebase
        init_firebase()
        self.db = get_firestore_db()
        
        self.conversation_processor = ConversationProcessor()
        self.priority_manager = PriorityManager()
        self.evaluation_manager = EvaluationManager()
        self.prompt_library = PromptLibrary()
        self.ollama = OllamaIntegration()
        
        # Fila para receber notificações do agente coletor
        self.notification_queue = notification_queue
        
        # Fila para processamento assíncrono de avaliações com prioridade
        self._evaluation_queue = PriorityQueue()
        
        # Registra threads de processamento
        self._processing_thread = None
        self._running = False
        
        # Thread para verificação periódica de conversas a serem avaliadas (fallback)
        self._verification_thread = None
        
        # Thread para processamento de notificações
        self._notification_thread = None
        
        self._evaluation_locks = {}  # Dicionário para armazenar locks por conversa
        self._lock = threading.Lock()  # Lock para operações no dicionário de locks
        self._evaluation_timeout = 300  # 5 minutos em segundos
        self._evaluation_start_times = {}  # Dicionário para armazenar tempos de início
        self._failed_evaluations = {}  # Dicionário para armazenar tentativas falhas
        self._max_retries = 3  # Número máximo de tentativas
        self._retry_delay = 60  # Delay entre tentativas em segundos
        
        self.last_evaluation_time = time.time()
        
        self.logger = logger.bind(evaluator_agent=True)
        self.logger.info("Agente Avaliador inicializado")
    
    def start(self):
        """
        Inicia o agente avaliador.
        """
        if self._running:
            logger.warning("Agente Avaliador já está em execução")
            return
        
        self._running = True
        
        # Iniciar thread de processamento de avaliações
        self._processing_thread = threading.Thread(
            target=self._process_evaluation_queue, 
            daemon=True
        )
        self._processing_thread.start()
        
        # Iniciar thread de verificação periódica (fallback)
        self._verification_thread = threading.Thread(
            target=self._periodic_verification,
            daemon=True
        )
        self._verification_thread.start()
        
        # Iniciar thread de processamento de notificações (se a fila estiver disponível)
        if self.notification_queue:
            self._notification_thread = threading.Thread(
                target=self._process_notifications,
                daemon=True
            )
            self._notification_thread.start()
        
        logger.info("Agente Avaliador iniciado")
    
    def stop(self):
        """
        Para o agente avaliador.
        """
        if not self._running:
            logger.warning("Agente Avaliador não está em execução")
            return
        
        self._running = False
        
        if self._processing_thread:
            self._processing_thread.join(timeout=10)
        
        if self._verification_thread:
            self._verification_thread.join(timeout=10)
        
        if self._notification_thread:
            self._notification_thread.join(timeout=10)
        
        logger.info("Agente Avaliador parado")
    
    def evaluate_conversation(self, conversation_id: str, priority: int = 5):
        """
        Adiciona uma conversa à fila para avaliação com determinada prioridade.
        
        Args:
            conversation_id: ID da conversa a ser avaliada
            priority: Prioridade da avaliação (1-10, sendo 1 a mais alta)
        """
        self._evaluation_queue.put((priority, time.time(), conversation_id))
        logger.info(f"Conversa {conversation_id} adicionada à fila de avaliação com prioridade {priority}")
    
    def _process_notifications(self):
        """
        Processa notificações recebidas do Agente Coletor.
        Este método monitora a fila de notificações e processa eventos de encerramento de conversas.
        """
        logger.info("Iniciando processamento de notificações")
        
        while self._running:
            try:
                # Tenta obter uma notificação da fila com timeout
                try:
                    notification = self.notification_queue.get(timeout=1.0)
                    self._handle_notification(notification)
                    self.notification_queue.task_done()
                except queue.Empty:
                    # Nenhuma notificação na fila, continuar
                    pass
            except Exception as e:
                logger.error(f"Erro no processamento de notificações: {e}")
                time.sleep(1)  # Pausa breve para evitar loop infinito em caso de erro
    
    def _handle_notification(self, notification: Dict[str, Any]) -> None:
        """
        Processa uma notificação da fila de notificações.
        
        O parâmetro notification é um dicionário com a seguinte estrutura esperada:
        {
            'event': str,  # Tipo do evento (ex: 'conversation_closed')
            'conversation_id': str,  # ID da conversa relacionada
            'data': dict,  # Dados adicionais (opcional)
        }
        
        Args:
            notification: Dicionário contendo informações sobre a notificação
        """
        try:
            # Validação básica da notificação
            if not isinstance(notification, dict):
                logger.warning(f"Notificação inválida recebida: {notification} (não é um dicionário)")
                return
            
            if 'event' not in notification:
                logger.warning(f"Notificação sem evento recebida: {notification}")
                return
            
            if 'conversation_id' not in notification:
                logger.warning(f"Notificação sem ID de conversa recebida: {notification}")
                return
            
            event = notification['event']
            conversation_id = notification['conversation_id']
            
            logger.info(f"Processando notificação: {event} para conversa {conversation_id}")
            
            if event == 'conversation_closed':
                try:
                    # Obter detalhes da conversa para avaliação
                    conversation = get_conversation(conversation_id)
                    
                    if not conversation:
                        logger.warning(f"Não foi possível obter a conversa {conversation_id} para avaliação")
                        return
                    
                    # Calcular prioridade de avaliação
                    priority = self._calculate_evaluation_priority(conversation)
                    
                    # Adicionar à fila de avaliação
                    self.evaluate_conversation(conversation_id, priority)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar notificação de conversa encerrada: {e}")
                    traceback.print_exc()
            else:
                logger.warning(f"Evento desconhecido recebido: {event}")
                
        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}")
            traceback.print_exc()
    
    def _calculate_evaluation_priority(self, conversation: Dict[str, Any]) -> int:
        """
        Calcula a prioridade de avaliação para uma conversa.
        
        Args:
            conversation: Dados da conversa
            
        Returns:
            int: Prioridade calculada (1-10, sendo 1 a mais alta)
        """
        try:
            # Implementação básica de priorização
            # Em uma implementação real, consideraríamos mais fatores
            
            # Verificar se há reclamações
            if conversation.get('has_complaint', False):
                return 1  # Prioridade máxima
            
            # Verificar se é uma conversa reaberta
            if conversation.get('reopened', False):
                return 2
            
            # Verificar se tem solicitações pendentes
            if conversation.get('pending_requests', []):
                return 3
            
            # Prioridade padrão
            return 5
            
        except Exception as e:
            logger.error(f"Erro ao calcular prioridade: {e}")
            return 5  # Prioridade média em caso de erro
    
    def _periodic_verification(self):
        """
        Verifica periodicamente se há conversas que precisam ser avaliadas.
        Este é um mecanismo de fallback para garantir que nenhuma conversa seja esquecida.
        """
        logger.info("Iniciando verificação periódica de conversas")
        
        while self._running:
            try:
                # Verificar conversas pendentes de avaliação
                self._check_for_pending_evaluations()
                
                # Verificar solicitações pendentes
                self._check_pending_requests()
                
                # Verificar conversas reabertas
                self._check_reopened_conversations()
                
                # Aguardar próximo ciclo
                time.sleep(VERIFICATION_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Erro na verificação periódica: {e}")
                time.sleep(60)  # Pausa maior em caso de erro
    
    def _check_for_pending_evaluations(self):
        """
        Verifica se há conversas encerradas que ainda não foram avaliadas.
        """
        try:
            # Buscar conversas encerradas
            # Considera diferentes variações de status de encerramento
            status_list = ['encerrada', 'finalizada', 'closed']
            
            closed_conversations = []
            for status in status_list:
                try:
                    conversations = get_conversations_by_status(status)
                    if conversations:
                        closed_conversations.extend(conversations)
                except Exception as status_error:
                    logger.warning(f"Erro ao buscar conversas com status '{status}': {status_error}")
            
            # Alternativa: buscar todas e filtrar
            if not closed_conversations:
                all_conversations = get_conversations(limit=100)
                closed_conversations = [
                    conv for conv in all_conversations 
                    if conv.get('status', '').lower() in status_list
                ]
            
            logger.info(f"Encontradas {len(closed_conversations)} conversas encerradas para verificação")
            
            for conversation in closed_conversations:
                conversation_id = conversation.get('id')
                
                if not conversation_id:
                    continue
                
                # Verificar se já foi avaliada
                is_evaluated = conversation.get('avaliada', False)
                
                if not is_evaluated:
                    # Não tem avaliação, adicionar à fila
                    priority = self._calculate_evaluation_priority(conversation)
                    self.evaluate_conversation(conversation_id, priority)
                    logger.info(f"Conversa {conversation_id} adicionada à fila de avaliação (verificação periódica)")
                
        except Exception as e:
            logger.error(f"Erro ao verificar avaliações pendentes: {e}")
            traceback.print_exc()
    
    def _check_pending_requests(self):
        """
        Verifica solicitações pendentes e marca conversas relacionadas para reavaliação.
        """
        try:
            # Buscar solicitações pendentes
            solicitacoes = get_solicitacoes_by_status('PENDING')
            
            now = datetime.datetime.now()
            
            for solicitacao in solicitacoes:
                # Verificar se está atrasada
                prazo = solicitacao.get('prazo')
                if prazo and datetime.datetime.fromisoformat(prazo) < now:
                    # Marcar conversa como atrasada
                    update_conversation_status(solicitacao['conversation_id'], 'atrasada')
                    
                    # Verificar se a conversa relacionada tem avaliação
                    evaluations = get_evaluations_by_conversation(solicitacao['conversation_id'])
                    if evaluations and evaluations[0].get('status') != 'NOT_EVALUATED':
                        # Marcar para reavaliação com alta prioridade
                        self.evaluate_conversation(solicitacao['conversation_id'], 2)
            
        except Exception as e:
            logger.error(f"Erro ao verificar solicitações pendentes: {e}")
    
    def _check_reopened_conversations(self):
        """
        Verifica conversas que foram reabertas e atualiza suas avaliações.
        """
        try:
            # Buscar conversas reabertas por status ou flag de reabertura
            try:
                reopened_conversations = get_conversations_by_status('reaberta')
            except Exception:
                reopened_conversations = []
            
            # Alternativa: buscar todas e filtrar por flag de reabertura
            if not reopened_conversations:
                all_conversations = get_conversations(limit=100)
                reopened_conversations = [
                    conv for conv in all_conversations 
                    if conv.get('status', '').lower() == 'reaberta' or 
                    conv.get('foiReaberta', False) == True or
                    conv.get('reopened', False) == True
                ]
            
            logger.info(f"Encontradas {len(reopened_conversations)} conversas reabertas")
            
            for conversation in reopened_conversations:
                conversation_id = conversation.get('id')
                if not conversation_id:
                    continue
                
                # Verificar se já existe lock para esta conversa
                lock = self._get_conversation_lock(conversation_id)
                if not lock.locked():
                    # Marcar para reavaliação com alta prioridade
                    self.evaluate_conversation(conversation_id, 1)  # Prioridade máxima
                    logger.info(f"Conversa reaberta {conversation_id} adicionada à fila para reavaliação")
                else:
                    logger.debug(f"Conversa reaberta {conversation_id} já está sendo avaliada")
                        
        except Exception as e:
            logger.error(f"Erro ao verificar conversas reabertas: {e}")
            traceback.print_exc()
    
    def _process_evaluation_queue(self):
        """
        Processa a fila de avaliações continuamente.
        Este método é executado em uma thread separada.
        """
        logger.info("Iniciando processamento da fila de avaliações")
        
        while self._running:
            try:
                # Obter próximo item da fila de avaliações com timeout
                try:
                    priority, timestamp, conversation_id = self._evaluation_queue.get(timeout=2.0)
                    logger.info(f"Processando avaliação da conversa {conversation_id} (prioridade: {priority})")
                    
                    # Verificar se já existe um lock para esta conversa
                    conversation_lock = self._get_conversation_lock(conversation_id)
                    
                    # Tentar adquirir o lock para a conversa (sem bloqueio)
                    if conversation_lock.acquire(blocking=False):
                        try:
                            # Registrar início da avaliação (para timeout)
                            with self._lock:
                                self._evaluation_start_times[conversation_id] = time.time()
                            
                            # Registrar tentativa
                            retry_count = self._failed_evaluations.get(conversation_id, 0)
                            
                            # Verificar se excedeu o número máximo de tentativas
                            if retry_count >= self._max_retries:
                                logger.warning(f"Número máximo de tentativas excedido para conversa {conversation_id}")
                                # Limpar registros
                                with self._lock:
                                    if conversation_id in self._failed_evaluations:
                                        del self._failed_evaluations[conversation_id]
                                    if conversation_id in self._evaluation_start_times:
                                        del self._evaluation_start_times[conversation_id]
                            else:
                                # Processar avaliação
                                start_time = time.time()
                                try:
                                    result = self._evaluate_conversation(conversation_id, priority)
                                    
                                    if result:
                                        # Avaliação bem-sucedida, limpar registros
                                        with self._lock:
                                            if conversation_id in self._failed_evaluations:
                                                del self._failed_evaluations[conversation_id]
                                            
                                        processing_time = time.time() - start_time
                                        logger.info(f"Avaliação da conversa {conversation_id} concluída com sucesso em {processing_time:.2f}s")
                                    else:
                                        # Avaliação retornou None, algo deu errado
                                        self._failed_evaluations[conversation_id] = retry_count + 1
                                        logger.warning(f"Avaliação da conversa {conversation_id} não foi concluída (tentativa {retry_count + 1}/{self._max_retries})")
                                        
                                        # Recolocar na fila com atraso se não excedeu o limite
                                        if retry_count < self._max_retries - 1:
                                            delay = self._retry_delay * (retry_count + 1)
                                            threading.Timer(
                                                delay, 
                                                lambda: self.evaluate_conversation(conversation_id, priority)
                                            ).start()
                                            logger.info(f"Agendando nova tentativa para conversa {conversation_id} em {delay}s")
                                    
                                except Exception as eval_error:
                                    # Incrementar contador de falhas
                                    self._failed_evaluations[conversation_id] = retry_count + 1
                                    
                                    # Registrar erro
                                    logger.error(f"Falha na avaliação da conversa {conversation_id} (tentativa {retry_count + 1}/{self._max_retries}): {eval_error}")
                                    traceback.print_exc()
                                    
                                    # Recolocar na fila com atraso se não excedeu o limite
                                    if retry_count < self._max_retries - 1:
                                        # Programar nova tentativa com delay progressivo
                                        delay = self._retry_delay * (retry_count + 1)
                                        threading.Timer(
                                            delay, 
                                            lambda: self.evaluate_conversation(conversation_id, priority)
                                        ).start()
                                        logger.info(f"Agendando nova tentativa para conversa {conversation_id} em {delay}s")
                        finally:
                            # Limpar registro de tempo e liberar o lock
                            with self._lock:
                                if conversation_id in self._evaluation_start_times:
                                    del self._evaluation_start_times[conversation_id]
                            conversation_lock.release()
                            
                            # Marcar tarefa como concluída
                            self._evaluation_queue.task_done()
                    else:
                        # Não conseguiu o lock, recolocar na fila
                        logger.debug(f"Conversa {conversation_id} já está sendo avaliada. Recolocando na fila.")
                        self._evaluation_queue.put((priority, timestamp, conversation_id))
                        self._evaluation_queue.task_done()
                        time.sleep(0.5)  # Pequena pausa para evitar ciclo rápido
                            
                except queue.Empty:
                    # Verificar timeouts em avaliações em andamento
                    self._check_evaluation_timeouts()
                    time.sleep(0.1)  # Pequena pausa para evitar uso intensivo de CPU
                    
            except Exception as e:
                logger.error(f"Erro no processamento da fila de avaliações: {e}")
                traceback.print_exc()
                time.sleep(1)  # Pausa para evitar loop infinito em caso de erro
    
    def _evaluate_conversation(self, conversation_id: str, priority: int = 1) -> Dict[str, any]:
        """
        Avalia uma conversa específica.
        
        Args:
            conversation_id: ID da conversa
            priority: Prioridade da avaliação
            
        Returns:
            Dict com os resultados da avaliação
        """
        try:
            # Verifica se a conversa existe e tem ID válido
            conversation = get_conversation(conversation_id)
            if not conversation or 'id' not in conversation:
                logger.error(f"Conversa {conversation_id} não encontrada ou sem ID")
                return None
                
            # Obtém o lock para esta conversa
            lock = self._get_conversation_lock(conversation_id)
            
            with lock:
                # Registra o início da avaliação
                self._evaluation_start_times[conversation_id] = time.time()
                
                try:
                    # Obtém as mensagens da conversa
                    messages = get_messages_by_conversation(conversation_id)
                    if not messages:
                        logger.warning(f"Nenhuma mensagem encontrada para a conversa {conversation_id}")
                        return None
                    
                    # Avalia a conversa
                    evaluation = self.evaluation_manager.evaluate_conversation(conversation, messages)
                    
                    # Consolida os dados
                    if evaluation:
                        self._consolidate_single_attendance(conversation)
                    
                    return evaluation
                    
                finally:
                    # Limpa o registro de tempo
                    if conversation_id in self._evaluation_start_times:
                        del self._evaluation_start_times[conversation_id]
                    
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa {conversation_id}: {e}")
            traceback.print_exc()
            return None
    
    def _calculate_nps(self, satisfacao: float) -> int:
        """
        Calcula o NPS (Net Promoter Score) com base na satisfação.
        
        Args:
            satisfacao: Nota de satisfação (0-10)
            
        Returns:
            int: NPS calculado (-100 a 100)
        """
        try:
            # Converter para escala 0-10 se necessário
            if satisfacao > 1:
                satisfacao = satisfacao / 10
            
            # Classificar em Detratores (0-6), Neutros (7-8) e Promotores (9-10)
            if satisfacao >= 0.9:  # 9-10
                return 100  # Promotor
            elif satisfacao >= 0.7:  # 7-8
                return 0  # Neutro
            else:  # 0-6
                return -100  # Detrator
                
        except Exception as e:
            logger.error(f"Erro ao calcular NPS: {e}")
            return 0
    
    def _consolidate_single_attendance(self, conversation: Dict[str, Any]) -> bool:
        """
        Consolida métricas de um único atendimento.
        
        Args:
            conversation: Dados da conversa
            
        Returns:
            bool: True se consolidado com sucesso, False caso contrário
        """
        try:
            conversation_id = conversation.get('id')
            if not conversation_id:
                logger.error("Não foi possível consolidar: conversa sem ID")
                return False
            
            # Preparar dados consolidados
            consolidated_data = {
                'conversation_id': conversation_id,
                'timestamp': datetime.datetime.now().isoformat(),
                'status': conversation.get('status', 'desconhecido'),
                'client_name': conversation.get('cliente', {}).get('nome', 'Desconhecido'),
                'start_time': conversation.get('dataHoraInicio', ''),
                'end_time': conversation.get('dataHoraFim', ''),
                'duration_seconds': self._calculate_conversation_duration(conversation),
                'message_count': conversation.get('total_mensagens', 0),
                'resolved': conversation.get('status', '') in ['encerrada', 'finalizada', 'closed'],
                'reopened': conversation.get('reaberta', False),
                'reopen_count': conversation.get('contagem_reaberturas', 0)
            }
            
            # Tentar salvar
            try:
                save_consolidated_attendance(consolidated_data)
                logger.info(f"Métricas da conversa {conversation_id} consolidadas com sucesso")
                return True
            except Exception as save_error:
                logger.error(f"Erro ao salvar métricas consolidadas: {save_error}")
                return False
            
        except Exception as e:
            logger.error(f"Erro ao consolidar métricas: {e}")
            return False
    
    def _calculate_conversation_duration(self, conversation: Dict[str, Any]) -> int:
        """
        Calcula a duração de uma conversa em segundos.
        
        Args:
            conversation: Dados da conversa
            
        Returns:
            int: Duração em segundos
        """
        try:
            start_time_str = conversation.get('dataHoraInicio')
            end_time_str = conversation.get('dataHoraFim')
            
            if not start_time_str or not end_time_str:
                return 0
                
            # Converter strings para objetos datetime
            if isinstance(start_time_str, str):
                start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            else:
                start_time = start_time_str
                
            if isinstance(end_time_str, str):
                end_time = datetime.datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            else:
                end_time = end_time_str
                
            # Calcular diferença
            duration = (end_time - start_time).total_seconds()
            return int(max(0, duration))  # Garantir valor não negativo
            
        except Exception as e:
            logger.error(f"Erro ao calcular duração da conversa: {e}")
            return 0
    
    def _get_conversation_lock(self, conversation_id: str) -> threading.Lock:
        """
        Obtém ou cria um lock para uma conversa específica.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            threading.Lock: Lock para a conversa
        """
        with self._lock:
            if conversation_id not in self._evaluation_locks:
                self._evaluation_locks[conversation_id] = threading.Lock()
            return self._evaluation_locks[conversation_id]
    
    def _check_evaluation_timeouts(self):
        """
        Verifica se há avaliações que excederam o tempo limite.
        """
        try:
            current_time = time.time()
            
            with self._lock:
                for conversation_id, start_time in list(self._evaluation_start_times.items()):
                    elapsed_time = current_time - start_time
                    
                    if elapsed_time > self._evaluation_timeout:
                        logger.warning(f"Avaliação da conversa {conversation_id} excedeu o tempo limite ({elapsed_time:.1f}s)")
                        
                        # Liberar o lock se ainda estiver bloqueado
                        lock = self._evaluation_locks.get(conversation_id)
                        if lock and lock.locked():
                            lock.release()
                            logger.info(f"Lock da conversa {conversation_id} liberado após timeout")
                        
                        # Limpar registros
                        if conversation_id in self._evaluation_start_times:
                            del self._evaluation_start_times[conversation_id]
                        
                        # Registrar falha
                        retry_count = self._failed_evaluations.get(conversation_id, 0)
                        self._failed_evaluations[conversation_id] = retry_count + 1
                        
                        # Tentar novamente se não excedeu o limite
                        if retry_count < self._max_retries:
                            logger.info(f"Agendando nova tentativa para conversa {conversation_id} após timeout")
                            self.evaluate_conversation(conversation_id, 5)  # Prioridade média
                        
        except Exception as e:
            logger.error(f"Erro ao verificar timeouts: {e}")
            traceback.print_exc()

def get_evaluator_agent(notification_queue: Optional[Queue] = None) -> EvaluatorAgent:
    """
    Obtém uma instância do agente avaliador.
    
    Args:
        notification_queue: Fila opcional para receber notificações
        
    Returns:
        EvaluatorAgent: Instância do agente
    """
    return EvaluatorAgent(notification_queue) 