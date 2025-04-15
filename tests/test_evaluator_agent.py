import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import time
import threading
from sqlalchemy.exc import SQLAlchemyError
import json
from loguru import logger
from sqlalchemy import select

from agent.evaluator_agent import EvaluatorAgent
from database.models import (
    Conversa, Mensagem, Solicitacao, Avaliacao, ConsolidadaAtendimento,
    ConversaStatus, SolicitacaoStatus, AvaliacaoStatus
)
from utils.text_analysis import ConversationProcessor
from agent.priority_manager import PriorityManager

@pytest.fixture
def mock_db_session():
    with patch('agent.evaluator_agent.safe_db_session') as mock:
        yield mock

@pytest.fixture
def mock_conversation_processor():
    processor = Mock(spec=ConversationProcessor)
    processor.analyze_response_quality.return_value = 0.8
    processor.detect_sentiment.return_value = 0.7
    return processor

@pytest.fixture
def mock_priority_manager():
    manager = Mock(spec=PriorityManager)
    manager.sort_conversations_by_priority.return_value = [
        {'id': 1, 'priority': 0.9},
        {'id': 2, 'priority': 0.7}
    ]
    return manager

@pytest.fixture
def mock_ollama_client():
    """Mock do cliente Ollama."""
    client = Mock()
    client.generate.return_value = {
        "response": json.dumps({
            "saudacao": True,
            "despedida": True,
            "sentimento": 0.8,
            "qualidade_resposta": 0.9,
            "tempo_resposta": "adequado",
            "resolucao": True,
        })
    }
    return client

@pytest.fixture
def evaluator_agent(mock_conversation_processor, mock_priority_manager, mock_ollama_client):
    agent = EvaluatorAgent()
    agent.conversation_processor = mock_conversation_processor
    agent.priority_manager = mock_priority_manager
    agent.ollama_client = mock_ollama_client
    return agent

def test_evaluator_agent_initialization(evaluator_agent):
    """Testa a inicialização correta do agente avaliador."""
    assert evaluator_agent._running is False
    assert evaluator_agent._evaluation_queue is not None
    assert evaluator_agent._evaluation_locks == {}
    assert evaluator_agent._evaluation_start_times == {}
    assert evaluator_agent._failed_evaluations == {}
    assert evaluator_agent._processing_thread is None
    assert evaluator_agent._verification_thread is None

def test_start_stop_evaluator_agent(evaluator_agent):
    """Testa o início e parada do agente avaliador."""
    evaluator_agent.start()
    assert evaluator_agent._running is True
    assert evaluator_agent._processing_thread is not None
    assert evaluator_agent._verification_thread is not None
    
    evaluator_agent.stop()
    assert evaluator_agent._running is False

def test_evaluate_conversation(mock_db_session, evaluator_agent):
    """Testa a adição de uma conversa à fila de avaliação."""
    conversa_id = 1
    evaluator_agent.evaluate_conversation(conversa_id)
    
    # Verifica se a conversa foi adicionada à fila
    assert not evaluator_agent._evaluation_queue.empty()
    queued_id = evaluator_agent._evaluation_queue.get()
    assert queued_id == conversa_id

def test_check_for_pending_evaluations(mock_db_session, evaluator_agent):
    """Testa a verificação de conversas pendentes para avaliação."""
    # Configurar mock da sessão
    mock_session = Mock()
    mock_db_session.return_value.__enter__.return_value = mock_session
    
    # Configurar mock da query
    mock_conversa = Mock(spec=Conversa)
    mock_conversa.conversa_id = 1
    mock_conversa.mensagens = []
    mock_conversa.solicitacoes = []
    mock_session.query.return_value.filter.return_value.options.return_value.all.return_value = [mock_conversa]
    
    # Executar verificação
    evaluator_agent._check_for_pending_evaluations()
    
    # Verificar se a conversa foi adicionada à fila
    assert not evaluator_agent._evaluation_queue.empty()
    queued_id = evaluator_agent._evaluation_queue.get()
    assert queued_id == 1

def test_check_pending_requests(mock_db_session, evaluator_agent):
    """Testa a verificação de solicitações pendentes."""
    # Configurar mock da sessão
    mock_session = Mock()
    mock_db_session.return_value.__enter__.return_value = mock_session
    
    # Configurar mock da solicitação
    mock_solicitacao = Mock(spec=Solicitacao)
    mock_solicitacao.prazo_prometido = datetime.now() - timedelta(days=1)
    mock_solicitacao.status = SolicitacaoStatus.PENDENTE
    mock_solicitacao.conversa_id = 1
    
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_solicitacao]
    
    # Executar verificação
    evaluator_agent._check_pending_requests()
    
    # Verificar se o status foi atualizado
    assert mock_solicitacao.status == SolicitacaoStatus.ATRASADA

def test_check_reopened_conversations(mock_db_session, evaluator_agent):
    """Testa a verificação de conversas reabertas."""
    # Configurar mock da sessão
    mock_session = Mock()
    mock_db_session.return_value.__enter__.return_value = mock_session
    
    # Configurar mock da conversa
    mock_conversa = Mock(spec=Conversa)
    mock_conversa.conversa_id = 1
    mock_conversa.status = ConversaStatus.ABERTA
    mock_conversa.quantidade_reaberturas = 1
    
    mock_avaliacao = Mock(spec=Avaliacao)
    mock_avaliacao.status_avaliacao = AvaliacaoStatus.AVALIADA
    mock_conversa.avaliacoes = [mock_avaliacao]
    
    mock_session.query.return_value.filter.return_value.options.return_value.all.return_value = [mock_conversa]
    
    # Executar verificação
    evaluator_agent._check_reopened_conversations()
    
    # Verificar se a avaliação foi marcada para reavaliação
    assert mock_avaliacao.status_avaliacao == AvaliacaoStatus.REAVALIACAO_PENDENTE

def test_calculate_response_time(evaluator_agent):
    """Testa o cálculo do tempo de resposta."""
    # Criar mensagens de exemplo
    mensagens = [
        Mock(spec=Mensagem, remetente='cliente', data_hora=datetime.now()),
        Mock(spec=Mensagem, remetente='atendente', data_hora=datetime.now() + timedelta(minutes=5)),
        Mock(spec=Mensagem, remetente='cliente', data_hora=datetime.now() + timedelta(minutes=10)),
        Mock(spec=Mensagem, remetente='atendente', data_hora=datetime.now() + timedelta(minutes=15))
    ]
    
    tempo_resposta = evaluator_agent._calculate_response_time(mensagens)
    assert tempo_resposta == 300  # 5 minutos em segundos

def test_analyze_response_quality(evaluator_agent, mock_conversation_processor):
    """Testa a análise da qualidade da resposta."""
    mensagens = [
        Mock(spec=Mensagem, remetente='atendente', conteudo='Olá, como posso ajudar?')
    ]
    
    qualidade = evaluator_agent._analyze_response_quality(mensagens)
    assert 0 <= qualidade <= 1
    mock_conversation_processor.analyze_response_quality.assert_called_once()

def test_analyze_customer_satisfaction(evaluator_agent, mock_conversation_processor):
    """Testa a análise da satisfação do cliente."""
    mensagens = [
        Mock(spec=Mensagem, remetente='cliente', conteudo='Estou muito satisfeito!')
    ]
    
    satisfacao = evaluator_agent._analyze_customer_satisfaction(mensagens)
    assert 0 <= satisfacao <= 1
    mock_conversation_processor.detect_sentiment.assert_called_once()

def test_calculate_nps(evaluator_agent):
    """Testa o cálculo do NPS."""
    # Teste com diferentes níveis de satisfação
    assert evaluator_agent._calculate_nps(0.0) == 0
    assert evaluator_agent._calculate_nps(0.5) == 5
    assert evaluator_agent._calculate_nps(1.0) == 10

def test_get_conversation_lock(evaluator_agent):
    """Testa a obtenção de locks para conversas."""
    conversa_id = 1
    
    # Primeira chamada deve criar um novo lock
    lock1 = evaluator_agent._get_conversation_lock(conversa_id)
    assert isinstance(lock1, threading.Lock)
    assert conversa_id in evaluator_agent._evaluation_locks
    
    # Segunda chamada deve retornar o mesmo lock
    lock2 = evaluator_agent._get_conversation_lock(conversa_id)
    assert lock1 is lock2

def test_check_evaluation_timeouts(evaluator_agent):
    """Testa a verificação de timeouts nas avaliações."""
    conversa_id = 1
    evaluator_agent._evaluation_start_times[conversa_id] = time.time() - 3600  # 1 hora atrás
    evaluator_agent._evaluation_locks[conversa_id] = threading.Lock()
    
    evaluator_agent._check_evaluation_timeouts()
    
    # Verificar se os registros foram limpos
    assert conversa_id not in evaluator_agent._evaluation_start_times
    assert conversa_id not in evaluator_agent._evaluation_locks

def test_evaluate_conversation_error_handling(mock_db_session, evaluator_agent):
    """Testa o tratamento de erros na avaliação de conversas."""
    # Configurar mock da sessão para simular erro
    mock_session = Mock()
    mock_db_session.return_value.__enter__.return_value = mock_session
    mock_session.query.side_effect = SQLAlchemyError("Erro de banco de dados")
    
    # Executar avaliação
    evaluator_agent._evaluate_conversation(1)
    
    # Verificar se o erro foi registrado
    assert 1 in evaluator_agent._failed_evaluations
    assert evaluator_agent._failed_evaluations[1] == 1

def test_periodic_verification_error_handling(evaluator_agent):
    """Testa o tratamento de erros na verificação periódica."""
    # Configurar mock para simular erro
    with patch.object(evaluator_agent, '_check_for_pending_evaluations', side_effect=Exception("Erro teste")):
        evaluator_agent._running = True
        evaluator_agent._periodic_verification()
        
    # Verificar se o agente continua rodando
    assert evaluator_agent._running is True

def test_init_evaluator_agent(evaluator_agent):
    """Testa a inicialização do EvaluatorAgent."""
    assert evaluator_agent is not None
    assert evaluator_agent.db_session is not None
    assert evaluator_agent.ollama_client is not None
    assert evaluator_agent.check_interval == 60

def test_evaluate_conversation_with_ollama(evaluator_agent):
    """Testa a avaliação de uma conversa com o Ollama."""
    # Criar uma conversa com mensagens
    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="finalizada",
        inicio=datetime.now() - timedelta(hours=1),
        fim=datetime.now(),
    )
    evaluator_agent.db_session.add(conversa)
    
    # Adicionar mensagens
    mensagens = [
        Mensagem(
            conversa=conversa,
            remetente="cliente",
            conteudo="Olá, preciso de ajuda com meu pedido",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=55),
        ),
        Mensagem(
            conversa=conversa,
            remetente="atendente",
            conteudo="Olá! Claro, vou ajudar você. Qual o número do seu pedido?",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=50),
        ),
        Mensagem(
            conversa=conversa,
            remetente="cliente",
            conteudo="O número é #123456",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=45),
        ),
        Mensagem(
            conversa=conversa,
            remetente="atendente",
            conteudo="Entendi. Seu pedido está em separação. Chegará em até 2 dias úteis.",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=40),
        ),
    ]
    evaluator_agent.db_session.add_all(mensagens)
    evaluator_agent.db_session.commit()

    # Avaliar conversa
    evaluator_agent._evaluate_conversation(conversa)
    
    # Verificar se a avaliação foi criada
    avaliacao = evaluator_agent.db_session.execute(
        select(Avaliacao).where(Avaliacao.conversa_id == conversa.id)
    ).scalar_one_or_none()
    
    assert avaliacao is not None
    assert avaliacao.nota_atendimento > 0
    assert avaliacao.nota_tempo_resposta > 0
    assert avaliacao.nota_resolucao > 0

def test_consolidate_metrics(evaluator_agent):
    """Testa a consolidação de métricas de uma conversa."""
    # Criar uma conversa com avaliação
    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="finalizada",
        inicio=datetime.now() - timedelta(hours=1),
        fim=datetime.now(),
        tempo_primeira_resposta=300,
        tempo_medio_resposta=400,
        total_mensagens=4,
    )
    evaluator_agent.db_session.add(conversa)
    
    avaliacao = Avaliacao(
        conversa=conversa,
        nota_atendimento=9.0,
        nota_tempo_resposta=8.5,
        nota_resolucao=9.5,
        tem_reclamacao=False,
    )
    evaluator_agent.db_session.add(avaliacao)
    evaluator_agent.db_session.commit()

    # Consolidar métricas
    evaluator_agent._consolidate_metrics(conversa)
    
    # Verificar se os dados consolidados foram criados
    consolidado = evaluator_agent.db_session.execute(
        select(ConsolidadaAtendimento).where(ConsolidadaAtendimento.conversa_id == conversa.id)
    ).scalar_one_or_none()
    
    assert consolidado is not None
    assert consolidado.nota_media == pytest.approx(9.0, rel=0.1)
    assert consolidado.tempo_medio_resposta == 400
    assert consolidado.total_mensagens == 4

@patch("agent.evaluator_agent.logger")
def test_error_handling(mock_logger, evaluator_agent):
    """Testa o tratamento de erros durante a avaliação."""
    # Criar uma conversa inválida
    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="finalizada",
    )
    evaluator_agent.db_session.add(conversa)
    evaluator_agent.db_session.commit()

    # Forçar um erro na avaliação
    evaluator_agent.ollama_client.generate.side_effect = Exception("Erro de API")
    
    # Tentar avaliar a conversa
    evaluator_agent._evaluate_conversation(conversa)
    
    # Verificar se o erro foi logado
    mock_logger.error.assert_called_once()

def test_priority_queue(evaluator_agent):
    """Testa a fila de prioridade para avaliações."""
    # Criar conversas com diferentes prioridades
    conversas = [
        Conversa(
            cliente_nome=f"Cliente {i}",
            cliente_telefone=f"55119999999{i}",
            status="finalizada",
            inicio=datetime.now() - timedelta(hours=3-i),
            fim=datetime.now() - timedelta(hours=2-i),
        )
        for i in range(3)
    ]
    evaluator_agent.db_session.add_all(conversas)
    evaluator_agent.db_session.commit()

    # Obter conversas para avaliação
    pending_conversations = evaluator_agent._get_pending_evaluations()
    
    # Verificar se as conversas estão ordenadas por prioridade
    assert len(pending_conversations) == 3
    assert pending_conversations[0].inicio < pending_conversations[1].inicio
    assert pending_conversations[1].inicio < pending_conversations[2].inicio 