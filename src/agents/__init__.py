"""
Pacote de agentes para o sistema de atendimento automatizado.
"""

from agent.collector_agent import get_collector_agent, CollectorAgent
from agent.conversation_processor import ConversationProcessor
from agent.ollama_integration import OllamaIntegration, analyze_message
from agent.prompts_library import PromptLibrary

# Importe o evaluator_agent apenas se estiver disponível
try:
    from agent.evaluator_agent import get_evaluator_agent, EvaluatorAgent
except ImportError:
    pass

__all__ = [
    'get_collector_agent',
    'CollectorAgent',
    'get_evaluator_agent',
    'EvaluatorAgent'
] 