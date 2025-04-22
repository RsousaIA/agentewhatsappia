"""
Pacote de agentes para o sistema de atendimento automatizado.
"""

from queue import Queue
from agent.collector_agent import get_collector_agent, CollectorAgent
from agent.conversation_processor import ConversationProcessor
from agent.ollama_integration import OllamaIntegration, analyze_message
from agent.prompts_library import PromptLibrary

# Importe o evaluator_agent apenas se estiver disponível
try:
    from agent.evaluator_agent import get_evaluator_agent, EvaluatorAgent
except ImportError:
    pass

# Fila compartilhada para notificações entre o coletor e o avaliador
evaluation_notification_queue = Queue()

def init_agents():
    """
    Inicializa os agentes do sistema com a fila de notificação compartilhada.
    
    Returns:
        Tupla com os agentes coletor e avaliador inicializados
    """
    collector = get_collector_agent(evaluation_notification_queue)
    evaluator = get_evaluator_agent(evaluation_notification_queue)
    
    return collector, evaluator

__all__ = [
    'get_collector_agent',
    'CollectorAgent',
    'get_evaluator_agent',
    'EvaluatorAgent',
    'init_agents',
    'evaluation_notification_queue'
] 