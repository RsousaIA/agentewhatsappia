"""
Módulo de integração com WhatsApp.
Gerencia a conexão com o WhatsApp e o processamento de mensagens.
"""

from .whatsapp_service import (
    WhatsAppService,
    get_whatsapp_service,
    MessageHandler
)

__all__ = [
    'WhatsAppService',
    'get_whatsapp_service',
    'MessageHandler'
] 