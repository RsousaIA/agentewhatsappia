import os
import json
import time
import datetime
import threading
import pytz
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import timedelta
from loguru import logger
from dotenv import load_dotenv
from queue import Queue
from database.firebase_db import (
    init_firebase,
    get_firestore_db,
    save_message,
    get_conversation,
    get_messages_by_conversation,
    upload_media,
    update_conversation,
    create_conversation,
    get_conversations_by_status,
    create_request,
    update_request,
    get_requests_by_conversation,
    save_evaluation,
    save_consolidated_attendance,
    get_last_message_time,
    update_conversation_status,
    get_conversations
)
from firebase_admin import firestore
from .conversation_processor import ConversationProcessor
from .ollama_integration import OllamaIntegration
from .prompts_library import PromptLibrary

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT", "21600"))  # 6 horas em segundos
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
EVALUATION_INTERVAL = int(os.getenv("EVALUATION_INTERVAL", "3600"))  # 1 hora em segundos
CONSOLIDATION_INTERVAL = int(os.getenv("CONSOLIDATION_INTERVAL", "86400"))  # 24 horas em segundos
REOPEN_CHECK_INTERVAL = int(os.getenv("REOPEN_CHECK_INTERVAL", "300"))  # 5 minutos em segundos
DEFAULT_MESSAGES_TO_CHECK = int(os.getenv("DEFAULT_MESSAGES_TO_CHECK", "10"))  # Mensagens a verificar para encerramento

class CollectorAgent:
    """
    Agente responsável por monitorar e coletar mensagens do WhatsApp.
    """
    def __init__(self):
        """
        Inicializa o agente coletor.
        """
        self.message_queue = Queue()
        self.active_conversations = {}
        self.conversation_processor = ConversationProcessor()
        self.ollama = OllamaIntegration()
        self.prompt_library = PromptLibrary()
        self.running = False
        self.db = None
        self.last_processed_time = {}
        self.last_evaluation_time = time.time()
        self.last_consolidation_time = time.time()
        self.last_reopen_check_time = time.time()
        self.closed_conversations = {}  # Armazena conversas fechadas e seus últimos tempos de mensagem
        
        # Inicializa o Firebase
        init_firebase()
        self.db = get_firestore_db()
        
        # Inicia threads de processamento
        self.processing_thread = None
        self.cleanup_thread = None
        self.evaluation_thread = None
        self.consolidation_thread = None
        self.reopen_check_thread = None
        
    def start(self):
        """
        Inicia o agente coletor.
        """
        if self.running:
            logger.warning("Agente já está em execução")
            return
            
        self.running = True
        
        # Inicia thread de processamento de mensagens
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Inicia thread de limpeza de conversas inativas
        self.cleanup_thread = threading.Thread(target=self._cleanup_inactive_conversations)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # Inicia thread de avaliação de atendimentos
        self.evaluation_thread = threading.Thread(target=self._evaluate_conversations)
        self.evaluation_thread.daemon = True
        self.evaluation_thread.start()
        
        # Inicia thread de consolidação de atendimentos
        self.consolidation_thread = threading.Thread(target=self._consolidate_attendances)
        self.consolidation_thread.daemon = True
        self.consolidation_thread.start()
        
        # Inicia thread de verificação de reabertura
        self.reopen_check_thread = threading.Thread(target=self._check_reopened_conversations)
        self.reopen_check_thread.daemon = True
        self.reopen_check_thread.start()
        
        logger.info("Agente coletor iniciado com sucesso")
    
    def stop(self):
        """
        Para o agente coletor.
        """
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()
        if self.cleanup_thread:
            self.cleanup_thread.join()
        if self.evaluation_thread:
            self.evaluation_thread.join()
        if self.consolidation_thread:
            self.consolidation_thread.join()
        if self.reopen_check_thread:
            self.reopen_check_thread.join()
        logger.info("Agente coletor parado com sucesso")

    def process_message(self, message_data: Dict[str, Any]):
        """
        Processa uma nova mensagem recebida.
        """
        try:
            # Adiciona timestamp de processamento
            message_data['processed_at'] = firestore.SERVER_TIMESTAMP
            
            # Verifica se a conversa estava fechada
            if message_data.get('conversation_id') in self.closed_conversations:
                # Verifica se a mensagem é nova (após o fechamento)
                last_message_time = self.closed_conversations[message_data.get('conversation_id')]
                if message_data.get('timestamp', 0) > last_message_time:
                    # Verifica se a mensagem indica reabertura
                    if self._should_reopen_conversation(message_data):
                        self._reopen_conversation(message_data.get('conversation_id'), message_data.get('content', ''))
            
            # Adiciona mensagem à fila de processamento
            self.message_queue.put(message_data)
            
            logger.info(f"Mensagem {message_data.get('message_id')} adicionada à fila de processamento")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            raise

    def _should_reopen_conversation(self, message_data: Dict[str, Any]) -> bool:
        """
        Verifica se a mensagem indica reabertura da conversa.
        
        Args:
            message_data: Dados da mensagem
            
        Returns:
            True se a conversa deve ser reaberta, False caso contrário
        """
        content = message_data.get('content', '').lower()
        
        # Análise da mensagem usando ollama_integration
        analysis = self._analyze_message(content)
        
        # Verifica se a mensagem contém indicadores de reabertura
        reopen_indicators = [
            'reabrir', 'voltar', 'continuar', 'ainda preciso',
            'não resolvi', 'preciso de mais ajuda', 'ajuda',
            'olá', 'oi', 'bom dia', 'boa tarde', 'boa noite',
            'ainda está aí', 'voltei'
        ]
        
        # Verificar se é uma nova solicitação
        is_new_request = analysis.get('has_request', False) or \
                         analysis.get('intent') in ['solicitação', 'pergunta', 'ajuda']
        
        # Verificar se é uma reclamação
        is_complaint = analysis.get('is_complaint', False) or \
                       analysis.get('intent') == 'reclamação'
        
        # Reabrir se for uma nova interação significativa
        return any(indicator in content for indicator in reopen_indicators) or \
               is_new_request or is_complaint or \
               analysis.get('intent') == 'reopen_conversation'

    def _reopen_conversation(self, conversation_id: str, message: str) -> None:
        """
        Reabre uma conversa fechada.
        
        Args:
            conversation_id: ID da conversa
            message: Mensagem que causou a reabertura
        """
        try:
            # Atualiza o status da conversa para ACTIVE
            update_conversation_status(conversation_id, 'ACTIVE')
            
            # Adiciona anotação ao sistema sobre a reabertura
            save_message(conversation_id, {
                'tipo': 'sistema',
                'conteudo': 'Conversa reaberta devido a nova mensagem do cliente após encerramento',
                'remetente': 'sistema',
                'timestamp': datetime.now(),
                'metadata': {
                    'action': 'CONVERSATION_REOPENED',
                    'reason': 'Nova mensagem após período de inatividade',
                    'reopening_message': message
                }
            })
            
            # Remove dos registros de conversas fechadas
            if conversation_id in self.closed_conversations:
                del self.closed_conversations[conversation_id]
            
            logger.info(f"Conversa {conversation_id} reaberta devido a nova mensagem")
            
        except Exception as e:
            logger.error(f"Erro ao reabrir conversa {conversation_id}: {e}")

    def _check_reopened_conversations(self):
        """
        Verifica periodicamente conversas fechadas para possível reabertura.
        """
        while self.running:
            try:
                logger.debug("Verificando conversas encerradas para possível reabertura...")
                
                # Busca conversas com status CLOSED
                closed_conversations = get_conversations_by_status('CLOSED')
                
                for conv in closed_conversations:
                    conversation_id = conv.get('id')
                    
                    # Verifica se há mensagens novas após o encerramento
                    last_message_time = get_last_message_time(conversation_id)
                    closed_time = conv.get('dataHoraEncerramento')
                    
                    if last_message_time and closed_time and last_message_time > closed_time:
                        # Busca a última mensagem para verificar se deve reabrir
                        messages = get_messages_by_conversation(conversation_id, limit=1)
                        if messages and len(messages) > 0:
                            last_message = messages[0]
                            
                            # Só reabre se a última mensagem for do cliente
                            if last_message.get('remetente') == 'cliente':
                                message_data = {
                                    'content': last_message.get('conteudo', ''),
                                    'conversation_id': conversation_id,
                                    'timestamp': last_message.get('timestamp')
                                }
                                
                                if self._should_reopen_conversation(message_data):
                                    self._reopen_conversation(conversation_id, last_message.get('conteudo', ''))
                
                # Aguarda até a próxima verificação
                time.sleep(REOPEN_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Erro ao verificar conversas para reabertura: {e}")
                time.sleep(60)  # Espera 1 minuto em caso de erro

    def _process_messages(self):
        """
        Processa mensagens da fila de processamento.
        """
        while self.running:
            try:
                # Pega mensagem da fila
                message_data = self.message_queue.get()
                
                # Processa a mensagem
                self._process_single_message(message_data)
                
                # Marca a mensagem como processada
                self.message_queue.task_done()
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                time.sleep(RETRY_DELAY)

    def _process_single_message(self, message_data: Dict[str, Any]):
        """
        Processa uma única mensagem.
        
        Args:
            message_data: Dados da mensagem a ser processada
        """
        try:
            # Obtém dados da mensagem
            conversation_id = message_data.get('conversation_id')
            message_content = message_data.get('content', '')
            sender = message_data.get('sender', '')
            timestamp = message_data.get('timestamp')
            
            # Verifica se a conversa existe
            conversation = get_conversation(conversation_id)
            if not conversation:
                # Cria nova conversa se não existir
                conversation = self._create_new_conversation(message_data)
                conversation_id = conversation.get('id')
            
            # Analisa a mensagem
            analysis = self._analyze_message(message_content)
            
            # Salva a mensagem no banco
            message_doc = {
                'tipo': 'texto',
                'conteudo': message_content,
                'remetente': sender,
                'timestamp': timestamp,
                'metadata': {
                    'analysis': analysis
                }
            }
            save_message(conversation_id, message_doc)
            
            # Atualiza último tempo de mensagem
            self.last_processed_time[conversation_id] = time.time()
            
            # Verifica se há solicitações
            if analysis.get('has_request'):
                context = self._get_conversation_context(conversation_id)
                request_analysis = self._detect_requests(context, message_content)
                
                if request_analysis.get('has_request'):
                    self._create_request(conversation_id, request_analysis)
            
            # Verifica se a conversa deve ser encerrada
            if analysis.get('is_closing'):
                recent_messages = self._get_recent_messages(conversation_id)
                closure_analysis = self._should_close_conversation(recent_messages)
                
                if closure_analysis.get('should_close') and closure_analysis.get('confidence') >= 80:
                    self._close_conversation(conversation_id, closure_analysis)
            
            logger.info(f"Mensagem processada com sucesso: {message_data.get('message_id')}")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem individual: {e}")
            raise

    def _create_new_conversation(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova conversa no banco de dados.
        
        Args:
            message_data: Dados da mensagem inicial
            
        Returns:
            Dados da conversa criada
        """
        conversation_data = {
            'cliente': {
                'telefone': message_data.get('phone'),
                'nome': message_data.get('name', 'Cliente')
            },
            'status': 'em_andamento',
            'dataHoraInicio': message_data.get('timestamp'),
            'ultimaMensagem': message_data.get('timestamp'),
            'atendentes': []
        }
        
        return create_conversation(conversation_data)

    def _get_conversation_context(self, conversation_id: str) -> str:
        """
        Obtém o contexto recente da conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Contexto formatado
        """
        messages = get_messages_by_conversation(conversation_id, limit=5)
        context = []
        
        for msg in messages:
            context.append(f"[{msg.get('remetente')}]: {msg.get('conteudo')}")
        
        return "\n".join(context)

    def _get_recent_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Obtém as mensagens recentes da conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Lista de mensagens recentes
        """
        return get_messages_by_conversation(conversation_id, limit=DEFAULT_MESSAGES_TO_CHECK)

    def _create_request(self, conversation_id: str, request_analysis: Dict[str, Any]):
        """
        Cria uma nova solicitação no banco de dados.
        
        Args:
            conversation_id: ID da conversa
            request_analysis: Análise da solicitação
        """
        request_data = {
            'descricao': request_analysis.get('request_description'),
            'prazo_prometido': request_analysis.get('deadline'),
            'status': 'pendente',
            'prioridade': request_analysis.get('priority'),
            'data_criacao': datetime.now()
        }
        
        create_request(conversation_id, request_data)

    def _close_conversation(self, conversation_id: str, closure_analysis: Dict[str, Any]):
        """
        Encerra uma conversa.
        
        Args:
            conversation_id: ID da conversa
            closure_analysis: Análise de encerramento
        """
        try:
            # Atualiza status da conversa
            update_conversation_status(conversation_id, 'encerrada')
            
            # Adiciona anotação sobre o encerramento
            save_message(conversation_id, {
                'tipo': 'sistema',
                'conteudo': f'Conversa encerrada: {closure_analysis.get("reason")}',
                'remetente': 'sistema',
                'timestamp': datetime.now(),
                'metadata': {
                    'action': 'CONVERSATION_CLOSED',
                    'reason': closure_analysis.get('reason'),
                    'confidence': closure_analysis.get('confidence')
                }
            })
            
            # Armazena tempo da última mensagem
            self.closed_conversations[conversation_id] = time.time()
            
            logger.info(f"Conversa {conversation_id} encerrada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao encerrar conversa {conversation_id}: {e}")

    def _cleanup_inactive_conversations(self):
        """
        Limpa conversas inativas.
        """
        while self.running:
            try:
                current_time = time.time()
                
                # Verifica conversas ativas
                for conv_id, last_time in self.last_processed_time.items():
                    if current_time - last_time > INACTIVITY_TIMEOUT:
                        # Verifica se deve encerrar
                        recent_messages = self._get_recent_messages(conv_id)
                        closure_analysis = self._should_close_conversation(recent_messages)
                        
                        if closure_analysis.get('should_close'):
                            self._close_conversation(conv_id, closure_analysis)
                
                time.sleep(REOPEN_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Erro ao limpar conversas inativas: {e}")
                time.sleep(RETRY_DELAY)

    def _evaluate_conversations(self):
        """
        Avalia conversas encerradas periodicamente.
        """
        while self.running:
            try:
                current_time = time.time()
                
                # Verifica se é hora de avaliar
                if current_time - self.last_evaluation_time >= EVALUATION_INTERVAL:
                    # Busca conversas encerradas não avaliadas
                    closed_conversations = get_conversations_by_status('encerrada')
                    
                    for conv in closed_conversations:
                        if not conv.get('avaliada', False):
                            self._evaluate_single_conversation(conv)
                    
                    self.last_evaluation_time = current_time
                
                time.sleep(60)  # Verifica a cada minuto
                
            except Exception as e:
                logger.error(f"Erro ao avaliar conversas: {e}")
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

    def _consolidate_attendances(self):
        """
        Consolida atendimentos periodicamente.
        """
        while self.running:
            try:
                current_time = time.time()
                
                # Verifica se é hora de consolidar
                if current_time - self.last_consolidation_time >= CONSOLIDATION_INTERVAL:
                    # Busca conversas avaliadas
                    evaluated_conversations = get_conversations_by_status('encerrada')
                    evaluated_conversations = [c for c in evaluated_conversations if c.get('avaliada', False)]
                    
                    for conv in evaluated_conversations:
                        self._consolidate_single_attendance(conv)
                    
                    self.last_consolidation_time = current_time
                
                time.sleep(60)  # Verifica a cada minuto
                
            except Exception as e:
                logger.error(f"Erro ao consolidar atendimentos: {e}")
                time.sleep(RETRY_DELAY)

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

    def _analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analisa uma mensagem usando a biblioteca de prompts.
        
        Args:
            message: Texto da mensagem a ser analisada
            
        Returns:
            Dicionário com os resultados da análise
        """
        prompt = self.prompt_library.get_message_analysis_prompt(message)
        response = self.ollama.generate(prompt)
        
        # Processa a resposta numerada
        lines = response.strip().split('\n')
        result = {
            'intent': lines[0].split(': ')[1].strip(),
            'sentiment': lines[1].split(': ')[1].strip(),
            'urgency': lines[2].split(': ')[1].strip(),
            'is_complaint': lines[3].split(': ')[1].strip().lower() == 'sim',
            'has_request': lines[4].split(': ')[1].strip().lower() == 'sim',
            'has_deadline': lines[5].split(': ')[1].strip().lower() == 'sim',
            'is_closing': lines[6].split(': ')[1].strip().lower() == 'sim',
            'topics': [t.strip() for t in lines[7].split(': ')[1].split(',')]
        }
        
        return result

    def _detect_requests(self, conversation_context: str, message: str) -> Dict[str, Any]:
        """
        Detecta solicitações em uma mensagem usando a biblioteca de prompts.
        
        Args:
            conversation_context: Contexto recente da conversa
            message: Texto da mensagem atual
            
        Returns:
            Dicionário com os resultados da detecção
        """
        prompt = self.prompt_library.get_request_detection_prompt(conversation_context, message)
        response = self.ollama.generate(prompt)
        
        # Processa a resposta numerada
        lines = response.strip().split('\n')
        result = {
            'has_request': lines[0].split(': ')[1].strip().lower() == 'sim',
            'request_description': lines[1].split(': ')[1].strip() if len(lines) > 1 else '',
            'has_deadline': lines[2].split(': ')[1].strip().lower() == 'sim' if len(lines) > 2 else False,
            'deadline': lines[3].split(': ')[1].strip() if len(lines) > 3 else '',
            'priority': lines[4].split(': ')[1].strip() if len(lines) > 4 else 'baixa'
        }
        
        return result

    def _should_close_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verifica se uma conversa deve ser encerrada usando a biblioteca de prompts.
        
        Args:
            messages: Lista das últimas mensagens da conversa
            
        Returns:
            Dicionário com os resultados da verificação
        """
        prompt = self.prompt_library.get_conversation_closure_prompt(messages)
        response = self.ollama.generate(prompt)
        
        # Processa a resposta numerada
        lines = response.strip().split('\n')
        result = {
            'should_close': lines[0].split(': ')[1].strip().lower() == 'sim',
            'confidence': int(lines[1].split(': ')[1].strip()),
            'reason': lines[2].split(': ')[1].strip()
        }
        
        return result

    def _detect_complaints(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta reclamações em uma conversa usando a biblioteca de prompts.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            Dicionário com os resultados da detecção
        """
        prompt = self.prompt_library.get_complaint_detection_prompt(messages)
        response = self.ollama.generate(prompt)
        
        # Processa a resposta numerada
        lines = response.strip().split('\n')
        result = {
            'has_complaints': lines[0].split(': ')[1].strip().lower() == 'sim',
            'complaints': [c.strip() for c in lines[1].split(': ')[1].split(',')] if len(lines) > 1 else [],
            'severity': [s.strip() for s in lines[2].split(': ')[1].split(',')] if len(lines) > 2 else [],
            'topics': [t.strip() for t in lines[3].split(': ')[1].split(',')] if len(lines) > 3 else [],
            'sentiment': lines[4].split(': ')[1].strip() if len(lines) > 4 else 'neutro',
            'satisfaction_score': int(lines[5].split(': ')[1].strip()) if len(lines) > 5 else 5
        }
        
        return result

def get_collector_agent() -> CollectorAgent:
    """
    Retorna uma instância do agente coletor.
    
    Returns:
        Instância do CollectorAgent
    """
    return CollectorAgent() 