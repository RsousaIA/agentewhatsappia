"""
Módulo core dos agentes contendo funcionalidades compartilhadas.
"""

from .prompts_library import PromptLibrary
from .ollama_integration import OllamaIntegration
from .conversation_processor import ConversationProcessor
from .priority_manager import PriorityManager

__all__ = [
    'PromptLibrary',
    'OllamaIntegration',
    'ConversationProcessor',
    'PriorityManager'
] 