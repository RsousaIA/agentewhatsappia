import os
import json
import time
from datetime import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
import threading
from queue import Queue
from loguru import logger
from dotenv import load_dotenv
from contextlib import contextmanager
import pytz

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
    get_evaluations_by_conversation,
    get_conversations_by_status,
    update_conversation
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

class EvaluatorAgent:
    """
    Agente responsável por avaliar a qualidade do atendimento
    com base nas conversas coletadas pelo Agente Coletor.
    """
    
    def __init__(self):
        """
        Inicializa o agente avaliador.
        """
        # Inicializa o Firebase
        init_firebase()
        self.db = get_firestore_db()
        
        self.conversation_processor = ConversationProcessor()
        self.priority_manager = PriorityManager()
        self.evaluation_manager = EvaluationManager()
        self.prompt_library = PromptLibrary()
        self.ollama = OllamaIntegration()
        
        # Fila para processamento assíncrono de avaliações
        self._evaluation_queue = Queue()
        
        # Registra thread de processamento
        self._processing_thread = None
        self._running = False
        
        # Thread para verificação periódica de conversas a serem avaliadas
        self._verification_thread = None
        
        self._evaluation_locks = {}  # Dicionário para armazenar locks por conversa
        self._lock = threading.Lock()  # Lock para operações no dicionário de locks
        self._evaluation_timeout = 300  # 5 minutos em segundos
        self._evaluation_start_times = {}  # Dicionário para armazenar tempos de início
        self._failed_evaluations = {}  # Dicionário para armazenar tentativas falhas
        self._max_retries = 3  # Número máximo de tentativas
        self._retry_delay = 60  # Delay entre tentativas em segundos
        
        self.running = False
        self.last_evaluation_time = time.time()
        
        # Inicia thread de avaliação
        self.evaluation_thread = None
        
        logger.info("Agente Avaliador inicializado")
    
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
        
        # Iniciar thread de verificação periódica
        self._verification_thread = threading.Thread(
            target=self._periodic_verification,
            daemon=True
        )
        self._verification_thread.start()
        
        # Inicia thread de avaliação
        self.evaluation_thread = threading.Thread(target=self._evaluate_conversations)
        self.evaluation_thread.daemon = True
        self.evaluation_thread.start()
        
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
        
        if self.evaluation_thread:
            self.evaluation_thread.join()
        
        logger.info("Agente Avaliador parado")
    
    def evaluate_conversation(self, conversation_id: str):
        """
        Adiciona uma conversa à fila para avaliação.
        
        Args:
            conversation_id: ID da conversa a ser avaliada
        """
        self._evaluation_queue.put(conversation_id)
        logger.info(f"Conversa {conversation_id} adicionada à fila de avaliação")
    
    def _periodic_verification(self):
        """
        Executa verificações periódicas de conversas e solicitações.
        """
        while self._running:
            try:
                # Verificar timeouts
                self._check_evaluation_timeouts()
                
                # Verificar conversas encerradas não avaliadas
                self._check_for_pending_evaluations()
                
                # Verificar solicitações pendentes e prazos
                self._check_pending_requests()
                
                # Verificar conversas reabertas
                self._check_reopened_conversations()
                
                # Aguardar até o próximo intervalo
                for _ in range(VERIFICATION_INTERVAL_MINUTES * 60):
                    if not self._running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro na verificação periódica: {e}")
                time.sleep(60)  # Esperar 1 minuto em caso de erro
    
    def _check_for_pending_evaluations(self):
        """
        Verifica se há conversas encerradas que ainda não foram avaliadas.
        """
        try:
            # Buscar conversas encerradas sem avaliação
            conversations = get_conversations(status='CLOSED')
            
            # Filtrar conversas sem avaliação
            conversations_to_evaluate = []
            for conversation in conversations:
                conversation_id = conversation.get('id')
                evaluations = get_evaluations_by_conversation(conversation_id)
                if not evaluations:
                    conversations_to_evaluate.append(conversation)
            
            # Ordenar conversas por prioridade
            conversations_ordered = self.priority_manager.sort_conversations_by_priority(conversations_to_evaluate)
            
            # Adicionar à fila na ordem de prioridade
            for conversation in conversations_ordered:
                lock = self._get_conversation_lock(conversation['id'])
                if not lock.locked():
                    self._evaluation_queue.put(conversation['id'])
                    logger.info(f"Conversa {conversation['id']} adicionada à fila de avaliação")
                    
        except Exception as e:
            logger.error(f"Erro ao verificar avaliações pendentes: {e}")
    
    def _check_pending_requests(self):
        """
        Verifica solicitações pendentes e atualiza status com base nos prazos.
        """
        try:
            # Buscar solicitações pendentes
            solicitacoes = get_solicitacoes_by_status('PENDING')
            
            now = datetime.now()
            
            for solicitacao in solicitacoes:
                if solicitacao.get('prazo_prometido') and solicitacao['prazo_prometido'] < now:
                    # Prazo expirado, marcar como atrasada
                    update_conversation_status(solicitacao['conversation_id'], 'DELAYED')
                    
                    # Verificar se a conversa relacionada tem avaliação
                    evaluations = get_evaluations_by_conversation(solicitacao['conversation_id'])
                    if evaluations and evaluations[0].get('status') != 'NOT_EVALUATED':
                        # Marcar para reavaliação
                        self.evaluate_conversation(solicitacao['conversation_id'])
            
        except Exception as e:
            logger.error(f"Erro ao verificar solicitações pendentes: {e}")
    
    def _check_reopened_conversations(self):
        """
        Verifica conversas que foram reabertas e atualiza suas avaliações.
        """
        try:
            # Buscar conversas reabertas
            conversations = get_conversations(status='OPEN')
            
            for conversation in conversations:
                if conversation.get('reopen_count', 0) > 0:
                    # Verificar se já existe avaliação
                    evaluations = get_evaluations_by_conversation(conversation['id'])
                    
                    if evaluations and evaluations[0].get('status') != 'NOT_EVALUATED':
                        # Marcar para reavaliação
                        self.evaluate_conversation(conversation['id'])
                        
        except Exception as e:
            logger.error(f"Erro ao verificar conversas reabertas: {e}")
    
    def _process_evaluation_queue(self):
        """
        Processa a fila de avaliações de forma assíncrona.
        """
        while self._running:
            try:
                # Obter próxima conversa da fila
                conversation_id = self._evaluation_queue.get(timeout=1)
                
                # Verificar se a conversa já está sendo avaliada
                lock = self._get_conversation_lock(conversation_id)
                if lock.locked():
                    logger.warning(f"Conversa {conversation_id} já está sendo avaliada")
                    self._evaluation_queue.put(conversation_id)  # Recolocar na fila
                    continue
                
                # Adquirir lock e registrar tempo de início
                with lock:
                    self._evaluation_start_times[conversation_id] = time.time()
                    
                    try:
                        # Avaliar a conversa
                        self._evaluate_conversation(conversation_id)
                        
                        # Limpar registros de falhas se houver sucesso
                        if conversation_id in self._failed_evaluations:
                            del self._failed_evaluations[conversation_id]
                            
                    except Exception as e:
                        logger.error(f"Erro ao avaliar conversa {conversation_id}: {e}")
                        
                        # Registrar falha
                        if conversation_id not in self._failed_evaluations:
                            self._failed_evaluations[conversation_id] = 0
                        self._failed_evaluations[conversation_id] += 1
                        
                        # Recolocar na fila se ainda houver tentativas
                        if self._failed_evaluations[conversation_id] < self._max_retries:
                            time.sleep(self._retry_delay)
                            self._evaluation_queue.put(conversation_id)
                        else:
                            logger.error(f"Conversa {conversation_id} falhou após {self._max_retries} tentativas")
                            
                    finally:
                        # Limpar registros
                        if conversation_id in self._evaluation_start_times:
                            del self._evaluation_start_times[conversation_id]
                            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no processamento da fila: {e}")
                time.sleep(1)
    
    def _evaluate_conversation(self, conversation_id: str):
        """
        Avalia uma conversa específica e atualiza suas métricas.
        
        Args:
            conversation_id: ID da conversa a ser avaliada
        """
        try:
            # Buscar conversa e suas mensagens
            conversation = get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversa {conversation_id} não encontrada")
                return
            
            messages = get_messages_by_conversation(conversation_id)
            if not messages:
                logger.warning(f"Conversa {conversation_id} não possui mensagens")
                return
            
            # Avaliar conversa usando o EvaluationManager
            evaluation_results = self.evaluation_manager.evaluate_conversation(conversation, messages)
            
            # Salvar avaliação
            evaluation_data = {
                'conversation_id': conversation_id,
                'communication_score': evaluation_results['communication_score'],
                'technical_score': evaluation_results['technical_score'],
                'empathy_score': evaluation_results['empathy_score'],
                'professionalism_score': evaluation_results['professionalism_score'],
                'results_score': evaluation_results['results_score'],
                'emotional_score': evaluation_results['emotional_score'],
                'deadlines_score': evaluation_results['deadlines_score'],
                'final_score': evaluation_results['final_score'],
                'complaints': evaluation_results['complaints'],
                'unaddressed_requests': evaluation_results['unaddressed_requests'],
                'delays': evaluation_results['delays'],
                'status': 'EVALUATED',
                'evaluated_at': evaluation_results['evaluated_at']
            }
            
            save_evaluation(evaluation_data)
            
            # Atualizar métricas consolidadas
            consolidated_data = {
                'conversation_id': conversation_id,
                'average_response_time': evaluation_results['deadlines_score'],
                'service_quality': evaluation_results['technical_score'],
                'customer_satisfaction': evaluation_results['empathy_score'],
                'reopen_count': conversation.get('reopen_count', 0),
                'nps': self._calculate_nps(evaluation_results['final_score'])
            }
            
            save_consolidated_attendance(consolidated_data)
            
            logger.info(f"Conversa {conversation_id} avaliada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa {conversation_id}: {e}")
            raise
    
    def _calculate_nps(self, satisfacao: float) -> int:
        """
        Calcula o NPS (Net Promoter Score) baseado na satisfação do cliente.
        
        Args:
            satisfacao: Score de satisfação entre 0 e 1
            
        Returns:
            NPS entre 0 e 10
        """
        # Converter satisfação (0-1) para NPS (0-10)
        return int(satisfacao * 10)
    
    def _get_conversation_lock(self, conversation_id: str) -> threading.Lock:
        """
        Obtém ou cria um lock para uma conversa específica.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Lock da conversa
        """
        with self._lock:
            if conversation_id not in self._evaluation_locks:
                self._evaluation_locks[conversation_id] = threading.Lock()
            return self._evaluation_locks[conversation_id]
    
    def _check_evaluation_timeouts(self):
        """
        Verifica e limpa avaliações que excederam o tempo limite.
        """
        now = time.time()
        with self._lock:
            for conversation_id, start_time in list(self._evaluation_start_times.items()):
                if now - start_time > self._evaluation_timeout:
                    logger.warning(f"Timeout na avaliação da conversa {conversation_id}")
                    if conversation_id in self._evaluation_locks:
                        del self._evaluation_locks[conversation_id]
                    if conversation_id in self._evaluation_start_times:
                        del self._evaluation_start_times[conversation_id]

    def _evaluate_conversations(self):
        """
        Thread que avalia as conversas periodicamente.
        """
        while self._running:
            try:
                current_time = time.time()
                
                if (current_time - self.last_evaluation_time) >= EVALUATION_INTERVAL:
                    # Obtém conversas finalizadas não avaliadas
                    closed_conversations = get_conversations_by_status("CLOSED")
                    
                    for conv in closed_conversations:
                        conversation_id = conv.get('id')
                        
                        # Verifica se já foi avaliada
                        evaluations = get_evaluations_by_conversation(conversation_id)
                        if not evaluations:
                            # Obtém mensagens da conversa
                            messages = get_messages_by_conversation(conversation_id)
                            
                            if messages:
                                # Avalia a conversa
                                evaluation = self.conversation_processor.evaluate_conversation(messages)
                                
                                # Salva avaliação
                                evaluation_data = {
                                    'conversation_id': conversation_id,
                                    'data_avaliacao': datetime.now(),
                                    'reclamacoes': evaluation.get('complaints', []),
                                    'nota_comunicacao_clara': evaluation.get('communication_score'),
                                    'nota_conhecimento_tecnico': evaluation.get('technical_score'),
                                    'nota_empatia_cordialidade': evaluation.get('empathy_score'),
                                    'nota_profissionalismo_etica': evaluation.get('professionalism_score'),
                                    'nota_orientacao_resultados': evaluation.get('results_score'),
                                    'nota_inteligencia_emocional': evaluation.get('emotional_intelligence_score'),
                                    'nota_cumprimento_prazos': evaluation.get('deadlines_score'),
                                    'nota_geral': evaluation.get('overall_score'),
                                    'zerou_por_cordialidade': evaluation.get('failed_empathy', False),
                                    'detalhes_criticos': evaluation.get('critical_details')
                                }
                                save_evaluation(evaluation_data)
                                
                                # Atualiza conversa com notas
                                update_data = {
                                    'nota_geral': evaluation.get('overall_score'),
                                    'ultima_avaliacao': datetime.now()
                                }
                                update_conversation(conversation_id, update_data)
                                
                                logger.info(f"Conversa {conversation_id} avaliada com sucesso")
                    
                    self.last_evaluation_time = current_time
                
                time.sleep(60)  # Verifica a cada minuto
                
            except Exception as e:
                logger.error(f"Erro na avaliação de conversas: {e}")
                time.sleep(RETRY_DELAY)

    def _evaluate_single_conversation(self, conversation: Dict[str, Any]):
        """
        Avalia uma única conversa.
        
        Args:
            conversation: Dados da conversa
        """
        try:
            conversation_id = conversation.get('id')
            
            # Obtém todas as mensagens da conversa
            messages = get_messages_by_conversation(conversation_id)
            
            # Obtém todas as solicitações da conversa
            requests = get_requests_by_conversation(conversation_id)
            
            # Gera o prompt de avaliação
            prompt = self.prompt_library.get_evaluation_prompt(conversation, messages, requests)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            evaluation = {
                'comunicacao_nota': float(lines[0].split(': ')[1].strip()),
                'conhecimento_nota': float(lines[1].split(': ')[1].strip()),
                'empatia_nota': float(lines[2].split(': ')[1].strip()),
                'profissionalismo_nota': float(lines[3].split(': ')[1].strip()),
                'resultados_nota': float(lines[4].split(': ')[1].strip()),
                'emocional_nota': float(lines[5].split(': ')[1].strip()),
                'cumprimento_prazos_nota': float(lines[6].split(': ')[1].strip()),
                'nota_geral': float(lines[7].split(': ')[1].strip()),
                'reclamacoes_detectadas': [r.strip() for r in lines[8].split(': ')[1].split(',')],
                'solicitacoes_nao_atendidas': [s.strip() for s in lines[9].split(': ')[1].split(',')],
                'solicitacoes_atrasadas': [s.strip() for s in lines[10].split(': ')[1].split(',')],
                'pontos_positivos': [p.strip() for p in lines[11].split(': ')[1].split(',')],
                'pontos_negativos': [p.strip() for p in lines[12].split(': ')[1].split(',')],
                'sugestoes_melhoria': [s.strip() for s in lines[13].split(': ')[1].split(',')]
            }
            
            # Salva a avaliação
            save_evaluation(conversation_id, evaluation)
            
            # Atualiza status da conversa
            update_conversation(conversation_id, {'avaliada': True})
            
            logger.info(f"Conversa {conversation_id} avaliada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa {conversation.get('id')}: {e}")

    def _consolidate_single_attendance(self, conversation: Dict[str, Any]):
        """
        Consolida um único atendimento.
        
        Args:
            conversation: Dados da conversa
        """
        try:
            conversation_id = conversation.get('id')
            
            # Obtém todas as mensagens da conversa
            messages = get_messages_by_conversation(conversation_id)
            
            # Obtém a avaliação da conversa
            evaluation = get_requests_by_conversation(conversation_id)
            
            # Gera o prompt de resumo
            prompt = self.prompt_library.get_summary_prompt(conversation, messages, evaluation)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            summary = {
                'resumo': lines[0].split(': ')[1].strip(),
                'problema_principal': lines[1].split(': ')[1].strip(),
                'solucao_aplicada': lines[2].split(': ')[1].strip(),
                'status_final': lines[3].split(': ')[1].strip(),
                'proximos_passos': [p.strip() for p in lines[4].split(': ')[1].split(',')],
                'tags': [t.strip() for t in lines[5].split(': ')[1].split(',')]
            }
            
            # Salva o resumo consolidado
            save_consolidated_attendance(conversation_id, summary)
            
            logger.info(f"Atendimento {conversation_id} consolidado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao consolidar atendimento {conversation.get('id')}: {e}")

def get_evaluator_agent():
    """
    Retorna a instância global do agente avaliador.
    
    Returns:
        Instância do agente avaliador
    """
    global _evaluator_agent
    if not hasattr(get_evaluator_agent, '_evaluator_agent'):
        get_evaluator_agent._evaluator_agent = EvaluatorAgent()
    return get_evaluator_agent._evaluator_agent 