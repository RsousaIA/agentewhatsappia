import pytest
import time
import queue
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from agent.evaluator_agent import EvaluatorAgent
from agent.evaluation_manager import EvaluationManager
from agent.priority_manager import PriorityManager
from agent.conversation_processor import ConversationProcessor

@pytest.fixture
def notification_queue():
    """Fixture que retorna uma fila de notificações mock."""
    return Mock(spec=queue.Queue)

@pytest.fixture
def evaluator_agent(notification_queue):
    """Fixture que retorna uma instância do EvaluatorAgent para testes."""
    with patch('database.firebase_db.init_firebase'), \
         patch('database.firebase_db.get_firestore_db'), \
         patch('agent.evaluator_agent.ConversationProcessor'), \
         patch('agent.evaluator_agent.PriorityManager'), \
         patch('agent.evaluator_agent.EvaluationManager'):
        agent = EvaluatorAgent(notification_queue)
        agent._running = True  # Permitir que o agente execute durante os testes
        return agent

def test_evaluator_agent_initialization(evaluator_agent, notification_queue):
    """Testa a inicialização do EvaluatorAgent."""
    assert evaluator_agent._running is True
    assert isinstance(evaluator_agent.conversation_processor, Mock)
    assert isinstance(evaluator_agent.priority_manager, Mock)
    assert isinstance(evaluator_agent.evaluation_manager, Mock)
    assert evaluator_agent._evaluation_queue.empty()
    assert len(evaluator_agent._evaluation_locks) == 0
    assert len(evaluator_agent._evaluation_start_times) == 0
    assert len(evaluator_agent._failed_evaluations) == 0
    assert evaluator_agent.notification_queue == notification_queue

def test_evaluate_conversation(evaluator_agent):
    """Testa a adição de uma conversa à fila de avaliação."""
    conversation_id = "test_conversation"
    priority = 3
    
    evaluator_agent.evaluate_conversation(conversation_id, priority)
    
    # Verificar se a conversa foi adicionada à fila com a prioridade correta
    assert not evaluator_agent._evaluation_queue.empty()
    item = evaluator_agent._evaluation_queue.get()
    assert item[0] == priority  # Prioridade correta
    assert item[2] == conversation_id  # ID da conversa
    
    # Testar com prioridade padrão
    evaluator_agent.evaluate_conversation(conversation_id)
    item = evaluator_agent._evaluation_queue.get()
    assert item[0] == 5  # Prioridade padrão (5)
    assert item[2] == conversation_id

def test_get_conversation_lock(evaluator_agent):
    """Testa a obtenção de locks para conversas."""
    conversation_id = "test_conversation"
    lock1 = evaluator_agent._get_conversation_lock(conversation_id)
    lock2 = evaluator_agent._get_conversation_lock(conversation_id)
    assert lock1 is lock2  # Deve retornar o mesmo lock para a mesma conversa

def test_check_evaluation_timeouts(evaluator_agent):
    """Testa a verificação e resolução de avaliações com timeout."""
    conversation_id = "test_conversation"
    
    # Configurar um registro de avaliação com timeout
    evaluator_agent._evaluation_start_times[conversation_id] = time.time() - 400  # 400 segundos atrás (excede o timeout padrão)
    evaluator_agent._evaluation_locks[conversation_id] = Mock()
    evaluator_agent._failed_evaluations[conversation_id] = 1  # Primeira tentativa já realizada
    
    # Mock para a função de registro de timeout
    with patch.object(evaluator_agent, '_record_evaluation_timeout') as mock_record, \
         patch('threading.Timer') as mock_timer:
        
        # Executar a verificação de timeouts
    evaluator_agent._check_evaluation_timeouts()
    
        # Verificar se o timeout foi registrado
        mock_record.assert_called_once()
        assert mock_record.call_args[0][0] == conversation_id
        assert isinstance(mock_record.call_args[0][1], float)  # Tempo decorrido
        
        # Verificar se o registro de tempo foi removido
    assert conversation_id not in evaluator_agent._evaluation_start_times
        
        # Verificar se foi agendada nova tentativa com delay progressivo
        mock_timer.assert_called_once()
        # O delay deve ser o retry_delay * (retry_count + 1)
        expected_delay = evaluator_agent._retry_delay * 2
        assert mock_timer.call_args[0][0] == expected_delay
        
        # Verificar incremento no contador de falhas
        assert evaluator_agent._failed_evaluations[conversation_id] == 2

def test_calculate_nps(evaluator_agent):
    """Testa o cálculo do NPS com a nova fórmula."""
    # Escala 0-1 (valores decimais)
    # Detratores (0-6) retornam -100
    assert evaluator_agent._calculate_nps(0.0) == -100
    assert evaluator_agent._calculate_nps(0.1) == -100
    assert evaluator_agent._calculate_nps(0.6) == -100
    
    # Neutros (7-8) retornam 0
    assert evaluator_agent._calculate_nps(0.7) == 0
    assert evaluator_agent._calculate_nps(0.8) == 0
    
    # Promotores (9-10) retornam 100
    assert evaluator_agent._calculate_nps(0.9) == 100
    assert evaluator_agent._calculate_nps(1.0) == 100
    
    # Escala 0-10 (valores inteiros)
    assert evaluator_agent._calculate_nps(0) == -100
    assert evaluator_agent._calculate_nps(6) == -100
    assert evaluator_agent._calculate_nps(7) == 0
    assert evaluator_agent._calculate_nps(8) == 0
    assert evaluator_agent._calculate_nps(9) == 100
    assert evaluator_agent._calculate_nps(10) == 100
    
    # Valores fora da escala são normalizados
    assert evaluator_agent._calculate_nps(-1) == -100  # Valores negativos viram 0 (detrator)
    assert evaluator_agent._calculate_nps(11) == 100   # Valores acima de 10 viram 10 (promotor)

def test_process_notification(evaluator_agent):
    """Testa o processamento de notificações de conversa encerrada."""
    # Criar notificação de encerramento de conversa
    notification = {
        'event': 'conversation_closed',
        'conversation_id': 'test_conversation',
        'timestamp': datetime.now().isoformat(),
        'metadata': {'reason': 'user_request'}
    }
    
    # Mock da conversa
    conversation = {
        'id': 'test_conversation',
        'status': 'encerrada',
        'avaliada': False,  # Conversa ainda não avaliada
        'cliente': {'nome': 'Cliente Teste'}
    }
    
    # Configurar mocks
    with patch('database.firebase_db.get_conversation', return_value=conversation), \
         patch.object(evaluator_agent, '_calculate_evaluation_priority', return_value=2), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        # Processar a notificação
        evaluator_agent._handle_notification(notification)
        
        # Verificar se a avaliação foi agendada com a prioridade correta
        mock_evaluate.assert_called_once_with('test_conversation', 2)
    
    # Testar com conversa já avaliada (deve ser ignorada)
    conversation['avaliada'] = True
    
    with patch('database.firebase_db.get_conversation', return_value=conversation), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        # Processar a notificação
        evaluator_agent._handle_notification(notification)
        
        # Verificar que a avaliação não foi agendada
        mock_evaluate.assert_not_called()
    
    # Testar notificação com evento desconhecido
    notification['event'] = 'unknown_event'
    
    with patch('database.firebase_db.get_conversation', return_value=conversation), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        # Processar a notificação
        evaluator_agent._handle_notification(notification)
        
        # Verificar que a avaliação não foi agendada
        mock_evaluate.assert_not_called()

def test_calculate_evaluation_priority(evaluator_agent):
    """Testa o cálculo de prioridade de avaliação com múltiplos fatores."""
    # Preparar diferentes cenários de teste
    
    # CASO 1: Conversa reaberta (prioridade máxima)
    reopened_conversation = {
        'id': 'reopened_conversation',
        'foiReaberta': True,
        'cliente': {'nome': 'Cliente Padrão'}
    }
    
    # CASO 2: Conversa com reclamação
    complaint_conversation = {
        'id': 'complaint_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente Padrão'}
    }
    
    # CASO 3: Conversa com cliente VIP
    vip_conversation = {
        'id': 'vip_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente VIP', 'vip': True}
    }
    
    # CASO 4: Conversa com muitas mensagens
    long_conversation = {
        'id': 'long_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente Padrão'}
    }
    
    # CASO 5: Conversa com solicitações urgentes
    urgent_conversation = {
        'id': 'urgent_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente Padrão'},
        'solicitacoes': [
            {'descricao': 'Solicitação urgente', 'prioridade': 'urgente'},
            {'descricao': 'Solicitação normal', 'prioridade': 'normal'}
        ]
    }
    
    # CASO 6: Conversa normal (prioridade padrão)
    normal_conversation = {
        'id': 'normal_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente Padrão'}
    }
    
    # CASO 7: Conversa muito curta (prioridade baixa)
    short_conversation = {
        'id': 'short_conversation',
        'foiReaberta': False,
        'cliente': {'nome': 'Cliente Padrão'}
    }
    
    # Configurar mocks para mensagens
    complaint_messages = [
        {'remetente': 'cliente', 'conteudo': 'Estou muito insatisfeito com o atendimento.'}
    ]
    
    normal_messages = [
        {'remetente': 'cliente', 'conteudo': 'Obrigado pela ajuda.'},
        {'remetente': 'atendente', 'conteudo': 'Por nada, estamos à disposição.'}
    ]
    
    long_messages = [{'remetente': 'cliente', 'conteudo': f'Mensagem {i}'} for i in range(30)]
    
    short_messages = [
        {'remetente': 'cliente', 'conteudo': 'Olá, preciso de ajuda.'},
        {'remetente': 'atendente', 'conteudo': 'Claro, em que posso ajudar?'},
        {'remetente': 'cliente', 'conteudo': 'Obrigado.'}
    ]
    
    with patch('database.firebase_db.get_messages_by_conversation') as mock_get_messages:
        # Teste para conversa reaberta
        mock_get_messages.return_value = normal_messages
        priority = evaluator_agent._calculate_evaluation_priority(reopened_conversation)
        assert priority == 1  # Prioridade máxima
        
        # Teste para conversa com reclamação
        mock_get_messages.return_value = complaint_messages
        priority = evaluator_agent._calculate_evaluation_priority(complaint_conversation)
        assert priority == 2  # Alta prioridade
        
        # Teste para conversa com cliente VIP
        mock_get_messages.return_value = normal_messages
        priority = evaluator_agent._calculate_evaluation_priority(vip_conversation)
        assert priority == 2  # Alta prioridade
        
        # Teste para conversa longa
        mock_get_messages.return_value = long_messages
        priority = evaluator_agent._calculate_evaluation_priority(long_conversation)
        assert priority == 4  # Prioridade média-alta
        
        # Teste para conversa com solicitações urgentes
        mock_get_messages.return_value = normal_messages
        priority = evaluator_agent._calculate_evaluation_priority(urgent_conversation)
        assert priority == 3  # Prioridade alta-média
        
        # Teste para conversa normal
        mock_get_messages.return_value = normal_messages
        priority = evaluator_agent._calculate_evaluation_priority(normal_conversation)
        assert priority == 5  # Prioridade padrão
        
        # Teste para conversa curta
        mock_get_messages.return_value = short_messages
        priority = evaluator_agent._calculate_evaluation_priority(short_conversation)
        assert priority == 7  # Prioridade baixa
        
        # Teste para conversa vazia (deve usar prioridade padrão)
        mock_get_messages.return_value = []
        priority = evaluator_agent._calculate_evaluation_priority({})
        assert priority == 5  # Prioridade padrão para caso de erro

@pytest.mark.asyncio
async def test_evaluate_conversation_integration(evaluator_agent):
    """Testa a avaliação completa de uma conversa."""
    # Mock dos dados da conversa
    conversation = {
        'id': 'test_conversation',
        'status': 'encerrada',
        'reopen_count': 0
    }
    
    messages = [
        {
            'tipo': 'texto',
            'remetente': 'cliente',
            'conteudo': 'Preciso de ajuda com meu problema',
            'timestamp': datetime.now() - timedelta(minutes=30)
        },
        {
            'tipo': 'texto',
            'remetente': 'atendente',
            'conteudo': 'Claro, como posso ajudar?',
            'timestamp': datetime.now() - timedelta(minutes=29)
        }
    ]
    
    # Mock dos resultados da avaliação
    evaluation_results = {
        'comunicacao_nota': 0.8,
        'conhecimento_nota': 0.9,
        'empatia_nota': 0.7,
        'profissionalismo_nota': 0.85,
        'resultados_nota': 0.75,
        'emocional_nota': 0.8,
        'cumprimento_prazos_nota': 0.9,
        'nota_geral': 0.8,
        'reclamacoes_detectadas': [],
        'solicitacoes_nao_atendidas': [],
        'solicitacoes_atrasadas': [],
        'pontos_positivos': ['Atendimento rápido'],
        'pontos_negativos': [],
        'sugestoes_melhoria': []
    }
    
    # Configurar mocks
    evaluator_agent.evaluation_manager.evaluate_conversation.return_value = evaluation_results
    
    # Executar avaliação
    with patch('database.firebase_db.get_conversation', return_value=conversation), \
         patch('database.firebase_db.get_messages_by_conversation', return_value=messages), \
         patch('database.firebase_db.save_evaluation') as mock_save_evaluation, \
         patch('database.firebase_db.save_consolidated_attendance') as mock_save_consolidated, \
         patch('database.firebase_db.update_conversation') as mock_update_conversation:
        
        evaluator_agent._evaluate_conversation('test_conversation')
        
        # Verificar chamadas
        evaluator_agent.evaluation_manager.evaluate_conversation.assert_called_once_with(conversation, messages)
        
        # Verificar salvamento de avaliação
        mock_save_evaluation.assert_called_once()
        eval_data = mock_save_evaluation.call_args[0][0]
        assert eval_data['conversation_id'] == 'test_conversation'
        assert eval_data['status'] == 'EVALUATED'
        
        # Verificar atualização da conversa
        mock_update_conversation.assert_called_once_with('test_conversation', {'avaliada': True})
        
        # Verificar salvamento de métricas consolidadas
        mock_save_consolidated.assert_called_once()
        consolidated_data = mock_save_consolidated.call_args[0][0]
        assert consolidated_data['conversation_id'] == 'test_conversation'
        # Com nota 0.8, deve estar abaixo do limiar de 0.9 para promotores, mas acima do limiar neutro (0.7)
        assert consolidated_data['nps'] == 0  # Neutro

def test_check_pending_requests(evaluator_agent):
    """Testa a verificação de solicitações pendentes."""
    # Mock de solicitações pendentes
    solicitacoes = [
        {
            'conversation_id': 'test_conversation',
            'prazo_prometido': datetime.now() - timedelta(days=1)  # Prazo expirado
        }
    ]
    
    with patch('database.firebase_db.get_solicitacoes_by_status', return_value=solicitacoes), \
         patch('database.firebase_db.update_conversation_status') as mock_update, \
         patch('database.firebase_db.get_evaluations_by_conversation', return_value=[{'status': 'EVALUATED'}]), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        evaluator_agent._check_pending_requests()
        
        # Verificar se a conversa foi marcada como atrasada
        mock_update.assert_called_once_with('test_conversation', 'atrasada')
        
        # Verificar se foi programada para reavaliação com alta prioridade
        mock_evaluate.assert_called_once_with('test_conversation', 2)

def test_check_reopened_conversations(evaluator_agent):
    """Testa a verificação de conversas reabertas."""
    # Mock de conversas reabertas
    conversations = [
        {
            'id': 'test_conversation',
            'status': 'reaberta',
            'reopen_count': 1
        }
    ]
    
    with patch('database.firebase_db.get_conversations_by_status', return_value=conversations), \
         patch('database.firebase_db.get_evaluations_by_conversation', return_value=[{'status': 'EVALUATED'}]), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        evaluator_agent._check_reopened_conversations()
        
        # Verificar se a conversa foi adicionada à fila de avaliação com prioridade máxima
        mock_evaluate.assert_called_once_with('test_conversation', 1)

def test_check_for_pending_evaluations(evaluator_agent):
    """Testa a verificação de avaliações pendentes."""
    # Mock de conversas encerradas
    conversations = [
        {
            'id': 'test_conversation',
            'status': 'encerrada'
        }
    ]
    
    with patch('database.firebase_db.get_conversations_by_status', return_value=conversations), \
         patch('database.firebase_db.get_evaluations_by_conversation', return_value=[]), \
         patch.object(evaluator_agent, '_calculate_evaluation_priority', return_value=3), \
         patch.object(evaluator_agent, 'evaluate_conversation') as mock_evaluate:
        
        evaluator_agent._check_for_pending_evaluations()
        
        # Verificar se a conversa foi adicionada à fila com a prioridade calculada
        mock_evaluate.assert_called_once_with('test_conversation', 3)

def test_process_evaluation_queue(evaluator_agent):
    """Testa o processamento da fila de avaliação com a nova lógica de locks."""
    conversation_id = "test_conversation"
    
    # Adicionar conversa à fila com prioridade
    evaluator_agent._evaluation_queue.put((2, time.time(), conversation_id))
    
    # Mock para o lock da conversa
    mock_lock = MagicMock()
    mock_lock.acquire.return_value = True  # O lock pode ser adquirido
    
    # Mock para a avaliação da conversa
    with patch.object(evaluator_agent, '_get_conversation_lock', return_value=mock_lock), \
         patch.object(evaluator_agent, '_evaluate_conversation') as mock_evaluate:
        
        # Executar uma iteração do processamento da fila
        evaluator_agent._process_evaluation_queue()
        
        # Verificar se o lock foi adquirido
        mock_lock.acquire.assert_called_once_with(blocking=False)
        
        # Verificar se a avaliação foi realizada
        mock_evaluate.assert_called_once_with(conversation_id)
        
        # Verificar se o lock foi liberado após a avaliação
        mock_lock.release.assert_called_once()
        
        # Verificar se o tempo de início foi registrado e depois removido
        assert conversation_id not in evaluator_agent._evaluation_start_times
        
        # Verificar se o lock foi usado
        mock_lock.__enter__.assert_called_once()
        mock_lock.__exit__.assert_called_once()
        
        # Verificar se a avaliação foi chamada
        mock_evaluate.assert_called_once_with(conversation_id)

def test_record_evaluation_timeout(evaluator_agent):
    """Testa o registro de timeouts de avaliação."""
    conversation_id = "test_conversation"
    elapsed_time = 350.5  # segundos
    
    # Mock para o logger
    with patch('agent.evaluator_agent.logger.warning') as mock_warning:
        # Chamar o método
        evaluator_agent._record_evaluation_timeout(conversation_id, elapsed_time)
        
        # Verificar se o aviso foi registrado
        mock_warning.assert_called_once()
        assert conversation_id in mock_warning.call_args[0][0]
        assert "350.5s" in mock_warning.call_args[0][0] 