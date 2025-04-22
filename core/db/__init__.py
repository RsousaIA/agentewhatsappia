"""
Módulo de banco de dados para o sistema de atendimento WhatsApp.
Fornece funções para interagir com o Firebase Firestore.
"""

from .firebase_client import (
    init_firebase,
    get_firestore_db,
    save_message,
    get_conversation,
    update_conversation,
    create_conversation,
    get_conversations_by_status,
    get_conversations_by_tag,
    get_conversation_messages,
    get_active_conversations
)

__all__ = [
    'init_firebase',
    'get_firestore_db',
    'save_message',
    'get_conversation',
    'update_conversation',
    'create_conversation',
    'get_conversations_by_status',
    'get_conversations_by_tag',
    'get_conversation_messages',
    'get_active_conversations'
] 