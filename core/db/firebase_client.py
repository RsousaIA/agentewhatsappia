"""
Cliente Firebase para conexão com o banco de dados.
Centraliza todas as operações de acesso ao Firestore.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import initialize_app, storage
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from threading import Lock
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Variáveis globais
firebase_app = None
_lock = Lock()
_conversation_locks = {}

def init_firebase():
    """
    Inicializa a conexão com o Firebase.
    Deve ser chamado antes de qualquer outra função deste módulo.
    
    Returns:
        firebase_admin.App: A instância do aplicativo Firebase
    
    Raises:
        ValueError: Se as credenciais do Firebase não estiverem configuradas
    """
    global firebase_app
    
    with _lock:
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

def get_firestore_db() -> firestore.Client:
    """
    Retorna uma instância do cliente Firestore.
    Inicializa o Firebase se necessário.
    
    Returns:
        firestore.Client: O cliente Firestore
    """
    if not firebase_app:
        init_firebase()
    
    return firestore.client()

def get_conversation_lock(conversation_id: str) -> Lock:
    """
    Obtém um lock para operações em uma conversa específica.
    Evita condições de corrida em operações concorrentes.
    
    Args:
        conversation_id: ID da conversa
        
    Returns:
        Lock: O lock para a conversa
    """
    global _conversation_locks
    
    with _lock:
        if conversation_id not in _conversation_locks:
            _conversation_locks[conversation_id] = Lock()
        
        return _conversation_locks[conversation_id]

def get_conversation(conversation_id: str) -> Optional[Dict]:
    """
    Obtém uma conversa pelo ID.
    
    Args:
        conversation_id: ID da conversa
        
    Returns:
        Dict ou None: Dados da conversa ou None se não existir
    """
    try:
        doc = get_firestore_db().collection('conversas').document(conversation_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Erro ao obter conversa {conversation_id}: {e}")
        return None

def create_conversation(conversation_id: str, conversation_data: Dict[str, Any]) -> bool:
    """
    Cria uma nova conversa no Firebase.
    
    Args:
        conversation_id: ID da conversa
        conversation_data: Dados da conversa contendo:
            - cliente: Dict com nome e telefone
            - status: string
            - dataHoraInicio: datetime
            - dataHoraEncerramento: datetime ou None
            - foiReaberta: boolean
            - agentesEnvolvidos: array
            - tempoTotal: number
            - tempoRespostaMedio: number
            - ultimaMensagem: datetime
            
    Returns:
        bool: True se a conversa foi criada com sucesso
    """
    try:
        db = get_firestore_db()
        
        # Cria o documento com ID fornecido
        db.collection('conversas').document(conversation_id).set(conversation_data)
        
        logger.info(f"Conversa {conversation_id} criada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        return False

def update_conversation(conversation_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Atualiza dados de uma conversa existente.
    
    Args:
        conversation_id: ID da conversa
        update_data: Dados a serem atualizados
            
    Returns:
        bool: True se atualizou com sucesso, False caso contrário
    """
    try:
        db = get_firestore_db()
        
        # Atualiza o documento da conversa
        db.collection('conversas').document(conversation_id).update(update_data)
        
        logger.info(f"Conversa {conversation_id} atualizada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao atualizar conversa: {e}")
        return False

def get_conversations_by_status(status: str, limit: int = 20) -> List[Dict]:
    """
    Obtém conversas com um determinado status.
    
    Args:
        status: Status das conversas a serem retornadas (ex: "em_andamento", "encerrada", "reaberta")
        limit: Número máximo de conversas a retornar
        
    Returns:
        List[Dict]: Lista das conversas com o status especificado
    """
    try:
        conversations = []
        db = get_firestore_db()
        
        # Consulta conversas com o status especificado
        query = db.collection('conversas').where(
            filter=firestore.FieldFilter('status', '==', status)
        ).limit(limit)
        
        # Executa a consulta
        results = query.stream()
        
        # Processa os resultados
        for doc in results:
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
            
        logger.info(f"Recuperadas {len(conversations)} conversas com status '{status}'")
        return conversations
        
    except Exception as e:
        logger.error(f"Erro ao obter conversas com status {status}: {e}")
        return []

def get_conversations_by_tag(tag: str, limit: int = 20) -> List[Dict]:
    """
    Obtém conversas que possuem uma determinada tag.
    
    Args:
        tag: Tag a ser buscada nas conversas (ex: "REOPENED", "URGENT", etc.)
        limit: Número máximo de conversas a retornar
        
    Returns:
        List[Dict]: Lista das conversas com a tag especificada
    """
    try:
        conversations = []
        db = get_firestore_db()
        
        # Consulta conversas que contêm a tag especificada
        query = db.collection('conversas').where(
            filter=firestore.FieldFilter('tags', 'array_contains', tag)
        ).limit(limit)
        
        # Executa a consulta
        results = query.stream()
        
        # Processa os resultados
        for doc in results:
            conversation = doc.to_dict()
            conversation['id'] = doc.id
            conversations.append(conversation)
            
        logger.info(f"Recuperadas {len(conversations)} conversas com a tag '{tag}'")
        return conversations
        
    except Exception as e:
        logger.error(f"Erro ao obter conversas com tag {tag}: {e}")
        return []

def get_active_conversations(limit: int = 50) -> List[Dict]:
    """
    Obtém todas as conversas ativas.
    
    Args:
        limit: Número máximo de conversas a retornar
        
    Returns:
        List[Dict]: Lista de conversas ativas
    """
    return get_conversations_by_status('ACTIVE', limit)

def save_message(conversation_id: str, message_data: Dict) -> str:
    """
    Salva uma nova mensagem para uma conversa.
    
    Args:
        conversation_id: ID da conversa
        message_data: Dados da mensagem contendo:
            - tipo: string ("texto", "audio", "imagem", etc.)
            - conteudo: string (texto ou URL)
            - remetente: string ("cliente" ou ID do atendente)
            - timestamp: datetime
            
    Returns:
        str: ID da mensagem salva
    """
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

def get_conversation_messages(conversation_id: str, limit: int = 10):
    """
    Obtém as mensagens de uma conversa.
    
    Args:
        conversation_id: ID da conversa
        limit: Número máximo de mensagens a retornar
        
    Returns:
        List[Dict]: Lista de mensagens da conversa
    """
    try:
        messages = []
        message_refs = (get_firestore_db()
                      .collection('conversas')
                      .document(conversation_id)
                      .collection('mensagens')
                      .order_by('timestamp', direction=firestore.Query.DESCENDING)
                      .limit(limit))
        
        for doc in message_refs.stream():
            message = doc.to_dict()
            message['id'] = doc.id
            messages.append(message)
        
        # Inverter para ordem cronológica
        messages.reverse()
        
        return messages
    except Exception as e:
        logger.error(f"Erro ao obter mensagens da conversa {conversation_id}: {e}")
        return []

def upload_media(file_path: str, content_type: str, conversation_id: str) -> str:
    """
    Faz upload de um arquivo de mídia para o Firebase Storage.
    
    Args:
        file_path: Caminho do arquivo local
        content_type: Tipo de conteúdo (MIME type)
        conversation_id: ID da conversa relacionada
        
    Returns:
        str: URL do arquivo no Firebase Storage
    """
    try:
        if not firebase_app:
            init_firebase()
        
        bucket = storage.bucket()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        
        # Caminho no storage: conversas/{conversation_id}/media/{timestamp}_{filename}
        blob_path = f"conversas/{conversation_id}/media/{timestamp}_{filename}"
        blob = bucket.blob(blob_path)
        
        # Upload do arquivo
        blob.upload_from_filename(file_path, content_type=content_type)
        
        # Tornar o arquivo publicamente acessível
        blob.make_public()
        
        # Retornar URL público
        return blob.public_url
        
    except Exception as e:
        logger.error(f"Erro ao fazer upload de mídia: {e}")
        raise 