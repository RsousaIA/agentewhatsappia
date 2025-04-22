"""
Agente Avaliador para análise de conversas do WhatsApp.
Responsável por avaliar conversas encerradas e gerar estatísticas.
"""

from .evaluator_agent import EvaluatorAgent, get_evaluator_agent

__all__ = [
    'EvaluatorAgent',
    'get_evaluator_agent'
] 