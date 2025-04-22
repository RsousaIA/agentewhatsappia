import os
import json
import time
import datetime
import threading
import pytz
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import timedelta
from loguru import logger
from dotenv import load_dotenv
from queue import Queue, Empty
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
    get_conversations,
    get_conversation_messages,
    get_active_conversations
)
from firebase_admin import firestore
from firebase_admin.firestore import SERVER_TIMESTAMP
from .conversation_processor import ConversationProcessor
from .ollama_integration import OllamaIntegration
from .prompts_library import PromptLibrary
import traceback
import uuid

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT", "21600"))  # 6 horas em segundos
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
REOPEN_CHECK_INTERVAL = int(os.getenv("REOPEN_CHECK_INTERVAL", "300"))  # 5 minutos em segundos
DEFAULT_MESSAGES_TO_CHECK = int(os.getenv("DEFAULT_MESSAGES_TO_CHECK", "10"))  # Mensagens a verificar para encerramento

# Constante para timestamp do servidor
SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP

# Configuração de logs específica para o agente coletor
logger.add(
    "logs/collector_agent.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    filter=lambda record: "collector_agent" in record["extra"]
)

# Configuração de logs de debug
logger.add(
    "logs/collector_agent_debug.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | {extra}",
    filter=lambda record: "collector_agent" in record["extra"]
)

# Configuração de logs de erro
logger.add(
    "logs/collector_agent_error.log",
    rotation="1 day",
    retention="30 days",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | {exception}",
    filter=lambda record: "collector_agent" in record["extra"]
)

# Configuração de logs de performance
logger.add(
    "logs/collector_agent_performance.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | {elapsed}",
    filter=lambda record: "collector_agent" in record["extra"] and "performance" in record["extra"]
)

class CollectorAgent:
    """
    Agente responsável por monitorar e coletar mensagens do WhatsApp.
    """
    def __init__(self, message_queue: Queue, evaluation_notification_queue: Optional[Queue] = None):
        """
        Inicializa o agente coletor.
        
        Args:
            message_queue: Fila de mensagens do WhatsApp
            evaluation_notification_queue: Fila para notificar o agente avaliador sobre conversas encerradas
        """
        self.db = get_firestore_db()
        self.prompt_library = PromptLibrary()
        self.ollama = OllamaIntegration()
        self.message_queue = message_queue
        self.evaluation_notification_queue = evaluation_notification_queue
        self.active_conversations: Dict[str, Dict] = {}  # Conversas ativas
        self.closed_conversations: Dict[str, float] = {}  # Conversas encerradas: {id: timestamp}
        self.is_running = False
        self.threads = []
        
        # Configuração dos threads
        self.message_processing_thread = None
        self.inactive_cleaning_thread = None
        
        # Intervalos de verificação (em segundos)
        self.inactive_check_interval = 300  # 5 minutos
        
        # Tempo limite para considerar uma conversa inativa (em segundos)
        self.inactive_timeout = INACTIVITY_TIMEOUT  # 6 horas
        
        # Número de telefone do atendente (para identificar mensagens)
        self.attendant_number = os.getenv("ATTENDANT_NUMBER", "")
        
        # Inicializa o Firebase
        init_firebase()
        
        self.logger = logger.bind(collector_agent=True)
        self.logger.info("Agente Coletor inicializado")
        
    def start(self):
        """
        Inicia o agente coletor.
        """
        if self.is_running:
            logger.warning("Agente já está em execução")
            return
            
        self.is_running = True
        
        # Inicia thread de processamento de mensagens
        self.message_processing_thread = threading.Thread(target=self._process_messages)
        self.message_processing_thread.daemon = True
        self.message_processing_thread.start()
        self.threads.append(self.message_processing_thread)
        
        # Inicia thread de limpeza de conversas inativas
        self.inactive_cleaning_thread = threading.Thread(target=self._clean_inactive_conversations)
        self.inactive_cleaning_thread.daemon = True
        self.inactive_cleaning_thread.start()
        self.threads.append(self.inactive_cleaning_thread)
        
        logger.info("Todos os threads do Agente Coletor foram iniciados")
    
    def stop(self):
        """
        Para o agente coletor.
        """
        if not self.is_running:
            logger.warning("Agente Coletor já está parado")
            return
        
        self.is_running = False
        
        # Esperar que todos os threads terminem
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
                
        self.threads = []
        logger.info("Agente Coletor parado")

    def _safe_extract_float(self, lines: List[str], index: int) -> float:
        """Extrai com segurança um valor float de uma linha"""
        try:
            if index < len(lines):
                parts = lines[index].split(': ')
                if len(parts) > 1:
                    return float(parts[1].strip())
        except (ValueError, IndexError):
            pass
        return 0.0
        
    def _safe_extract_list(self, lines: List[str], index: int) -> List[str]:
        """Extrai com segurança uma lista de strings de uma linha"""
        try:
            if index < len(lines):
                parts = lines[index].split(': ')
                if len(parts) > 1:
                    return [item.strip() for item in parts[1].split(',') if item and item.strip()]
        except (ValueError, IndexError):
            pass
        return []

    def process_message(self, message_data: Dict[str, Any]):
        """
        Processa uma nova mensagem recebida.
        """
        try:
            # Adiciona timestamp de processamento
            message_data['processed_at'] = SERVER_TIMESTAMP
            
            # Verifica se a mensagem está associada a uma conversa
            conversation_id = message_data.get('conversation_id')
            
            if conversation_id:
                # Verificar se a conversa existe e seu status atual
                conversation = get_conversation(conversation_id)
                
                if conversation and conversation.get('status') == 'encerrada':
                    # A conversa existe mas está fechada
                    # Verificar se devemos reabri-la com base na mensagem atual
                    if self._should_reopen_conversation(message_data):
                        self._reopen_conversation(conversation_id, message_data.get('content', ''))
                        logger.info(f"Conversa {conversation_id} reaberta devido a nova mensagem")
                elif not conversation:
                    # Conversa não encontrada, precisamos criar uma nova
                    logger.info(f"Conversa {conversation_id} não encontrada, uma nova será criada no processamento")
            else:
                # Sem ID de conversa, uma nova conversa será criada durante o processamento
                logger.info("Mensagem sem ID de conversa, uma nova será criada no processamento")
            
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
        if not conversation_id:
            logger.error("Tentativa de reabrir conversa sem ID")
            return
            
        try:
            # Atualiza o status da conversa para "reaberta"
            update_conversation_status(conversation_id, 'reaberta')
            
            # Adiciona anotação ao sistema sobre a reabertura
            save_message(conversation_id, {
                'tipo': 'sistema',
                'conteudo': 'Conversa reaberta devido a nova mensagem do cliente após encerramento',
                'remetente': 'sistema',
                'timestamp': datetime.datetime.now(),
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

    def _process_messages(self):
        """
        Processa mensagens da fila de processamento.
        """
        logger.info("Iniciando processamento de mensagens")
        
        while self.is_running:
            try:
                # Tenta obter uma mensagem da fila com timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                    self._process_single_message(message)
                    self.message_queue.task_done()
                except Empty:
                    # Nenhuma mensagem na fila, continuar
                    pass
            except Exception as e:
                logger.error(f"Erro no processamento de mensagens: {e}")
                time.sleep(1)  # Pause breve para evitar loop infinito em caso de erro

    def _process_single_message(self, message_data: Dict[str, Any]):
        """
        Processa uma única mensagem.
        
        Args:
            message_data: Dados da mensagem a ser processada
        """
        try:
            # Extrai informações essenciais da mensagem
            conversation_id = message_data.get('conversation_id')
            content = message_data.get('body', '')
            sender = message_data.get('sender', '')
            
            # Define o ator (cliente ou atendente)
            actor = 'cliente' if sender and sender != self.attendant_number else 'atendente'
            
            if not conversation_id:
                # Nova conversa chegando
                conversation = self._create_new_conversation(sender, sender, content)
                conversation_id = conversation
                
                if not conversation_id:
                    logger.error("Falha ao obter ID da conversa após criação")
                    return
            
            # Verifica se a conversa existe
            conversation = get_conversation(conversation_id)
            if not conversation:
                # Conversa não existe, cria uma nova
                logger.info(f"Conversa {conversation_id} não encontrada, criando nova")
                conversation = self._create_new_conversation(sender, sender, content)
                conversation_id = conversation
            
            # Prepara o timestamp
            message_timestamp = message_data.get('timestamp')
            if isinstance(message_timestamp, str):
                try:
                    # Tenta converter string para datetime
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            message_timestamp = datetime.datetime.strptime(message_timestamp, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    # Se falhar, usa o timestamp atual
                    message_timestamp = datetime.datetime.now()
            elif not message_timestamp:
                message_timestamp = datetime.datetime.now()
            
            # Salva a mensagem recebida
            message_to_save = {
                'conteudo': content,
                'remetente': actor,
                'timestamp': message_timestamp,
                'conversation_id': conversation_id
            }
            
            # Define o tipo da mensagem com base em mídias anexadas
            media_url = message_data.get('media_url', '')
            if media_url:
                mime_type = message_data.get('mime_type', '')
                if 'audio' in mime_type:
                    message_to_save['tipo'] = 'audio'
                elif 'image' in mime_type:
                    message_to_save['tipo'] = 'imagem'
                elif 'video' in mime_type:
                    message_to_save['tipo'] = 'video'
                else:
                    message_to_save['tipo'] = 'arquivo'
                message_to_save['url_midia'] = media_url
            else:
                message_to_save['tipo'] = 'texto'
            
            # Salva a mensagem na conversa
            save_message(conversation_id, message_to_save)
            
            # Atualiza o timestamp da última mensagem na conversa
            update_data = {
                'ultimaMensagem': message_timestamp,
                'lastMessage': content,  # Adiciona também o conteúdo da última mensagem
                'lastMessageAt': message_timestamp.isoformat() if isinstance(message_timestamp, datetime.datetime) else str(message_timestamp)
            }
            
            # Se for uma conversa nova, atualiza o status para 'em_andamento'
            current_status = conversation.get('status', '').lower() if conversation else ''
            if current_status in ['', 'novo', 'nova']:
                update_data['status'] = 'em_andamento'
            
            # Atualiza a conversa
            update_conversation(conversation_id, update_data)
            
            # Verifica condições para encerramento da conversa
            if self._check_conversation_closure(conversation_id, content, actor):
                should_close, close_reason = self._check_conversation_closure(conversation_id, content, actor)
                self._close_conversation(conversation_id, close_reason)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            logger.exception("Detalhes do erro:")
            traceback.print_exc()

    def _format_conversation_id(self, phone_number: str, timestamp: Optional[datetime] = None) -> str:
        """
        Formata o ID da conversa usando o número do telefone do cliente e a data/hora.
        
        Args:
            phone_number: Número do telefone do cliente
            timestamp: Data e hora da primeira mensagem (opcional)
            
        Returns:
            ID formatado para a conversa
        """
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        # Formata a data e hora como parte do ID (formato: YYYYMMDD_HHMMSS)
        formatted_date = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Remove caracteres especiais do número de telefone
        clean_phone = str(phone_number).replace("+", "").replace(" ", "").replace("-", "")
        
        # Cria o ID no formato: número_data_hora
        return f"{clean_phone}_{formatted_date}"

    def _create_new_conversation(self, sender: str, recipient: str, message_content: str, timestamp: Optional[datetime] = None) -> Optional[str]:
        """
        Cria uma nova conversa no banco de dados.
        
        Args:
            sender: Telefone do remetente
            recipient: Telefone do destinatário
            message_content: Conteúdo da mensagem
            timestamp: Timestamp da mensagem
            
        Returns:
            ID da conversa criada ou None em caso de erro
        """
        try:
            # Gera um ID para a conversa
            conversation_id = self._format_conversation_id(sender, timestamp)
            
            # Se não foi fornecido um timestamp, usa o atual
            if timestamp is None:
                timestamp = datetime.datetime.now()
            
            # Formata o timestamp para string ISO
            timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else str(timestamp)
            
            # Cria dados da conversa
            conversation_data = {
                'cliente': {
                    'nome': sender,  # Usa o telefone como nome por padrão
                    'telefone': sender
                },
                'atendente': {
                    'telefone': recipient
                },
                'status': 'em_andamento',
                'dataHoraInicio': timestamp,
                'dataHoraEncerramento': None,
                'foiReaberta': False,
                'avaliada': False,
                'ultimaMensagem': timestamp,
                'agentesEnvolvidos': [recipient] if recipient != sender else [],
                
                # Campos adicionais conforme imagens
                'createdAt': timestamp_str,
                'hasUnreadMessages': True,
                'isGroup': False,
                'lastMessage': message_content,
                'lastMessageAt': timestamp_str,
                'phoneNumber': sender,
                'userName': ''
            }
            
            # Salva a conversa no banco
            if create_conversation(conversation_data):
                logger.info(f"Conversa {conversation_id} criada com sucesso")
                return conversation_id
            else:
                logger.error(f"Falha ao criar conversa para {sender}")
                return None
        
        except Exception as e:
            logger.error(f"Erro ao criar conversa: {e}")
            logger.exception("Detalhes do erro:")
            return None

    def _get_conversation_context(self, conversation_id: str) -> str:
        """
        Obtém o contexto recente da conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Contexto formatado
        """
        if not conversation_id:
            logger.warning("Tentativa de obter contexto de conversa sem ID")
            return ""
            
        messages = get_messages_by_conversation(conversation_id, limit=5)
        context = []
        
        for msg in messages:
            context.append(f"[{msg.get('remetente', 'desconhecido')}]: {msg.get('conteudo', '')}")
        
        return "\n".join(context)

    def _get_recent_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Obtém as mensagens recentes da conversa.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Lista de mensagens recentes
        """
        if not conversation_id:
            logger.warning("Tentativa de obter mensagens recentes de conversa sem ID")
            return []
            
        try:
            # Tenta obter diretamente da subcoleção de mensagens
            db = get_firestore_db()
            messages_ref = db.collection('conversas').document(conversation_id).collection('mensagens').limit(DEFAULT_MESSAGES_TO_CHECK)
            raw_messages = [doc.to_dict() for doc in messages_ref.get()]
            
            # Log para depuração
            logger.info(f"Obtidas {len(raw_messages)} mensagens brutas da subcoleção para a conversa {conversation_id}")
            
            # Se não encontrou mensagens na subcoleção, tenta o método anterior
            if not raw_messages:
                logger.warning(f"Nenhuma mensagem encontrada na subcoleção. Tentando método alternativo para conversa {conversation_id}")
                raw_messages = get_conversation_messages(conversation_id, limit=DEFAULT_MESSAGES_TO_CHECK)
                logger.info(f"Método alternativo retornou {len(raw_messages) if isinstance(raw_messages, list) else 'não-lista'} para a conversa {conversation_id}")
                
                # Se ainda não houver mensagens, faz uma análise detalhada da estrutura
                if not raw_messages or not isinstance(raw_messages, list) or len(raw_messages) == 0:
                    logger.warning(f"Nenhuma mensagem encontrada por ambos os métodos para conversa {conversation_id}. Realizando depuração detalhada.")
                    self._debug_collection_structure(conversation_id)
                    
                    # Tenta uma abordagem alternativa - acessar documentos diretamente pelo ID
                    try:
                        # Verifica se existem documentos com prefixos true_ ou false_
                        all_docs = list(messages_ref.get())
                        logger.info(f"Encontrados {len(all_docs)} documentos totais na subcoleção de mensagens")
                        
                        if all_docs:
                            # Se existem documentos, mas to_dict() não funcionou, tenta acessar diretamente
                            raw_messages = []
                            for doc in all_docs:
                                try:
                                    doc_data = doc.to_dict()
                                    if doc_data:  # Adiciona apenas se não estiver vazio
                                        # Adiciona o id como campo
                                        doc_data['doc_id'] = doc.id
                                        raw_messages.append(doc_data)
                                except Exception as doc_e:
                                    logger.error(f"Erro ao converter documento {doc.id}: {doc_e}")
                            
                            logger.info(f"Recuperados {len(raw_messages)} documentos válidos após processamento manual")
                    except Exception as alt_e:
                        logger.error(f"Erro na abordagem alternativa: {alt_e}")
            
            # Processa mensagens em diferentes formatos
            processed_messages = []
            for msg in raw_messages:
                # Verifica se a mensagem é um dicionário válido
                if isinstance(msg, dict):
                    # Cria uma cópia da mensagem para não modificar a original
                    processed_msg = msg.copy()
                    
                    # Verifica se tem os campos essenciais ou equivalentes
                    has_sender = 'remetente' in processed_msg or 'sender' in processed_msg or 'doc_id' in processed_msg
                    has_content = ('conteudo' in processed_msg or 'content' in processed_msg or 
                                 'body' in processed_msg or 'text' in processed_msg or 'doc_id' in processed_msg)
                    
                    if has_sender and has_content:
                        # Normaliza o campo remetente/sender
                        if 'sender' in processed_msg and 'remetente' not in processed_msg:
                            processed_msg['remetente'] = processed_msg['sender']
                        elif 'remetente' not in processed_msg:
                            # Se não tem remetente, tenta inferir do ID do documento ou usa valor padrão
                            if 'doc_id' in processed_msg and processed_msg['doc_id'].startswith('true_'):
                                processed_msg['remetente'] = 'cliente'
                            elif 'doc_id' in processed_msg and processed_msg['doc_id'].startswith('false_'):
                                processed_msg['remetente'] = 'atendente'
                            else:
                                processed_msg['remetente'] = 'desconhecido'
                        
                        # Normaliza o campo conteudo/content
                        if 'conteudo' not in processed_msg:
                            if 'content' in processed_msg:
                                processed_msg['conteudo'] = processed_msg['content']
                            elif 'body' in processed_msg:
                                processed_msg['conteudo'] = processed_msg['body']
                            elif 'text' in processed_msg:
                                processed_msg['conteudo'] = processed_msg['text']
                            elif 'doc_id' in processed_msg:
                                # Se não tem conteúdo, usa o ID como conteúdo
                                processed_msg['conteudo'] = f"Mensagem ID: {processed_msg['doc_id']}"
                        
                        # Garante que o campo 'content' existe (usado no _should_close_conversation)
                        if 'content' not in processed_msg:
                            processed_msg['content'] = processed_msg['conteudo']
                        
                        # Garante que tem timestamp
                        if 'timestamp' not in processed_msg:
                            if 'createdAt' in processed_msg:
                                processed_msg['timestamp'] = processed_msg['createdAt']
                            else:
                                processed_msg['timestamp'] = datetime.datetime.now()
                        
                        processed_messages.append(processed_msg)
                        
                # Se for uma lista, processa cada item da lista
                elif isinstance(msg, list):
                    for submsg in msg:
                        if isinstance(submsg, dict):
                            # Processa de forma similar ao caso do dicionário
                            processed_submsg = submsg.copy()
                            
                            has_sender = 'remetente' in processed_submsg or 'sender' in processed_submsg or 'doc_id' in processed_submsg
                            has_content = ('conteudo' in processed_submsg or 'content' in processed_submsg or 
                                         'body' in processed_submsg or 'doc_id' in processed_submsg)
                            
                            if has_sender and has_content:
                                # Normaliza o campo remetente/sender
                                if 'sender' in processed_submsg and 'remetente' not in processed_submsg:
                                    processed_submsg['remetente'] = processed_submsg['sender']
                                elif 'remetente' not in processed_submsg:
                                    # Se não tem remetente, tenta inferir do ID do documento ou usa valor padrão
                                    if 'doc_id' in processed_submsg and processed_submsg['doc_id'].startswith('true_'):
                                        processed_submsg['remetente'] = 'cliente'
                                    elif 'doc_id' in processed_submsg and processed_submsg['doc_id'].startswith('false_'):
                                        processed_submsg['remetente'] = 'atendente'
                                    else:
                                        processed_submsg['remetente'] = 'desconhecido'
                                
                                # Normaliza o campo conteudo/content
                                if 'conteudo' not in processed_submsg:
                                    if 'content' in processed_submsg:
                                        processed_submsg['conteudo'] = processed_submsg['content']
                                    elif 'body' in processed_submsg:
                                        processed_submsg['conteudo'] = processed_submsg['body']
                                    elif 'text' in processed_submsg:
                                        processed_submsg['conteudo'] = processed_submsg['text']
                                    elif 'doc_id' in processed_submsg:
                                        # Se não tem conteúdo, usa o ID como conteúdo
                                        processed_submsg['conteudo'] = f"Mensagem ID: {processed_submsg['doc_id']}"
                                
                                # Garante que o campo 'content' existe
                                if 'content' not in processed_submsg:
                                    processed_submsg['content'] = processed_submsg['conteudo']
                                
                                # Garante que tem timestamp
                                if 'timestamp' not in processed_submsg:
                                    if 'createdAt' in processed_submsg:
                                        processed_submsg['timestamp'] = processed_submsg['createdAt']
                                    else:
                                        processed_submsg['timestamp'] = datetime.datetime.now()
                                
                                processed_messages.append(processed_submsg)
            
            # Registra informações sobre as mensagens processadas
            if processed_messages:
                logger.info(f"Obtidas {len(processed_messages)} mensagens processadas para a conversa {conversation_id}")
            else:
                logger.warning(f"Nenhuma mensagem processável obtida para a conversa {conversation_id}")
            
            return processed_messages
            
        except Exception as e:
            logger.error(f"Erro ao obter mensagens para conversa {conversation_id}: {str(e)}")
            logger.exception("Detalhes do erro:")
            return []

    def _create_request(self, conversation_id: str, request_analysis: Dict[str, Any]):
        """
        Cria uma nova solicitação no banco de dados.
        
        Args:
            conversation_id: ID da conversa
            request_analysis: Análise da solicitação
        """
        if not conversation_id:
            logger.warning("Tentativa de criar solicitação para conversa sem ID")
            return
            
        # Obtem a primeira solicitação da lista se existir
        request_desc = ""
        if request_analysis.get('requests') and len(request_analysis.get('requests', [])) > 0:
            request_desc = request_analysis.get('requests')[0]
        elif request_analysis.get('request_description'):
            # Compatibilidade com formato anterior
            request_desc = request_analysis.get('request_description')
        
        # Obtem o prazo se existir
        deadline = request_analysis.get('deadline', '')
        
        # Cria dados da solicitação
        request_data = {
            'descricao': request_desc,
            'prazo_prometido': deadline,
            'status': 'pendente',
            'prioridade': request_analysis.get('priority', 'baixa'),
            'data_criacao': datetime.datetime.now()
        }
        
        # Salva no banco de dados
        create_request(conversation_id, request_data)

    def _check_conversation_closure(self, conversation_id: Optional[str], message_content: Optional[str], actor: Optional[str]) -> Tuple[bool, str]:
        """
        Verifica se uma conversa deve ser encerrada com base no conteúdo da mensagem.
        
        Args:
            conversation_id: ID da conversa
            message_content: Conteúdo da mensagem
            actor: Quem enviou a mensagem (cliente ou atendente)
            
        Returns:
            Tupla (bool, str) indicando se deve encerrar e o motivo
        """
        if not conversation_id or not message_content or not actor:
            return False, ""
        
        try:
            # Normaliza o conteúdo da mensagem para facilitar comparações
            content = str(message_content).lower()
            
            # Verifica se é uma resposta negativa do cliente após pergunta sobre continuar o atendimento
            if actor == 'cliente':
                # Obtém as últimas mensagens para verificar contexto
                try:
                    # Usa o método aprimorado para recuperar mensagens
                    recent_messages = self._get_recent_messages(conversation_id)
                    
                    if not recent_messages:
                        logger.warning(f"Nenhuma mensagem recente encontrada para verificar encerramento da conversa {conversation_id}")
                        # Tenta o método original como fallback
                        conversation_messages = get_conversation_messages(conversation_id, limit=5)
                        
                        # Processa mensagens em diferentes formatos
                        processed_messages = []
                        for msg in conversation_messages:
                            if isinstance(msg, dict) and ('remetente' in msg or 'sender' in msg) and ('conteudo' in msg or 'content' in msg):
                                processed_messages.append(msg)
                            elif isinstance(msg, list):
                                for submsg in msg:
                                    if isinstance(submsg, dict) and ('remetente' in submsg or 'sender' in submsg) and ('conteudo' in submsg or 'content' in submsg):
                                        processed_messages.append(submsg)
                    else:
                        processed_messages = recent_messages
                    
                    # Verifica se a mensagem anterior foi do atendente perguntando sobre mais ajuda
                    attendant_question = False
                    
                    # Verifica as mensagens processadas
                    for msg in reversed(processed_messages):
                        remetente = msg.get('remetente', msg.get('sender', ''))
                        if remetente and remetente != 'cliente':
                            conteudo_msg = self._safe_extract_text(msg.get('conteudo', msg.get('content', '')))
                            if conteudo_msg:
                                msg_content = str(conteudo_msg).lower()
                                if any(phrase in msg_content for phrase in [
                                    'mais alguma coisa', 
                                    'posso ajudar', 
                                    'precisa de ajuda', 
                                    'mais alguma dúvida',
                                    'algo mais',
                                    'mais algum assunto',
                                    'qualquer coisa'
                                ]):
                                    attendant_question = True
                                    break
                
                    # Se o atendente perguntou sobre mais ajuda e o cliente respondeu negativamente
                    if attendant_question and any(word in content for word in [
                        'não', 'nao', 'não preciso', 'nao preciso', 'não obrigado', 'nao obrigado'
                    ]):
                        logger.info(f"Encerrando conversa {conversation_id} - Cliente respondeu negativamente após pergunta")
                        return True, "Cliente respondeu negativamente após pergunta sobre mais ajuda"
                        
                    # Verifica se o cliente respondeu com agradecimento após pergunta de mais ajuda
                    if attendant_question and any(word in content for word in [
                        'obrigado', 'obrigada', 'agradeço', 'agradecido', 'valeu'
                    ]):
                        logger.info(f"Encerrando conversa {conversation_id} - Cliente agradeceu após pergunta sobre mais ajuda")
                        return True, "Cliente agradeceu após pergunta sobre mais ajuda"
                except Exception as e:
                    logger.error(f"Erro ao verificar mensagens anteriores: {e}")
                    logger.exception("Detalhes do erro:")
                    # Não retorna aqui para permitir verificação dos outros padrões de encerramento
            
            # Verifica se é uma mensagem de despedida explícita (independente de quem enviou)
            despedidas = [
                'tchau', 'até mais', 'até logo', 'até a próxima', 'adeus',
                'bom dia', 'boa tarde', 'boa noite', 'obrigado pela atenção',
                'agradeço pelo atendimento', 'agradeço a atenção', 'obrigada'
            ]
            
            for despedida in despedidas:
                if despedida in content:
                    logger.info(f"Encerrando conversa {conversation_id} - Mensagem de despedida detectada: '{despedida}'")
                    return True, f"Mensagem de despedida detectada: '{despedida}'"
                
            return False, ""
            
        except Exception as e:
            logger.error(f"Erro ao verificar encerramento da conversa: {e}")
            logger.exception("Detalhes do erro:")
            return False, ""

    def _close_conversation(self, conversation_id: Optional[str], close_reason: Optional[str] = None) -> None:
        """
        Encerra uma conversa.
        
        Args:
            conversation_id: ID da conversa a ser encerrada
            close_reason: Motivo do encerramento da conversa
        """
        if not conversation_id:
            logger.warning("Tentativa de encerrar conversa sem ID")
            return
            
        # Usa o novo método de encerramento que atualiza a conversa existente em vez de criar uma nova
        closure_info = {
            'encerrada_por': 'sistema',
            'motivo': close_reason or 'Conversa encerrada por inatividade ou pelo padrão de conversa'
        }
        
        self._handle_conversation_closure(conversation_id, closure_info)
        logger.info(f"Conversa {conversation_id} encaminhada para encerramento com motivo: {closure_info['motivo']}")

    def _clean_inactive_conversations(self):
        """
        Verifica e encerra conversas inativas.
        Monitora conversas ativas e verifica se devem ser encerradas por inatividade ou pelo padrão de conversa.
        """
        logger.info("Iniciando monitoramento de conversas inativas")
        
        while self.is_running:
            try:
                start_time = time.time()
                current_time = datetime.datetime.now()
                current_timestamp = current_time.timestamp()
                
                # Busca conversas em andamento, reabertas e novas
                active_conversations = get_conversations_by_status('em_andamento')
                active_conversations.extend(get_conversations_by_status('reaberta'))
                # Inclui conversas com status "novo" ou "nova"
                active_conversations.extend(get_conversations_by_status('novo'))
                active_conversations.extend(get_conversations_by_status('nova'))
                # Verifica outros status que possam estar em inglês ou com variações
                active_conversations.extend(get_conversations_by_status('ACTIVE'))
                active_conversations.extend(get_conversations_by_status('active'))
                
                logger.info(f"Verificando {len(active_conversations)} conversas ativas - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Registra IDs das conversas ativas
                if active_conversations:
                    conversation_ids = [conv.get('id', 'sem_id') for conv in active_conversations]
                    logger.info(f"IDs das conversas ativas: {', '.join(conversation_ids)}")
                
                # Processa cada conversa ativa
                for conversation in active_conversations:
                    conversation_id = conversation.get('id')
                    if not conversation_id:
                        logger.warning("Conversa sem ID encontrada na lista de ativas")
                        continue
                    
                    try:
                        # Obtém o timestamp da última mensagem
                        ultima_mensagem = get_last_message_time(conversation_id)
                        
                        if not ultima_mensagem:
                            # Verifica se há uma data em 'ultimaMensagem' no documento da conversa
                            ultima_mensagem = conversation.get('ultimaMensagem')
                            if not ultima_mensagem:
                                logger.warning(f"Não foi possível obter o timestamp da última mensagem para a conversa {conversation_id}")
                                continue
                        
                        # Certifica-se de que ultima_mensagem é um número (timestamp)
                        if isinstance(ultima_mensagem, datetime.datetime):
                            # Se for datetime, converte para timestamp
                            ultima_mensagem = ultima_mensagem.timestamp()
                        elif isinstance(ultima_mensagem, str):
                            # Se for string, tenta converter para timestamp
                            try:
                                # Primeiro tenta converter para datetime
                                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                                    try:
                                        dt_obj = datetime.datetime.strptime(ultima_mensagem, fmt)
                                        ultima_mensagem = dt_obj.timestamp()
                                        break
                                    except ValueError:
                                        continue
                                
                                # Se nenhum formato corresponder, tenta converter diretamente para float
                                if isinstance(ultima_mensagem, str):
                                    ultima_mensagem = float(ultima_mensagem)
                            except Exception as e:
                                logger.warning(f"Não foi possível converter o timestamp '{ultima_mensagem}' para número: {e}")
                                continue
                        
                        # Verifica ultima_mensagem é um número após as conversões
                        if not isinstance(ultima_mensagem, (int, float)):
                            logger.warning(f"Timestamp inválido para conversa {conversation_id}: {ultima_mensagem} (tipo: {type(ultima_mensagem)})")
                            continue
                        
                        # Calcula o tempo de inatividade
                        inactivity_time = current_timestamp - ultima_mensagem
                        
                        # Verifica se deve encerrar por inatividade
                        if inactivity_time > self.inactive_timeout:
                            logger.info(f"Conversa {conversation_id} inativa por {inactivity_time/60:.1f} minutos. Encerrando...")
                            self._close_conversation(conversation_id, "Inatividade excedeu o limite definido")
                            continue
                        
                        # Obtém as mensagens recentes para verificar o padrão de conversa
                        recent_messages = self._get_recent_messages(conversation_id)
                        if recent_messages:
                            # Verifica se deve encerrar pelo padrão de conversa
                            should_close_result = self._should_close_conversation(recent_messages)
                            if should_close_result.get('should_close', False):
                                close_reason = should_close_result.get('reason', 'Padrão de conversa indica encerramento')
                                logger.info(f"Padrão de encerramento detectado para a conversa {conversation_id}: {close_reason}")
                                self._close_conversation(conversation_id, close_reason)
                                continue
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar conversa {conversation_id}: {str(e)}")
                        logger.exception(f"Detalhes do erro para conversa {conversation_id}:")
                        continue
                
                # Calcula o tempo de execução
                execution_time = time.time() - start_time
                logger.info(f"Verificação de conversas inativas concluída em {execution_time:.2f} segundos")
                
                # Aguarda o intervalo definido antes da próxima verificação
                time.sleep(self.inactive_check_interval)
                
            except Exception as e:
                logger.error(f"Erro no monitoramento de conversas inativas: {str(e)}")
                time.sleep(60)  # Aguarda 1 minuto em caso de erro

    def _analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analisa uma mensagem usando OllamaIntegration.
        
        Args:
            message: Texto da mensagem a ser analisada
            
        Returns:
            Dicionário com os resultados da análise
        """
        try:
            # Usar o método analyze_message do OllamaIntegration
            return self.ollama.analyze_message(message)
        except Exception as e:
            logger.error(f"Erro ao analisar mensagem: {e}")
            # Retorno padrão em caso de erro
            return {
                "intent": "error",
                "sentiment": "neutral",
                "urgency": "baixa",
                "is_complaint": False,
                "has_request": False,
                "has_deadline": False,
                "deadline_info": None,
                "is_closing": False,
                "topics": []
            }

    def _detect_requests(self, conversation_context: str, message: str) -> Dict[str, Any]:
        """
        Detecta solicitações e prazos em uma mensagem usando OllamaIntegration.
        
        Args:
            conversation_context: Contexto recente da conversa
            message: Texto da mensagem atual
        
        Returns:
            Dicionário com os resultados da detecção
        """
        try:
            # Usar o método detect_requests do OllamaIntegration
            return self.ollama.detect_requests(conversation_context, message)
        except Exception as e:
            logger.error(f"Erro ao detectar solicitações: {e}")
            # Retorno padrão em caso de erro
            return {
                "has_request": False,
                "requests": [],
                "priority": "baixa"
            }

    def _should_close_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verifica se a conversa deve ser encerrada baseada nas mensagens recentes.
        
        Args:
            messages: Lista de mensagens ordenadas por timestamp
        
        Returns:
            Dict contendo 'should_close' (bool) e 'reason' (str)
        """
        if not messages:
            return {'should_close': False, 'reason': 'sem_mensagens'}
        
        # Log para depuração
        logger.info(f"Verificando encerramento com {len(messages)} mensagens")
        
        # Verificar inatividade
        # Ordena mensagens por timestamp para garantir que a última mensagem seja a mais recente
        try:
            sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', datetime.datetime.now()))
            last_message = sorted_messages[-1]
        except Exception as e:
            logger.error(f"Erro ao ordenar mensagens por timestamp: {e}")
            last_message = messages[-1]  # Se falhar, usa a última da lista não ordenada
            
        current_time = datetime.datetime.now().timestamp()
        last_message_time = last_message.get('timestamp')
        
        # Log para depuração
        logger.debug(f"Última mensagem: {self._safe_extract_text(last_message.get('conteudo', last_message.get('content', '')))[:50]}...")
        
        # Certifica-se de que last_message_time é um número (timestamp)
        try:
            if isinstance(last_message_time, datetime.datetime):
                last_message_time = last_message_time.timestamp()
            elif isinstance(last_message_time, str):
                # Tenta converter para datetime primeiro
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt_obj = datetime.datetime.strptime(last_message_time, fmt)
                        last_message_time = dt_obj.timestamp()
                        break
                    except ValueError:
                        continue
                
                # Se nenhum formato corresponder, tenta converter diretamente para float
                if isinstance(last_message_time, str):
                    last_message_time = float(last_message_time)
            
            # Verifica se last_message_time é um número após as conversões
            if not isinstance(last_message_time, (int, float)):
                logger.warning(f"Timestamp inválido: {last_message_time} (tipo: {type(last_message_time)})")
                # Se não conseguiu converter, não verifica inatividade
                return {'should_close': False, 'reason': 'timestamp_invalido'}
            
            # Se passou o tempo de inatividade (6 horas), encerra automaticamente
            inactivity_time = current_time - last_message_time
            if inactivity_time > INACTIVITY_TIMEOUT:
                logger.info(f"Inatividade detectada: {inactivity_time/3600:.2f} horas (limite: {INACTIVITY_TIMEOUT/3600:.2f} horas)")
                return {'should_close': True, 'reason': 'inatividade'}
        
        except Exception as e:
            logger.error(f"Erro ao processar timestamp: {e}")
            return {'should_close': False, 'reason': f'erro_timestamp: {str(e)}'}
        
        # Usar o Ollama para análise avançada das mensagens
        try:
            # Formata mensagens no formato esperado pelo Ollama
            formatted_messages = []
            for msg in messages:
                # Extrai o conteúdo correto da mensagem
                content = self._safe_extract_text(msg.get('conteudo', msg.get('content', '')))
                
                # Determina o papel (role) da mensagem
                remetente = msg.get('remetente', msg.get('sender', 'desconhecido')).lower()
                role = 'cliente' if remetente == 'cliente' else 'atendente'
                
                formatted_messages.append({
                    'content': content,
                    'role': role,
                    'timestamp': msg.get('timestamp')
                })
            
            # Usa a IA para decisão mais precisa sobre encerramento
            ai_analysis = self.ollama.should_close_conversation(formatted_messages)
            
            # Verifica se o resultado da IA indica encerramento com confiança acima de 70%
            if ai_analysis.get('should_close', False) and ai_analysis.get('confidence', 0) > 70:
                return {'should_close': True, 'reason': ai_analysis.get('reason', 'ia_decisao')}
                
            return {'should_close': False, 'reason': ai_analysis.get('reason', 'conversa_ativa')}
            
        except Exception as e:
            logger.error(f"Erro na análise de encerramento por IA: {e}")
            
            # Fallback: verificação simples de palavras de despedida
            farewell_words = ['tchau', 'até mais', 'adeus', 'até logo', 'obrigado', 'finalizado', 'ok', 'entendi', 'perfeito']
            
            # Verificar última mensagem para palavras de despedida
            last_content = self._safe_extract_text(last_message.get('conteudo', last_message.get('content', ''))).lower()
            if any(word in last_content for word in farewell_words):
                return {'should_close': True, 'reason': 'despedida'}
                
            return {'should_close': False, 'reason': 'sem_indicador_encerramento'}

    def _detect_complaints(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta reclamações em uma conversa.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            Dicionário com os resultados da detecção
        """
        try:
            # Formata mensagens no formato esperado pelo Ollama
            formatted_messages = []
            for msg in messages:
                # Extrai o conteúdo correto da mensagem
                content = self._safe_extract_text(msg.get('conteudo', msg.get('content', '')))
                
                # Determina o papel (role) da mensagem
                remetente = msg.get('remetente', msg.get('sender', 'desconhecido')).lower()
                role = 'cliente' if remetente == 'cliente' else 'atendente'
                
                formatted_messages.append({
                    'content': content,
                    'role': role,
                    'timestamp': msg.get('timestamp')
                })
            
            # Usa a integração do Ollama para detectar reclamações
            return self.ollama.detect_complaints(formatted_messages)
            
        except Exception as e:
            logger.error(f"Erro na detecção de reclamações: {e}")
            logger.exception("Detalhes do erro:")
            return {
                'has_complaints': False,
                'complaints': [],
                'sentiment': 'neutro',
                'satisfaction_score': 5
            }

    def _safe_extract_text(self, content):
        """
        Extrai texto seguro de um conteúdo que pode ser texto ou um objeto com várias propriedades.
        
        Args:
            content: Conteúdo da mensagem, que pode ser texto ou objeto
            
        Returns:
            Texto extraído com segurança
        """
        if not content:
            return ""
            
        if isinstance(content, str):
            return content
            
        # Se o conteúdo for um objeto, tenta extrair texto
        try:
            if isinstance(content, dict):
                # Tenta diversos campos comuns para encontrar o texto
                for field in ['text', 'body', 'conteudo', 'content', 'message', 'mensagem']:
                    if field in content and content[field]:
                        text_content = content[field]
                        if isinstance(text_content, str):
                            return text_content
                        # Se o valor também for um objeto, chama a função recursivamente
                        return self._safe_extract_text(text_content)
                    
                # Se não encontrou em campos específicos, retorna a primeira string que encontrar
                for key, value in content.items():
                    if isinstance(value, str) and value:
                        return value
            
            # Se chegou aqui, tenta converter para string
            return str(content)
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto de mensagem: {e}")
            # Tenta converter para string de qualquer forma
            try:
                return str(content)
            except:
                return ""

    def analyze_conversation_closure(self, conversation_id: str) -> Dict[str, Any]:
        """
        Analisa o encerramento de uma conversa usando a integração com Ollama.
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            Análise do encerramento da conversa com should_close, reason e confidence
        """
        # Obtém as mensagens recentes
        processed_messages = self._get_recent_messages(conversation_id)
        
        # Se não houver mensagens, retorna resultado padrão
        if not processed_messages:
            logger.warning(f"Não foram encontradas mensagens processáveis para a conversa {conversation_id}")
            return {
                'should_close': False,
                'reason': 'Não há mensagens na conversa',
                'confidence': 0.0
            }
        
        logger.info(f"Análise de encerramento para a conversa {conversation_id} com {len(processed_messages)} mensagens")
            
        # Verifica inatividade
        if len(processed_messages) > 0:
            # Ordena mensagens por timestamp
            try:
                sorted_msgs = sorted(processed_messages, key=lambda x: x.get('timestamp', datetime.datetime.now()))
                last_msg = sorted_msgs[-1]
            except Exception as e:
                logger.error(f"Erro ao ordenar mensagens por timestamp: {e}")
                last_msg = processed_messages[-1]  # Se falhar, usa a última da lista não ordenada
            
            last_msg_time = last_msg.get('timestamp')
            current_time = datetime.datetime.now()
            
            # Converte para timestamp se não for
            time_diff = 0
            try:
                if isinstance(last_msg_time, datetime.datetime):
                    # Garantir que ambos os datetimes tenham o mesmo timezone
                    if last_msg_time.tzinfo is not None and current_time.tzinfo is None:
                        # Se last_msg_time tem timezone, mas current_time não, removemos o timezone
                        last_msg_time = last_msg_time.replace(tzinfo=None)
                    elif last_msg_time.tzinfo is None and current_time.tzinfo is not None:
                        # Se current_time tem timezone, mas last_msg_time não, removemos o timezone
                        current_time = current_time.replace(tzinfo=None)
                        
                    time_diff = (current_time - last_msg_time).total_seconds()
                else:
                    # Se não for datetime, tenta converter para timestamp
                    try:
                        if last_msg_time:
                            if isinstance(last_msg_time, str):
                                # Tenta converter para datetime primeiro
                                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                                    try:
                                        dt_obj = datetime.datetime.strptime(last_msg_time, fmt)
                                        last_msg_time = dt_obj.timestamp()
                                        break
                                    except ValueError:
                                        continue
                                
                                # Se ainda for string após as tentativas, tenta converter para float
                                if isinstance(last_msg_time, str):
                                    last_msg_time = float(last_msg_time)
                                    
                            last_timestamp = float(last_msg_time) if isinstance(last_msg_time, (int, float)) else 0
                            time_diff = current_time.timestamp() - last_timestamp
                    except (TypeError, ValueError) as e:
                        logger.error(f"Erro ao converter timestamp: {e}")
                        time_diff = 0
            except Exception as e:
                logger.error(f"Erro ao calcular diferença de tempo: {e}")
                time_diff = 0
            
            # Se passou mais de 6 horas desde a última mensagem
            if time_diff > INACTIVITY_TIMEOUT:
                logger.info(f"Conversa {conversation_id} inativa por {time_diff//3600:.1f} horas (limite: {INACTIVITY_TIMEOUT//3600} horas)")
                return {
                    'should_close': True,
                    'reason': 'Inatividade prolongada',
                    'confidence': 1.0
                }
        
        # Verifica se há padrão de encerramento nas últimas mensagens
        if len(processed_messages) >= 2:
            # Verifica as duas últimas mensagens (ordenando por timestamp)
            try:
                sorted_msgs = sorted(processed_messages, key=lambda x: x.get('timestamp', datetime.datetime.now()))
                
                if len(sorted_msgs) >= 2:
                    last_msg = sorted_msgs[-1]
                    prev_msg = sorted_msgs[-2]
                    
                    # Extrai os campos de forma segura
                    last_msg_sender = last_msg.get('remetente', last_msg.get('sender', ''))
                    prev_msg_sender = prev_msg.get('remetente', prev_msg.get('sender', ''))
                    
                    last_msg_content = self._safe_extract_text(last_msg.get('conteudo', last_msg.get('content', ''))).lower()
                    prev_msg_content = self._safe_extract_text(prev_msg.get('conteudo', prev_msg.get('content', ''))).lower()
                    
                    # Verifica se o cliente agradeceu após pergunta do atendente
                    if (last_msg_sender == 'cliente' and 
                        prev_msg_sender != 'cliente' and
                        any(word in last_msg_content for word in ['obrigado', 'obrigada', 'agradeço']) and
                        any(phrase in prev_msg_content for phrase in ['qualquer coisa', 'mais alguma'])):
                        return {
                            'should_close': True,
                            'reason': 'Cliente agradeceu após oferta de ajuda',
                            'confidence': 0.9
                        }
            except Exception as e:
                logger.error(f"Erro ao verificar padrão de encerramento: {e}")
        
        # Formata mensagens para o formato esperado pelo Ollama
        formatted_messages = []
        for msg in processed_messages:
            content = self._safe_extract_text(msg.get('conteudo', msg.get('content', '')))
            remetente = msg.get('remetente', msg.get('sender', 'desconhecido')).lower()
            role = 'cliente' if remetente == 'cliente' else 'atendente'
            
            formatted_messages.append({
                'content': content,
                'role': role,
                'timestamp': msg.get('timestamp')
            })
        
        try:
            # Usa a integração do Ollama para analisar o encerramento
            result = self.ollama.should_close_conversation(formatted_messages)
            
            # Se não houver resultado ou resultado incompleto, retorna padrão
            if not result:
                return {
                    'should_close': False,
                    'reason': 'Análise incompleta',
                    'confidence': 0.0
                }
            
            # Ajusta o formato do resultado para o esperado
            return {
                'should_close': result.get('should_close', False),
                'reason': result.get('reason', 'Não especificado'),
                'confidence': result.get('confidence', 0.0) / 100.0  # Converte de porcentagem para decimal se necessário
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar encerramento da conversa {conversation_id}: {e}")
            return {
                'should_close': False,
                'reason': f"Erro: {str(e)}",
                'confidence': 0.0
            }

    def _debug_collection_structure(self, conversation_id: str) -> None:
        """
        Função de depuração que mostra a estrutura das mensagens na subcoleção.
        Útil para entender o formato dos documentos quando o processamento falha.
        
        Args:
            conversation_id: ID da conversa para analisar
        """
        try:
            # Acessa o Firestore
            db = get_firestore_db()
            messages_ref = db.collection('conversas').document(conversation_id).collection('mensagens')
            documents = messages_ref.limit(5).get()
            
            # Analisa os documentos
            logger.info(f"Análise de estrutura da subcoleção mensagens para conversa {conversation_id}")
            
            for i, doc in enumerate(documents):
                doc_data = doc.to_dict()
                logger.info(f"Documento {i+1} - ID: {doc.id}")
                logger.info(f"  Campos: {', '.join(doc_data.keys())}")
                
                # Analisa cada campo importante
                for field in ['remetente', 'sender', 'conteudo', 'content', 'body', 'timestamp', 'createdAt']:
                    if field in doc_data:
                        field_value = doc_data[field]
                        field_type = type(field_value).__name__
                        field_preview = str(field_value)[:50] + "..." if len(str(field_value)) > 50 else str(field_value)
                        logger.info(f"  {field}: ({field_type}) {field_preview}")
            
            # Verifica documentos diretamente via document ID
            prefixes = ['true_', 'false_']
            for prefix in prefixes:
                potential_ids = [doc_id for doc_id in [d.id for d in documents] if doc_id.startswith(prefix)]
                if potential_ids:
                    logger.info(f"Encontrados IDs de documentos com prefixo '{prefix}': {', '.join(potential_ids[:3])}")
            
            # Verifica a estrutura da coleção
            structure_query = db.collection('conversas').document(conversation_id)
            structure = structure_query.get()
            if structure.exists:
                fields = structure.to_dict().keys()
                logger.info(f"Documento pai da conversa {conversation_id} tem campos: {', '.join(fields)}")
            else:
                logger.warning(f"Documento pai da conversa {conversation_id} não existe")
                
        except Exception as e:
            logger.error(f"Erro ao analisar estrutura da coleção: {e}")
            logger.exception("Detalhes do erro:")

    def _handle_conversation_closure(self, conversation_id: str, closure_info: Dict[str, Any]):
        """
        Lida com o encerramento de uma conversa.
        
        Args:
            conversation_id: ID da conversa a ser encerrada
            closure_info: Informações adicionais sobre o encerramento
        """
        try:
            logger.info(f"Processando encerramento da conversa {conversation_id}")
            
            # Obter dados atuais da conversa
            conversation = get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversa {conversation_id} não encontrada para encerramento")
                return
            
            # Preparar dados de atualização para marcar como encerrada
            update_data = {
                'status': 'encerrada',
                'dataHoraEncerramento': datetime.datetime.now().isoformat(),
                'encerrada_por': closure_info.get('encerrada_por', 'sistema'),
                'motivo_encerramento': closure_info.get('motivo', 'Conversa encerrada pelo sistema'),
                'ultima_atualizacao': datetime.datetime.now().isoformat()
            }
            
            # Atualizar conversa existente
            success = update_conversation(conversation_id, update_data)
            
            if success:
                logger.info(f"Conversa {conversation_id} encerrada com sucesso")
                
                # Notificar o agente avaliador
                if self.evaluation_notification_queue:
                    self.evaluation_notification_queue.put({
                        'event': 'conversation_closed',
                        'conversation_id': conversation_id,
                        'data': {
                            'closed_at': update_data['dataHoraEncerramento'],
                            'reason': update_data['motivo_encerramento']
                        }
                    })
                    logger.info(f"Notificação de encerramento enviada para a fila: {conversation_id}")
            else:
                logger.error(f"Falha ao encerrar conversa {conversation_id}")
            
        except Exception as e:
            logger.error(f"Erro ao encerrar conversa {conversation_id}: {e}")
            traceback.print_exc()

    def _handle_new_message(self, message_data: Dict) -> None:
        """
        Processa uma nova mensagem recebida no sistema.
        
        Args:
            message_data: Dados da mensagem
        """
        try:
            # Extrai os dados necessários da mensagem
            conversation_id = self._extract_conversation_id(message_data)
            message_id = message_data.get('id', str(uuid.uuid4()))
            content = self._extract_content(message_data)
            actor = self._extract_actor(message_data)
            
            # Verifica se os dados essenciais estão presentes
            if not conversation_id or not content:
                logger.warning(f"Mensagem ignorada. Dados incompletos: {message_data}")
                return
                
            # Verifica se já existe uma conversa com esse ID
            conversation_exists = self._conversation_exists(conversation_id)
            
            # Se a conversa não existe, cria uma nova
            if not conversation_exists:
                self._create_new_conversation(conversation_id, content, actor)
            else:
                # Adiciona a mensagem à conversa existente
                self._add_message_to_conversation(conversation_id, message_id, content, actor)
                
                # Verifica se a conversa deve ser encerrada com base no conteúdo
                should_close, close_reason = self._check_conversation_closure(conversation_id, content, actor)
                if should_close:
                    logger.info(f"Encerrando conversa {conversation_id} baseado na última mensagem")
                    self._close_conversation(conversation_id, close_reason)
                    return
                
                # Se é uma mensagem do cliente, processa usando o modelo LLM
                if actor == 'cliente':
                    self._process_customer_message(conversation_id, content)
        
        except Exception as e:
            logger.error(f"Erro ao processar nova mensagem: {e}")
            logger.exception("Detalhes do erro:")

def get_collector_agent(evaluation_notification_queue: Optional[Queue] = None) -> CollectorAgent:
    """
    Retorna uma instância do agente coletor.
    
    Args:
        evaluation_notification_queue: Fila opcional para notificação de conversas encerradas
    
    Returns:
        Instância do CollectorAgent
    """
    # Cria uma fila de mensagens para o agente
    message_queue = Queue()
    
    return CollectorAgent(message_queue, evaluation_notification_queue) 