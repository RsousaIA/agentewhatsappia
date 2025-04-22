import sys
import os
import unittest

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

class TestImports(unittest.TestCase):
    """Testa se todas as importações principais do sistema estão funcionando."""
    
    def test_database_imports(self):
        """Testa importações relacionadas ao banco de dados."""
        try:
            from database.firebase_db import get_firestore_db
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Falha ao importar módulo do banco de dados: {str(e)}")
            
    def test_agent_imports(self):
        """Testa importações relacionadas aos agentes."""
        try:
            from src.agent.collector_agent import CollectorAgent
            from src.agent.evaluator_agent import EvaluatorAgent
            from src.agent.agent_manager import AgentManager
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Falha ao importar módulos dos agentes: {str(e)}")
            
    def test_utils_imports(self):
        """Testa importações relacionadas aos utilitários."""
        try:
            from src.utils.logger import setup_logger
            from src.utils.metricas_servico import obter_metricas_servico
            from src.utils.list_avaliacoes import get_avaliacoes
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Falha ao importar módulos de utilitários: {str(e)}")
            
    def test_metrics_imports(self):
        """Testa importações relacionadas às métricas."""
        try:
            from src.metrics.metrics_manager import MetricsManager
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Falha ao importar módulos de métricas: {str(e)}")

if __name__ == '__main__':
    unittest.main() 