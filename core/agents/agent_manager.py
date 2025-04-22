"""
Gerenciador de agentes inteligentes.
Controla os agentes de coleção e avaliação de mensagens.
"""

import threading
import logging
from typing import Dict, Any, Optional
from loguru import logger
from .collector import CollectorAgent, get_collector_agent
from .evaluator import EvaluatorAgent, get_evaluator_agent

class AgentManager:
    """
    Gerenciador que controla os agentes de coleção e avaliação.
    Fornece uma interface unificada para iniciar, parar e controlar os agentes.
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de agentes.
        """
        logger.info("Inicializando gerenciador de agentes...")
        
        # Referenciar os agentes
        self.collector_agent = get_collector_agent()
        self.evaluator_agent = get_evaluator_agent()
        
        # Estado dos agentes
        self.collector_running = False
        self.evaluator_running = False
        
        logger.info("Gerenciador de agentes inicializado com sucesso")
    
    def start_collector(self) -> bool:
        """
        Inicia o agente coletor.
        
        Returns:
            bool: True se o agente foi iniciado com sucesso
        """
        if not self.collector_running:
            try:
                self.collector_agent.start()
                self.collector_running = True
                logger.info("Agente Coletor iniciado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao iniciar Agente Coletor: {e}")
                return False
        else:
            logger.warning("Agente Coletor já está em execução")
            return True
    
    def stop_collector(self) -> bool:
        """
        Para o agente coletor.
        
        Returns:
            bool: True se o agente foi parado com sucesso
        """
        if self.collector_running:
            try:
                self.collector_agent.stop()
                self.collector_running = False
                logger.info("Agente Coletor parado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao parar Agente Coletor: {e}")
                return False
        else:
            logger.warning("Agente Coletor não está em execução")
            return True
    
    def start_evaluator(self) -> bool:
        """
        Inicia o agente avaliador.
        
        Returns:
            bool: True se o agente foi iniciado com sucesso
        """
        if not self.evaluator_running:
            try:
                self.evaluator_agent.start()
                self.evaluator_running = True
                logger.info("Agente Avaliador iniciado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao iniciar Agente Avaliador: {e}")
                return False
        else:
            logger.warning("Agente Avaliador já está em execução")
            return True
    
    def stop_evaluator(self) -> bool:
        """
        Para o agente avaliador.
        
        Returns:
            bool: True se o agente foi parado com sucesso
        """
        if self.evaluator_running:
            try:
                self.evaluator_agent.stop()
                self.evaluator_running = False
                logger.info("Agente Avaliador parado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao parar Agente Avaliador: {e}")
                return False
        else:
            logger.warning("Agente Avaliador não está em execução")
            return True
    
    def start_all(self) -> bool:
        """
        Inicia todos os agentes.
        
        Returns:
            bool: True se todos os agentes foram iniciados com sucesso
        """
        collector_success = self.start_collector()
        evaluator_success = self.start_evaluator()
        
        return collector_success and evaluator_success
    
    def stop_all(self) -> bool:
        """
        Para todos os agentes.
        
        Returns:
            bool: True se todos os agentes foram parados com sucesso
        """
        collector_success = self.stop_collector()
        evaluator_success = self.stop_evaluator()
        
        return collector_success and evaluator_success
    
    def get_status(self) -> Dict[str, bool]:
        """
        Retorna o status de todos os agentes.
        
        Returns:
            Dict[str, bool]: Status de cada agente
        """
        return {
            'collector': self.collector_running,
            'evaluator': self.evaluator_running
        }
    
    def process_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Processa uma mensagem através do agente coletor.
        
        Args:
            message_data: Dados da mensagem
            
        Returns:
            bool: True se a mensagem foi processada com sucesso
        """
        if not self.collector_running:
            logger.warning("Tentativa de processar mensagem com Agente Coletor parado")
            return False
        
        try:
            self.collector_agent.process_message(message_data)
            return True
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return False

# Instância global do gerenciador
_agent_manager_instance = None

def get_agent_manager() -> AgentManager:
    """
    Retorna a instância global do gerenciador de agentes.
    Cria uma nova instância se necessário.
    
    Returns:
        AgentManager: A instância do gerenciador
    """
    global _agent_manager_instance
    
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager()
        
    return _agent_manager_instance 