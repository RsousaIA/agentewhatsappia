"""
Agente Coletor para processamento de mensagens do WhatsApp.
Responsável por coletar, analisar e gerenciar conversas.
"""

from .collector_agent import CollectorAgent, get_collector_agent

__all__ = [
    'CollectorAgent',
    'get_collector_agent'
] 