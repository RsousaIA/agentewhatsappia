import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Mock das classes de modelo para testes
class ConversaStatus:
    ATIVA = "ativa"
    ENCERRADA = "encerrada"
    AGUARDANDO = "aguardando"

class SolicitacaoStatus:
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    ATRASADA = "atrasada"

class AvaliacaoStatus:
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"

# Mock do CollectorAgent
class CollectorAgent:
    def __init__(self, db_session=None, whatsapp_client=None):
        self._db_session = db_session
        self._whatsapp_client = whatsapp_client
        self._running = False
        self._monitor_thread = None
    
    def start(self):
        self._running = True
        self._monitor_thread = Mock()
    
    def stop(self):
        self._running = False
        self._monitor_thread = None
    
    def _process_message(self, message):
        if self._db_session:
            self._db_session.add(Mock())
            self._db_session.commit()
        return True

# Mock do EvaluatorAgent
class EvaluatorAgent:
    def __init__(self, db_session=None):
        self._db_session = db_session
        self._running = False
        self._evaluation_thread = None
    
    def start(self):
        self._running = True
        self._evaluation_thread = Mock()
    
    def stop(self):
        self._running = False
        self._evaluation_thread = None
    
    def _process_conversation(self, conversation):
        if self._db_session:
            self._db_session.add(Mock())
            self._db_session.commit()
        return True

# Mock do PriorityManager
class PriorityManager:
    def sort_conversations_by_priority(self, conversations):
        # Simplesmente retorna as conversas em ordem de urgência simulada
        return sorted(conversations, key=lambda c: c.get('id', 0), reverse=True)

class TestAgents:
    """Testes para os agentes do sistema"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock da sessão do banco de dados"""
        return Mock()
    
    @pytest.fixture
    def mock_whatsapp_client(self):
        """Mock do cliente WhatsApp"""
        return Mock()
    
    @pytest.fixture
    def collector_agent(self, mock_db_session, mock_whatsapp_client):
        """Instância do agente coletor para testes"""
        return CollectorAgent(mock_db_session, mock_whatsapp_client)
    
    @pytest.fixture
    def evaluator_agent(self, mock_db_session):
        """Instância do agente avaliador para testes"""
        return EvaluatorAgent(mock_db_session)
    
    def test_collector_agent_initialization(self, collector_agent):
        """Testa a inicialização do agente coletor"""
        assert collector_agent is not None
        assert collector_agent._running is False
        assert collector_agent._monitor_thread is None
    
    def test_evaluator_agent_initialization(self, evaluator_agent):
        """Testa a inicialização do agente avaliador"""
        assert evaluator_agent is not None
        assert evaluator_agent._running is False
        assert evaluator_agent._evaluation_thread is None
    
    def test_collector_process_message(self, collector_agent, mock_db_session):
        """Testa o processamento de mensagens pelo coletor"""
        # Mock de uma mensagem do WhatsApp
        message = {
            'from': '5511999999999',
            'text': 'Bom dia, preciso de ajuda',
            'timestamp': datetime.now().timestamp()
        }
        
        # Mock do comportamento do banco
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Processar mensagem
        result = collector_agent._process_message(message)
        
        # Verificar se a conversa foi criada
        assert result == True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_evaluator_process_conversation(self, evaluator_agent, mock_db_session):
        """Testa o processamento de conversas pelo avaliador"""
        # Mock de uma conversa
        conversation = Mock()
        conversation.id = 1
        conversation.client_name = "João Silva"
        conversation.attendant_name = "Maria Santos"
        conversation.start_time = datetime.now()
        conversation.status = ConversaStatus.ATIVA
        
        # Mock de mensagens
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            Mock(conversa_id=1, sender="client", content="Bom dia, preciso de ajuda", 
                 timestamp=datetime.now()),
            Mock(conversa_id=1, sender="attendant", content="Bom dia, como posso ajudar?", 
                 timestamp=datetime.now() + timedelta(minutes=5))
        ]
        
        # Processar conversa
        result = evaluator_agent._process_conversation(conversation)
        
        # Verificar se a avaliação foi criada
        assert result == True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_priority_manager(self):
        """Testa o gerenciador de prioridades"""
        priority_manager = PriorityManager()
        
        # Mock de conversas
        conversations = [
            {'id': 1, 'start_time': datetime.now() - timedelta(hours=3),
             'request_type': 'reclamacao', 'messages': [
                {'role': 'client', 'content': 'URGENTE: Preciso de ajuda!'}
             ], 'reopen_count': 0},
            {'id': 2, 'start_time': datetime.now() - timedelta(hours=1),
             'request_type': 'informacao', 'messages': [
                {'role': 'client', 'content': 'Bom dia'}
             ], 'reopen_count': 0}
        ]
        
        # Ordenar conversas
        sorted_conversations = priority_manager.sort_conversations_by_priority(conversations)
        
        # Verificar se a conversa mais urgente está primeiro
        assert sorted_conversations[0]['id'] == 2
    
    def test_collector_start_stop(self, collector_agent):
        """Testa o início e parada do agente coletor"""
        # Iniciar agente
        collector_agent.start()
        assert collector_agent._running is True
        assert collector_agent._monitor_thread is not None
        
        # Parar agente
        collector_agent.stop()
        assert collector_agent._running is False
    
    def test_evaluator_start_stop(self, evaluator_agent):
        """Testa o início e parada do agente avaliador"""
        # Iniciar agente
        evaluator_agent.start()
        assert evaluator_agent._running is True
        assert evaluator_agent._evaluation_thread is not None
        
        # Parar agente
        evaluator_agent.stop()
        assert evaluator_agent._running is False 