import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from agent.evaluators.evaluation_manager import EvaluationManager

@pytest.fixture
def evaluation_manager():
    """Fixture que retorna uma instância do EvaluationManager para testes."""
    with patch('ai.ConversationProcessor'):
        manager = EvaluationManager()
        # Configurar mocks para os métodos do ConversationProcessor
        manager.conversation_processor.analyze_communication.return_value = 0.8
        manager.conversation_processor.analyze_technical_knowledge.return_value = 0.9
        manager.conversation_processor.analyze_empathy.return_value = 0.7
        manager.conversation_processor.analyze_professionalism.return_value = 0.85
        manager.conversation_processor.analyze_results.return_value = 0.75
        manager.conversation_processor.analyze_emotional_intelligence.return_value = 0.8
        manager.conversation_processor.detect_complaint.return_value = False
        manager.conversation_processor.extract_requests.return_value = []
        manager.conversation_processor.check_request_addressed.return_value = True
        return manager

def test_evaluation_manager_initialization(evaluation_manager):
    """Testa a inicialização do EvaluationManager."""
    assert evaluation_manager.weights['communication'] == 0.15
    assert evaluation_manager.weights['technical'] == 0.20
    assert evaluation_manager.weights['empathy'] == 0.15
    assert evaluation_manager.weights['professionalism'] == 0.15
    assert evaluation_manager.weights['results'] == 0.20
    assert evaluation_manager.weights['emotional_intelligence'] == 0.10
    assert evaluation_manager.weights['deadlines'] == 0.05
    
    assert evaluation_manager.deadlines['urgent'] == 1
    assert evaluation_manager.deadlines['high'] == 4
    assert evaluation_manager.deadlines['medium'] == 8
    assert evaluation_manager.deadlines['low'] == 24

def test_analyze_communication(evaluation_manager):
    """Testa a análise de comunicação."""
    messages = [
        {'type': 'SYSTEM', 'content': 'Bom dia, como posso ajudar?'},
        {'type': 'USER', 'content': 'Preciso de ajuda'},
        {'type': 'SYSTEM', 'content': 'Claro, conte-me mais sobre o problema'}
    ]
    
    score = evaluation_manager._analyze_communication(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_communication.call_count == 2

def test_analyze_technical_knowledge(evaluation_manager):
    """Testa a análise de conhecimento técnico."""
    messages = [
        {'type': 'SYSTEM', 'content': 'Para resolver isso, você precisa reiniciar o serviço'},
        {'type': 'USER', 'content': 'Como faço isso?'},
        {'type': 'SYSTEM', 'content': 'Use o comando systemctl restart service'}
    ]
    
    score = evaluation_manager._analyze_technical_knowledge(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_technical_knowledge.call_count == 2

def test_analyze_empathy(evaluation_manager):
    """Testa a análise de empatia."""
    messages = [
        {'type': 'SYSTEM', 'content': 'Entendo sua frustração'},
        {'type': 'USER', 'content': 'Estou muito chateado'},
        {'type': 'SYSTEM', 'content': 'Vou fazer o possível para ajudar'}
    ]
    
    score = evaluation_manager._analyze_empathy(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_empathy.call_count == 2

def test_analyze_professionalism(evaluation_manager):
    """Testa a análise de profissionalismo."""
    messages = [
        {'type': 'SYSTEM', 'content': 'Bom dia, sou o atendente João'},
        {'type': 'USER', 'content': 'Olá'},
        {'type': 'SYSTEM', 'content': 'Como posso ser útil hoje?'}
    ]
    
    score = evaluation_manager._analyze_professionalism(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_professionalism.call_count == 2

def test_analyze_results(evaluation_manager):
    """Testa a análise de resultados."""
    messages = [
        {'type': 'SYSTEM', 'content': 'O problema foi resolvido?'},
        {'type': 'USER', 'content': 'Sim, obrigado'},
        {'type': 'SYSTEM', 'content': 'Que bom que consegui ajudar'}
    ]
    
    score = evaluation_manager._analyze_results(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_results.call_count == 2

def test_analyze_emotional_intelligence(evaluation_manager):
    """Testa a análise de inteligência emocional."""
    messages = [
        {'type': 'SYSTEM', 'content': 'Percebo que você está frustrado'},
        {'type': 'USER', 'content': 'Estou muito irritado'},
        {'type': 'SYSTEM', 'content': 'Vamos resolver isso juntos'}
    ]
    
    score = evaluation_manager._analyze_emotional_intelligence(messages)
    assert 0 <= score <= 1
    assert evaluation_manager.conversation_processor.analyze_emotional_intelligence.call_count == 2

def test_analyze_deadlines(evaluation_manager):
    """Testa a análise de prazos."""
    conversation = {
        'requests': [
            {
                'id': '1',
                'priority': 'urgent',
                'deadline': datetime.now() - timedelta(hours=2),
                'timestamp': datetime.now() - timedelta(hours=3)
            }
        ]
    }
    
    messages = [
        {
            'type': 'SYSTEM',
            'content': 'Sua solicitação foi atendida',
            'timestamp': datetime.now() - timedelta(hours=1)
        }
    ]
    
    score = evaluation_manager._analyze_deadlines(conversation, messages)
    assert 0 <= score <= 1

def test_detect_complaints(evaluation_manager):
    """Testa a detecção de reclamações."""
    messages = [
        {'type': 'USER', 'content': 'Estou insatisfeito', 'id': '1', 'timestamp': datetime.now()},
        {'type': 'SYSTEM', 'content': 'Entendo sua frustração'},
        {'type': 'USER', 'content': 'O serviço está péssimo', 'id': '2', 'timestamp': datetime.now()}
    ]
    
    evaluation_manager.conversation_processor.detect_complaint.side_effect = [True, False, True]
    
    complaints = evaluation_manager._detect_complaints(messages)
    assert len(complaints) == 2
    assert complaints[0]['message_id'] == '1'
    assert complaints[1]['message_id'] == '2'

def test_check_unaddressed_requests(evaluation_manager):
    """Testa a verificação de solicitações não atendidas."""
    messages = [
        {'type': 'USER', 'content': 'Preciso de ajuda com o sistema'},
        {'type': 'SYSTEM', 'content': 'Claro, como posso ajudar?'},
        {'type': 'USER', 'content': 'O sistema está lento'},
        {'type': 'SYSTEM', 'content': 'Vou verificar isso para você'}
    ]
    
    evaluation_manager.conversation_processor.extract_requests.return_value = ['ajuda com o sistema', 'sistema lento']
    
    unaddressed = evaluation_manager._check_unaddressed_requests(messages)
    assert len(unaddressed) == 0  # Todas as solicitações foram atendidas

def test_check_delays(evaluation_manager):
    """Testa a verificação de atrasos."""
    conversation = {
        'requests': [
            {
                'id': '1',
                'priority': 'urgent',
                'deadline': datetime.now() - timedelta(hours=2),
                'timestamp': datetime.now() - timedelta(hours=3)
            }
        ]
    }
    
    messages = [
        {
            'type': 'SYSTEM',
            'content': 'Sua solicitação foi atendida',
            'timestamp': datetime.now() - timedelta(hours=1)
        }
    ]
    
    delays = evaluation_manager._check_delays(conversation, messages)
    assert len(delays) == 1
    assert delays[0]['request_id'] == '1'
    assert delays[0]['priority'] == 'urgent'

def test_evaluate_conversation(evaluation_manager):
    """Testa a avaliação completa de uma conversa."""
    conversation = {
        'id': 'test_conversation',
        'requests': [
            {
                'id': '1',
                'priority': 'urgent',
                'deadline': datetime.now() - timedelta(hours=2),
                'timestamp': datetime.now() - timedelta(hours=3)
            }
        ]
    }
    
    messages = [
        {'type': 'USER', 'content': 'Preciso de ajuda urgente', 'id': '1', 'timestamp': datetime.now() - timedelta(hours=3)},
        {'type': 'SYSTEM', 'content': 'Entendo sua urgência', 'timestamp': datetime.now() - timedelta(hours=2)},
        {'type': 'SYSTEM', 'content': 'O problema foi resolvido', 'timestamp': datetime.now() - timedelta(hours=1)}
    ]
    
    results = evaluation_manager.evaluate_conversation(conversation, messages)
    
    assert 'communication_score' in results
    assert 'technical_score' in results
    assert 'empathy_score' in results
    assert 'professionalism_score' in results
    assert 'results_score' in results
    assert 'emotional_score' in results
    assert 'deadlines_score' in results
    assert 'final_score' in results
    assert 'complaints' in results
    assert 'unaddressed_requests' in results
    assert 'delays' in results
    assert 'evaluated_at' in results
    
    assert 0 <= results['final_score'] <= 1 