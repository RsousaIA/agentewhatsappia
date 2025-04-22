import os
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dotenv import load_dotenv
from datetime import datetime
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Union, Any, Tuple
from firebase_admin import initialize_app, storage
from google.cloud.firestore import Client
from .cache import cached, invalidate_cache, cache_manager
from threading import Lock

# Configuração de logging
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Verificar se já foi inicializado
firebase_app = None

# Configuração do cache
CACHE_SIZE = 1000
CACHE_TTL = 300  # 5 minutos

# Locks para operações concorrentes
conversation_locks = {}
global_lock = Lock()

def init_firebase():
    """Inicializa a conexão com o Firebase"""
    global firebase_app
    
    if firebase_app:
        return firebase_app
    
    try:
        # Verificar se as credenciais estão definidas como variável de ambiente ou arquivo
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        
        if cred_json:
            # Usar credenciais como JSON string
            cred_info = json.loads(cred_json)
            cred = credentials.Certificate(cred_info)
        elif cred_path:
            # Usar arquivo de credenciais
            cred = credentials.Certificate(cred_path)
        else:
            logger.error("Credenciais do Firebase não configuradas")
            raise ValueError("Credenciais do Firebase não configuradas")
        
        # Inicializar o app
        firebase_app = initialize_app(cred, {
            'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
        })
        logger.info("Firebase inicializado com sucesso")
        
        return firebase_app
    except Exception as e:
        logger.error(f"Erro ao inicializar Firebase: {e}")
        raise

def get_firestore_db() -> Client:
    """Retorna uma instância do cliente Firestore"""
    if not firebase_app:
        init_firebase()
    
    return firestore.client()

# Funções para a coleção 'conversas'
@cached(ttl=CACHE_TTL, pattern='conversation:*')
def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Obtém uma conversa pelo ID"""
    try:
        doc = get_firestore_db().collection('conversas').document(conversation_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Erro ao obter conversa {conversation_id}: {e}")
        return None

@invalidate_cache('conversation:*')
def create_conversation(conversation_data: Dict[str, Any]) -> Optional[str]:
    """
    Cria uma nova conversa no Firebase.
    
    Args:
        conversation_data: Dados da conversa contendo:
            - cliente: Dict com dados do cliente
            - status: string (em_andamento, encerrada, etc.)
            - dataHoraInicio: datetime
            - ultimaMensagem: datetime
            - id: ID personalizado (opcional)
            
    Returns:
        ID da conversa criada ou None em caso de erro
    """
    try:
        db = get_firestore_db()
        
        # Converte timestamps em string para datetime, se necessário
        for field in ['dataHoraInicio', 'dataHoraEncerramento', 'ultimaMensagem', 'lastMessageAt', 'createdAt']:
            if field in conversation_data and isinstance(conversation_data[field], str):
                try:
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            conversation_data[field] = datetime.strptime(conversation_data[field], fmt)
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.warning(f"Não foi possível converter timestamp para o campo {field}: {e}")
        
        # Verifica se já possui ID personalizado
        custom_id = conversation_data.get('id')
        conversation_id = None
        
        if custom_id:
            # Remove o ID do dicionário para não duplicar
            conversation_data_copy = conversation_data.copy()
            if 'id' in conversation_data_copy:
                conversation_data_copy.pop('id')
            
            # Cria documento com ID personalizado
            doc_ref = db.collection('conversas').document(custom_id)
            doc_ref.set(conversation_data_copy)
            conversation_id = custom_id
            logger.info(f"Conversa criada com ID personalizado: {custom_id}")
        else:
            # Gera um ID usando o phoneNumber no formato adequado
            phone_number = conversation_data.get('phoneNumber', '')
            if phone_number:
                # Gera um formato como phoneNumber_YYYYMMDD_HHMMSS
                now = datetime.datetime.now()
                timestamp_fmt = now.strftime("%Y%m%d_%H%M%S")
                conversation_id = f"{phone_number}_{timestamp_fmt}"
                doc_ref = db.collection('conversas').document(conversation_id)
                doc_ref.set(conversation_data)
                logger.info(f"Conversa criada com ID baseado em phoneNumber: {conversation_id}")
            else:
                # Se não tiver phoneNumber, gera ID automático
                doc_ref = db.collection('conversas').document()
                doc_ref.set(conversation_data)
                conversation_id = doc_ref.id
                logger.info(f"Conversa criada com ID automático: {conversation_id}")
        
        return conversation_id
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        logger.exception("Detalhes do erro:")
        return None

@invalidate_cache('conversation:*')
def update_conversation(conversation_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Atualiza uma conversa existente no Firebase.
    
    Args:
        conversation_id: ID da conversa a ser atualizada
        update_data: Dados a serem atualizados na conversa
        
    Returns:
        bool: True se a atualização foi bem-sucedida, False caso contrário
    """
    try:
        db = get_firestore_db()
        
        # Converte timestamps em string para datetime, se necessário
        for field in ['dataHoraInicio', 'dataHoraEncerramento', 'ultimaMensagem', 'lastMessageAt', 'createdAt']:
            if field in update_data and isinstance(update_data[field], str):
                try:
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            update_data[field] = datetime.strptime(update_data[field], fmt)
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    logger.warning(f"Não foi possível converter timestamp para o campo {field}: {e}")
        
        # Adiciona timestamp de atualização
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        
        # Atualiza o documento
        doc_ref = db.collection('conversas').document(conversation_id)
        doc_ref.update(update_data)
        
        logger.info(f"Conversa {conversation_id} atualizada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar conversa {conversation_id}: {e}")
        logger.exception("Detalhes do erro:")
        return False

@invalidate_cache('conversation:*')
def update_conversation_status(conversation_id: str, status: str) -> None:
    """
    Atualiza o status de uma conversa no Firebase.
    
    Args:
        conversation_id: ID da conversa
        status: Novo status da conversa (ACTIVE, CLOSED, etc)
    """
    try:
        db = get_firestore_db()
        conversation_ref = db.collection('conversas').document(conversation_id)
        
        # Atualiza o status e o timestamp da última atualização
        conversation_ref.update({
            'status': status,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Status da conversa {conversation_id} atualizado para {status}")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status da conversa {conversation_id}: {e}")
        raise

# Funções para a coleção 'mensagens'
@cached(ttl=CACHE_TTL, pattern='messages:*')
def get_messages_by_conversation(conversation_id: str, limit: int = 100) -> List[Dict]:
    """
    Obtém mensagens de uma conversa, verificando tanto na subcoleção quanto na coleção separada.
    
    Args:
        conversation_id: ID da conversa
        limit: Número máximo de mensagens a retornar
        
    Returns:
        List[Dict]: Lista de mensagens da conversa
    """
    try:
        db = get_firestore_db()
        messages = []
        
        # Primeiro, tenta buscar mensagens na subcoleção do documento da conversa
        subcollection_msgs = (db.collection('conversas')
                               .document(conversation_id)
                               .collection('mensagens')
                               .order_by('timestamp', direction=firestore.Query.DESCENDING)
                               .limit(limit)
                               .stream())
        
        for doc in subcollection_msgs:
            msg_data = doc.to_dict()
            msg_data['id'] = doc.id
            messages.append(msg_data)
        
        # Se não encontrou mensagens na subcoleção, tenta na coleção separada
        if not messages:
            collection_msgs = (db.collection('mensagens')
                                .where(filter=firestore.FieldFilter('conversation_id', '==', conversation_id))
                                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                                .limit(limit)
                                .stream())
            
            for doc in collection_msgs:
                msg_data = doc.to_dict()
                msg_data['id'] = doc.id
                messages.append(msg_data)
        
        # Registra o resultado
        logger.info(f"Recuperadas {len(messages)} mensagens para a conversa {conversation_id}")
        
        return messages
    except Exception as e:
        logger.error(f"Erro ao obter mensagens da conversa {conversation_id}: {e}")
        logger.exception("Detalhes do erro:")
        return []

@invalidate_cache('messages:*')
def save_message(conversation_id: str, message_data: Dict[str, Any]) -> bool:
    """
    Salva uma mensagem na subcoleção de mensagens de uma conversa.
    
    Args:
        conversation_id: ID da conversa
        message_data: Dados da mensagem contendo:
            - tipo: string ("texto", "audio", "imagem", etc.)
            - conteudo: string (texto ou URL)
            - remetente: string ("cliente" ou ID do atendente)
            - timestamp: datetime
            
    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        db = get_firestore_db()
        
        # Referência para a subcoleção de mensagens da conversa
        messages_ref = db.collection('conversas').document(conversation_id).collection('mensagens')
        
        # Adiciona a mensagem
        messages_ref.add(message_data)
        
        logger.info(f"Mensagem salva com sucesso na conversa {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem: {e}")
        return False

# Funções para a coleção 'solicitacoes'
@cached(ttl=CACHE_TTL, pattern='solicitacoes:*')
def get_solicitacoes_by_status(status: str, limit: int = 50) -> List[Dict]:
    """Obtém solicitações por status"""
    try:
        solicitacoes = []
        query = (get_firestore_db()
                .collection('solicitacoes')
                .where(filter=firestore.FieldFilter('status', '==', status))
                .order_by('data_criacao', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            solicitacoes.append(doc.to_dict())
            
        return solicitacoes
    except Exception as e:
        logger.error(f"Erro ao obter solicitações com status {status}: {e}")
        return []

@invalidate_cache('solicitacoes:*')
def create_solicitacao(solicitacao_data: Dict) -> str:
    """Cria uma nova solicitação"""
    try:
        doc_ref = get_firestore_db().collection('solicitacoes').document()
        solicitacao_data.update({
            'data_criacao': firestore.SERVER_TIMESTAMP,
            'ultima_atualizacao': firestore.SERVER_TIMESTAMP
        })
        doc_ref.set(solicitacao_data)
        return doc_ref.id
    except Exception as e:
        logger.error(f"Erro ao criar solicitação: {e}")
        raise

@invalidate_cache('solicitacoes:*')
def update_solicitacao(solicitacao_id: str, update_data: Dict) -> bool:
    """Atualiza uma solicitação existente"""
    try:
        db = get_firestore_db()
        update_data['ultima_atualizacao'] = firestore.SERVER_TIMESTAMP
        db.collection('solicitacoes').document(solicitacao_id).update(update_data)
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar solicitação: {e}")
        return False

@cached(ttl=CACHE_TTL, pattern='solicitacoes:*')
def get_solicitacao(solicitacao_id: str) -> Optional[Dict]:
    """Obtém uma solicitação específica"""
    try:
        doc = get_firestore_db().collection('solicitacoes').document(solicitacao_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Erro ao obter solicitação: {e}")
        return None

# Funções para a coleção 'avaliacoes'
@cached(ttl=CACHE_TTL, pattern='avaliacoes:*')
def get_avaliacoes_by_conversation(conversation_id: str) -> List[Dict]:
    """Obtém avaliações de uma conversa"""
    try:
        avaliacoes = []
        query = (get_firestore_db()
                .collection('avaliacoes')
                .where(filter=firestore.FieldFilter('conversation_id', '==', conversation_id))
                .order_by('data_criacao', direction=firestore.Query.DESCENDING))
        
        for doc in query.stream():
            avaliacoes.append(doc.to_dict())
            
        return avaliacoes
    except Exception as e:
        logger.error(f"Erro ao obter avaliações da conversa {conversation_id}: {e}")
        return []

@invalidate_cache('avaliacoes:*')
def create_avaliacao(avaliacao_data: Dict) -> str:
    """Cria uma nova avaliação"""
    try:
        doc_ref = get_firestore_db().collection('avaliacoes').document()
        avaliacao_data.update({
            'data_criacao': firestore.SERVER_TIMESTAMP
        })
        doc_ref.set(avaliacao_data)
        return doc_ref.id
    except Exception as e:
        logger.error(f"Erro ao criar avaliação: {e}")
        raise

@cached(ttl=CACHE_TTL, pattern='avaliacoes:*')
def get_avaliacao(avaliacao_id: str) -> Optional[Dict]:
    """Obtém uma avaliação específica"""
    try:
        doc = get_firestore_db().collection('avaliacoes').document(avaliacao_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Erro ao obter avaliação: {e}")
        return None

# Funções para a coleção 'consolidada_atendimentos'
@cached(ttl=CACHE_TTL, pattern='consolidado:*')
def get_consolidado_by_period(start_date: datetime, end_date: datetime) -> Optional[Dict]:
    """Obtém dados consolidados por período"""
    try:
        query = (get_firestore_db()
                .collection('consolidada_atendimentos')
                .where(filter=firestore.FieldFilter('data_inicio', '>=', start_date))
                .where(filter=firestore.FieldFilter('data_fim', '<=', end_date))
                .limit(1))
        
        for doc in query.stream():
            return doc.to_dict()
            
        return None
    except Exception as e:
        logger.error(f"Erro ao obter dados consolidados: {e}")
        return None

@invalidate_cache('consolidated:*')
def save_consolidated_attendance(consolidated_data: Dict) -> Optional[str]:
    """
    Salva um atendimento consolidado no Firebase.
    
    Args:
        consolidated_data: Dicionário com os dados do atendimento consolidado
            Deve conter pelo menos o campo 'conversation_id'
            
    Returns:
        Optional[str]: ID do documento criado ou None em caso de erro
    """
    try:
        if not consolidated_data:
            logger.error("Erro ao salvar atendimento consolidado: dados vazios")
            return None
            
        # Verifica se o campo obrigatório está presente
        if 'conversation_id' not in consolidated_data:
            logger.error("Erro ao salvar atendimento consolidado: campo conversation_id obrigatório")
            return None
            
        # Garante que temos um timestamp de criação
        if 'created_at' not in consolidated_data:
            consolidated_data['created_at'] = datetime.datetime.now()
        
        # Garante que o status é válido
        if 'statusFinal' not in consolidated_data:
            consolidated_data['statusFinal'] = 'avaliado'
            
        # Adiciona outros campos padrão se não estiverem presentes
        if 'notaGeral' not in consolidated_data:
            consolidated_data['notaGeral'] = 0
            
        # Converte valores numéricos para garantir tipo correto
        if 'notaGeral' in consolidated_data:
            try:
                consolidated_data['notaGeral'] = float(consolidated_data['notaGeral'])
            except (ValueError, TypeError):
                logger.warning(f"Valor inválido para notaGeral: {consolidated_data.get('notaGeral')}, usando 0")
                consolidated_data['notaGeral'] = 0
            
        # Conecta ao Firestore
        db = get_firestore_db()
        
        # Usa o conversation_id como ID do documento para evitar duplicidade
        doc_id = consolidated_data['conversation_id']
        
        # Verifica se já existe um documento com este ID
        existing_doc = db.collection('consolidadoAtendimentos').document(doc_id).get()
        
        if existing_doc.exists:
            # Se já existe, atualiza os dados
            db.collection('consolidadoAtendimentos').document(doc_id).update(consolidated_data)
            logger.info(f"Atendimento consolidado atualizado para conversa {doc_id}")
        else:
            # Se não existe, cria um novo documento
            db.collection('consolidadoAtendimentos').document(doc_id).set(consolidated_data)
            logger.info(f"Novo atendimento consolidado criado para conversa {doc_id}")
        
        return doc_id
    except Exception as e:
        logger.error(f"Erro ao salvar atendimento consolidado: {e}")
        import traceback
        traceback.print_exc()
        return None

@cached(ttl=CACHE_TTL, pattern='consolidado:*')
def get_consolidado(consolidado_id: str) -> Optional[Dict]:
    """Obtém um registro consolidado específico"""
    try:
        doc = get_firestore_db().collection('consolidada_atendimentos').document(consolidado_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Erro ao obter registro consolidado: {e}")
        return None

# Funções de consulta
def get_conversations(limit: int = 50) -> List[Dict]:
    """
    Obtém as conversas mais recentes.
    
    Args:
        limit: Número máximo de conversas a retornar
        
    Returns:
        Lista de conversas ordenadas por data de última atualização
    """
    try:
        conversations = []
        query = (get_firestore_db()
                .collection('conversas')
                .order_by('ultimaMensagem', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            conversations.append(data)
            
        logger.info(f"Recuperadas {len(conversations)} conversas recentes")
        return conversations
    
    except Exception as e:
        logger.error(f"Erro ao obter conversas: {e}")
        return []

def get_solicitacoes_by_status(status: str, limit: int = 50) -> List[Dict]:
    """Obtém solicitações por status"""
    try:
        solicitacoes = []
        query = (get_firestore_db()
                .collection('solicitacoes')
                .where(filter=firestore.FieldFilter('status', '==', status))
                .order_by('data_criacao', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            solicitacoes.append(doc.to_dict())
            
        return solicitacoes
    
    except Exception as e:
        logger.error(f"Erro ao obter solicitações: {e}")
        return []

def get_avaliacoes_by_conversation(conversation_id: str) -> List[Dict]:
    """Obtém avaliações de uma conversa"""
    try:
        avaliacoes = []
        query = (get_firestore_db()
                .collection('avaliacoes')
                .where(filter=firestore.FieldFilter('conversation_id', '==', conversation_id))
                .order_by('data_criacao', direction=firestore.Query.DESCENDING))
        
        for doc in query.stream():
            avaliacoes.append(doc.to_dict())
            
        return avaliacoes
    
    except Exception as e:
        logger.error(f"Erro ao obter avaliações: {e}")
        return []

def clear_all_caches():
    """Limpa todos os caches"""
    cache_manager.clear()
    logger.info("Todos os caches foram limpos")

# Funções para gerenciamento de mídia
def upload_media(file_path: str, content_type: str, conversation_id: str) -> str:
    """Upload de arquivo de mídia para o Firebase Storage"""
    try:
        if not firebase_app:
            init_firebase()
            
        bucket = storage.bucket()
        filename = os.path.basename(file_path)
        blob_name = f"media/{conversation_id}/{filename}"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path, content_type=content_type)
        
        # Gera URL pública com token de acesso
        url = blob.generate_signed_url(
            version="v4",
            expiration=3600,  # URL válida por 1 hora
            method="GET"
        )
        
        return url
    except Exception as e:
        logger.error(f"Erro ao fazer upload de mídia: {e}")
        raise

def delete_media(media_url: str) -> bool:
    """Deleta um arquivo de mídia do Firebase Storage"""
    try:
        if not firebase_app:
            init_firebase()
            
        bucket = storage.bucket()
        # Extrai o nome do blob da URL
        blob_name = media_url.split('/')[-1]
        blob = bucket.blob(blob_name)
        
        blob.delete()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar mídia: {e}")
        return False

def get_media_url(media_id: str) -> Optional[str]:
    """Obtém a URL de um arquivo de mídia"""
    try:
        if not firebase_app:
            init_firebase()
            
        bucket = storage.bucket()
        blob = bucket.blob(f"media/{media_id}")
        
        if not blob.exists():
            return None
            
        # Gera URL pública com token de acesso
        url = blob.generate_signed_url(
            version="v4",
            expiration=3600,  # URL válida por 1 hora
            method="GET"
        )
        
        return url
    except Exception as e:
        logger.error(f"Erro ao obter URL da mídia: {e}")
        return None

# Função para obter métricas do cache
def get_cache_metrics() -> Dict[str, int]:
    """Retorna as métricas do cache"""
    return cache_manager.get_metrics()

def get_last_message_time(conversation_id: str) -> Optional[Union[float, datetime]]:
    """
    Obtém o timestamp da última mensagem de uma conversa.
    
    Args:
        conversation_id: ID da conversa
        
    Returns:
        Optional[Union[float, datetime]]: Timestamp da última mensagem ou None se não houver mensagens
    """
    try:
        db = get_firestore_db()
        
        # Primeiro, tenta buscar as mensagens na subcoleção de mensagens da conversa
        messages_ref = db.collection('conversas').document(conversation_id).collection('mensagens')
        last_message_query = messages_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).get()
        
        if len(last_message_query) > 0:
            timestamp = last_message_query[0].get('timestamp')
            # Retorna o timestamp conforme encontrado (pode ser datetime ou numérico)
            return timestamp
            
        # Se não encontrou na subcoleção, tenta na coleção separada de mensagens
        messages_ref = db.collection('mensagens')
        last_message_query = messages_ref.where(
            filter=firestore.FieldFilter('conversation_id', '==', conversation_id)
        ).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).get()
        
        if len(last_message_query) > 0:
            timestamp = last_message_query[0].get('timestamp')
            # Retorna o timestamp conforme encontrado (pode ser datetime ou numérico)
            return timestamp
        
        # Se ainda não encontrou, busca no documento da conversa
        conversation = get_conversation(conversation_id)
        if conversation and 'ultimaMensagem' in conversation:
            # Tenta converter o timestamp do formato string para datetime ou numérico
            ultima_mensagem = conversation.get('ultimaMensagem')
            if isinstance(ultima_mensagem, str):
                try:
                    # Tenta parser vários formatos de data/hora em string
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(ultima_mensagem, fmt)
                        except ValueError:
                            continue
                    
                    # Se chegou aqui, nenhum dos formatos funcionou
                    logger.warning(f"Formato de data/hora não reconhecido: {ultima_mensagem}")
                except Exception as parse_error:
                    logger.error(f"Erro ao converter timestamp da string: {parse_error}")
            
            # Se não for string ou não puder converter, retorna como está
            return ultima_mensagem
        
        # Se chegou aqui é porque não encontrou informação de timestamp
        logger.warning(f"Nenhuma mensagem ou timestamp encontrado para a conversa {conversation_id}")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao obter última mensagem da conversa {conversation_id}: {e}")
        return None

@cached(ttl=CACHE_TTL, pattern='conversations:*')
def get_conversations_by_status(status: str, limit: int = 50) -> List[Dict]:
    """
    Obtém conversas com um determinado status.
    
    Args:
        status: Status das conversas a serem retornadas
        limit: Número máximo de conversas a retornar
        
    Returns:
        List[Dict]: Lista de conversas com o status especificado
    """
    try:
        conversations = []
        query = (get_firestore_db()
                .collection('conversas')
                .where(filter=firestore.FieldFilter('status', '==', status))
                .limit(limit))
        
        for doc in query.stream():
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
        
        return conversations
        
    except Exception as e:
        logger.error(f"Erro ao obter conversas com status {status}: {e}")
        return []

@cached(ttl=CACHE_TTL, pattern='conversations:*')
def get_conversations_by_tag(tag: str, limit: int = 50) -> List[Dict]:
    """
    Obtém conversas que possuem uma determinada tag.
    
    Args:
        tag: Tag a ser buscada nas conversas
        limit: Número máximo de conversas a retornar
        
    Returns:
        List[Dict]: Lista de conversas com a tag especificada
    """
    try:
        conversations = []
        query = (get_firestore_db()
                .collection('conversas')
                .where(filter=firestore.FieldFilter('tags', 'array_contains', tag))
                .limit(limit))
        
        for doc in query.stream():
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
        
        logger.info(f"Recuperadas {len(conversations)} conversas com a tag '{tag}'")
        return conversations
        
    except Exception as e:
        logger.error(f"Erro ao obter conversas com tag {tag}: {e}")
        return []

@invalidate_cache('requests:*')
def create_request(request_data: Dict) -> str:
    """
    Cria uma nova solicitação no Firebase.
    
    Args:
        request_data: Dados da solicitação
        
    Returns:
        ID da solicitação criada
    """
    try:
        doc_ref = get_firestore_db().collection('solicitacoes').document()
        request_data.update({
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'status': 'PENDING'
        })
        doc_ref.set(request_data)
        return doc_ref.id
    except Exception as e:
        logger.error(f"Erro ao criar solicitação: {e}")
        raise

@invalidate_cache('requests:*')
def update_request(request_id: str, update_data: Dict) -> bool:
    """
    Atualiza uma solicitação existente no Firebase.
    
    Args:
        request_id: ID da solicitação
        update_data: Dados a serem atualizados
        
    Returns:
        True se a atualização foi bem sucedida, False caso contrário
    """
    try:
        db = get_firestore_db()
        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        db.collection('solicitacoes').document(request_id).update(update_data)
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar solicitação {request_id}: {e}")
        return False

@cached(ttl=CACHE_TTL, pattern='requests:*')
def get_requests_by_conversation(conversation_id: str, limit: int = 50) -> List[Dict]:
    """
    Obtém solicitações de uma conversa específica.
    
    Args:
        conversation_id: ID da conversa
        limit: Limite de solicitações a serem retornadas
        
    Returns:
        Lista de solicitações da conversa
    """
    try:
        requests = []
        query = (get_firestore_db()
                .collection('solicitacoes')
                .where(filter=firestore.FieldFilter('conversation_id', '==', conversation_id))
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            request = doc.to_dict()
            request['id'] = doc.id
            requests.append(request)
            
        return requests
    except Exception as e:
        logger.error(f"Erro ao obter solicitações da conversa {conversation_id}: {e}")
        return []

@invalidate_cache('evaluations:*')
def save_evaluation(evaluation_data: Dict) -> str:
    """Salva uma avaliação para o Agente Avaliador"""
    try:
        conversation_id = evaluation_data.get('conversation_id')
        if not conversation_id:
            logger.error("Erro ao salvar avaliação: conversation_id não fornecido nos dados de avaliação")
            raise ValueError("conversation_id é obrigatório nos dados de avaliação")
            
        with get_conversation_lock(conversation_id):
            doc_ref = (get_firestore_db()
                      .collection('conversas')
                      .document(conversation_id)
                      .collection('avaliacoes')
                      .document())
            
            evaluation_data.update({
                'data_avaliacao': firestore.SERVER_TIMESTAMP
            })
            doc_ref.set(evaluation_data)
            
            # Atualiza status da conversa
            update_conversation(conversation_id, {
                'avaliada': True,
                'ultima_avaliacao': firestore.SERVER_TIMESTAMP
            })
            
            return doc_ref.id
    except Exception as e:
        logger.error(f"Erro ao salvar avaliação: {e}")
        raise

# Funções específicas para o Agente Coletor
@cached(ttl=CACHE_TTL, pattern='collector:*')
def get_active_conversations(limit: int = 50) -> List[Dict]:
    """Obtém conversas ativas para o Agente Coletor"""
    try:
        conversations = []
        query = (get_firestore_db()
                .collection('conversas')
                .where(filter=firestore.FieldFilter('status', 'in', ['em_andamento', 'reaberta']))
                .order_by('ultimaMensagem', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            conversations.append(data)
            
        return conversations
    except Exception as e:
        logger.error(f"Erro ao obter conversas ativas: {e}")
        return []

@invalidate_cache('collector:*')
def save_message(conversation_id: str, message_data: Dict) -> str:
    """Salva uma nova mensagem para o Agente Coletor"""
    try:
        with get_conversation_lock(conversation_id):
            doc_ref = (get_firestore_db()
                      .collection('conversas')
                      .document(conversation_id)
                      .collection('mensagens')
                      .document())
            
            message_data.update({
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            doc_ref.set(message_data)
            
            # Atualiza última mensagem da conversa
            update_conversation(conversation_id, {
                'ultimaMensagem': firestore.SERVER_TIMESTAMP
            })
            
            return doc_ref.id
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem: {e}")
        raise

# Funções específicas para o Agente Avaliador
@cached(ttl=CACHE_TTL, pattern='evaluator:*')
def get_conversations_to_evaluate(limit: int = 50) -> List[Dict]:
    """Obtém conversas para avaliação"""
    try:
        conversations = []
        query = (get_firestore_db()
                .collection('conversas')
                .where(filter=firestore.FieldFilter('status', '==', 'encerrada'))
                .where(filter=firestore.FieldFilter('avaliada', '==', False))
                .order_by('dataHoraEncerramento', direction=firestore.Query.DESCENDING)
                .limit(limit))
        
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            conversations.append(data)
            
        return conversations
    except Exception as e:
        logger.error(f"Erro ao obter conversas para avaliação: {e}")
        return []

# Funções de gerenciamento de locks
def get_conversation_lock(conversation_id: str) -> Lock:
    """Obtém ou cria um lock para uma conversa específica"""
    with global_lock:
        if conversation_id not in conversation_locks:
            conversation_locks[conversation_id] = Lock()
        return conversation_locks[conversation_id]

# Funções de cache e rate limiting
def clear_conversation_cache(conversation_id: str):
    """Limpa o cache de uma conversa específica"""
    cache_manager.clear_pattern(f'*:{conversation_id}')

# Funções de backup e recuperação
def backup_conversation(conversation_id: str) -> Dict:
    """Cria um backup de uma conversa específica"""
    try:
        conversation = get_conversation(conversation_id)
        messages = get_messages_by_conversation(conversation_id)
        requests = get_requests_by_conversation(conversation_id)
        evaluations = get_avaliacoes_by_conversation(conversation_id)
        
        return {
            'conversation': conversation,
            'messages': messages,
            'requests': requests,
            'evaluations': evaluations,
            'backup_time': datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao criar backup da conversa {conversation_id}: {e}")
        raise

def get_conversation_messages(conversation_id: str, limit: int = 10, start_after: Optional[str] = None):
    """
    Obtém as mensagens de uma conversa específica com suporte a paginação.
    
    Args:
        conversation_id: ID da conversa
        limit: Número máximo de mensagens a retornar
        start_after: ID da mensagem a partir da qual continuar a consulta (para paginação)
        
    Returns:
        Tupla com (lista de mensagens, ID da última mensagem para paginação)
    """
    if not conversation_id:
        logger.error("ID de conversa inválido")
        return [], None
        
    try:
        db = get_firestore_db()
        # Coleção 'conversas' > documento com ID da conversa > subcoleção 'mensagens'
        messages_ref = db.collection('conversas').document(conversation_id).collection('mensagens')
        
        # Query base ordenada por timestamp (mais recentes primeiro)
        base_query = messages_ref.order_by('timestamp', direction=firestore.Query.DESCENDING)
        
        # Aplicar paginação se houver um ponto de partida
        if start_after:
            start_doc = messages_ref.document(start_after).get()
            if start_doc.exists:
                query = base_query.start_after(start_doc).limit(limit)
            else:
                query = base_query.limit(limit)
        else:
            query = base_query.limit(limit)
        
        # Executar a consulta
        messages = []
        docs = list(query.stream())
        
        for doc in docs:
            message_data = doc.to_dict()
            message_data['id'] = doc.id
            messages.append(message_data)
        
        # Retornar o último ID para paginação futura
        last_doc_id = docs[-1].id if docs else None
        
        logger.info(f"Recuperadas {len(messages)} mensagens da conversa {conversation_id}")
        return messages, last_doc_id
        
    except Exception as e:
        logger.error(f"Erro ao buscar mensagens da conversa {conversation_id}: {e}")
        return [], None

def get_conversations_with_pagination(status: Optional[str] = None, limit: int = 20, 
                                     start_after: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
    """
    Obtém conversas com paginação para conjuntos grandes de resultados.
    
    Args:
        status: Status das conversas a serem retornadas (opcional)
        limit: Número máximo de conversas por página
        start_after: ID do documento a partir do qual continuar a consulta (para paginação)
        
    Returns:
        Tupla com (lista de conversas, ID do último documento para paginação)
    """
    try:
        db = get_firestore_db()
        collection_ref = db.collection('conversas')
        
        # Construir a query base
        if status:
            base_query = collection_ref.where(
                filter=firestore.FieldFilter('status', '==', status)
            )
        else:
            base_query = collection_ref
            
        # Ordenar por data de última atualização
        base_query = base_query.order_by('ultimaMensagem', direction=firestore.Query.DESCENDING)
        
        # Aplicar paginação se houver um ponto de partida
        if start_after:
            start_doc = collection_ref.document(start_after).get()
            if start_doc.exists:
                query = base_query.start_after(start_doc).limit(limit)
            else:
                query = base_query.limit(limit)
        else:
            query = base_query.limit(limit)
        
        # Executar a consulta
        conversations = []
        docs = list(query.stream())
        
        for doc in docs:
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
        
        # Retornar o último ID para paginação futura
        last_doc_id = docs[-1].id if docs else None
        
        logger.info(f"Recuperadas {len(conversations)} conversas com paginação")
        return conversations, last_doc_id
        
    except Exception as e:
        logger.error(f"Erro ao obter conversas paginadas: {e}")
        return [], None

def get_messages_with_pagination(conversation_id: str, limit: int = 50, 
                                start_after: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
    """
    Obtém mensagens com paginação para conversas longas.
    
    Args:
        conversation_id: ID da conversa
        limit: Número máximo de mensagens por página
        start_after: ID da mensagem a partir da qual continuar a consulta
        
    Returns:
        Tupla com (lista de mensagens, ID da última mensagem para paginação)
    """
    try:
        db = get_firestore_db()
        
        # Referência para a coleção de mensagens
        messages_ref = db.collection('mensagens')
        
        # Query base filtrada por ID da conversa
        base_query = messages_ref.where(
            filter=firestore.FieldFilter('conversation_id', '==', conversation_id)
        ).order_by('timestamp', direction=firestore.Query.DESCENDING)
        
        # Aplicar paginação se houver um ponto de partida
        if start_after:
            start_doc = messages_ref.document(start_after).get()
            if start_doc.exists:
                query = base_query.start_after(start_doc).limit(limit)
            else:
                query = base_query.limit(limit)
        else:
            query = base_query.limit(limit)
        
        # Executar a consulta
        messages = []
        docs = list(query.stream())
        
        for doc in docs:
            message = doc.to_dict()
            message['id'] = doc.id
            messages.append(message)
        
        # Retornar o último ID para paginação futura
        last_doc_id = docs[-1].id if docs else None
        
        logger.info(f"Recuperadas {len(messages)} mensagens paginadas para conversa {conversation_id}")
        return messages, last_doc_id
        
    except Exception as e:
        logger.error(f"Erro ao obter mensagens paginadas: {e}")
        return [], None

def get_conversations_by_periodo(start_date, end_date):
    """
    Retorna todas as conversas em um período específico.
    
    Args:
        start_date: Data inicial
        end_date: Data final
        
    Returns:
        List: Lista de conversas
    """
    try:
        db = get_firestore_db()
        
        # Converter datas para string se necessário
        if isinstance(start_date, datetime.datetime):
            start_date = start_date.isoformat()
        if isinstance(end_date, datetime.datetime):
            end_date = end_date.isoformat()
            
        # Query para buscar conversas no período
        now = datetime.datetime.now()
        
        # Obter referência à coleção
        conversations_ref = db.collection('conversas')
        
        # Executar query
        query = conversations_ref.where(
            filter=firestore.FieldFilter('dataHoraInicio', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('dataHoraInicio', '<=', end_date)
        )
        
        conversations = []
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            conversations.append(data)
            
        return conversations
    except Exception as e:
        logger.error(f"Erro ao obter conversas por período: {e}")
        return []

def save_consolidated_attendance(consolidated_data):
    """
    Salva dados consolidados de atendimento.
    
    Args:
        consolidated_data: Dicionário com dados consolidados
        
    Returns:
        bool: True se sucesso, False caso contrário
    """
    try:
        if not isinstance(consolidated_data, dict):
            logger.error("Os dados de consolidação devem ser um dicionário")
            return False
        
        if 'conversation_id' not in consolidated_data:
            logger.error("O ID da conversa é obrigatório para consolidação")
            return False
            
        # Adicionar timestamp de criação
        consolidated_data['created_at'] = datetime.datetime.now()
        
        # Salvar no Firestore
        db = get_firestore_db()
        
        # Usar o conversation_id como ID do documento
        doc_id = consolidated_data['conversation_id']
        
        # Verificar se já existe um documento com este ID
        existing_doc = db.collection('consolidadoAtendimentos').document(doc_id).get()
        
        if existing_doc.exists:
            # Se já existe, atualiza os dados
            db.collection('consolidadoAtendimentos').document(doc_id).update(consolidated_data)
            logger.info(f"Atendimento consolidado atualizado para conversa {doc_id}")
        else:
            # Se não existe, cria um novo documento
            db.collection('consolidadoAtendimentos').document(doc_id).set(consolidated_data)
            logger.info(f"Novo atendimento consolidado criado para conversa {doc_id}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar atendimento consolidado: {e}")
        return False

def backup_data():
    """
    Cria um backup completo do banco de dados.
    
    Returns:
        str: Caminho do arquivo de backup
    """
    try:
        db = get_firestore_db()
        data = {}
        
        # Backup de conversas
        conversations = db.collection('conversas').get()
        data['conversas'] = []
        for doc in conversations:
            data['conversas'].append(doc.to_dict())
            
        # Backup de mensagens
        messages = db.collection('mensagens').get()
        data['mensagens'] = []
        for doc in messages:
            data['mensagens'].append(doc.to_dict())
            
        # Backup de avaliações
        evaluations = db.collection('avaliacoes').get()
        data['avaliacoes'] = []
        for doc in evaluations:
            data['avaliacoes'].append(doc.to_dict())
            
        # Salvar para arquivo JSON
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Backup concluído: {filename}")
        
        # Registrar backup no Firestore
        db.collection('backups').add({
            'filename': filename,
            'backup_time': datetime.datetime.now().isoformat()
        })
        
        return filename
    except Exception as e:
        logger.error(f"Erro ao fazer backup: {e}")
        return None 