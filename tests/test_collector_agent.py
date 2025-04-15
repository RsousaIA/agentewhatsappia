"""Testes para o CollectorAgent."""
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger
from sqlalchemy import select

from agent.collector_agent import CollectorAgent
from database.models import Conversa, Mensagem, Solicitacao
from whatsapp.api_client import WhatsAppAPIClient


@pytest.fixture
def mock_whatsapp_client():
    """Mock do cliente WhatsApp."""
    client = MagicMock(spec=WhatsAppAPIClient)
    client.get_messages.return_value = []
    return client


@pytest.fixture
def collector_agent(db_session, mock_whatsapp_client, temp_env_file):
    """Fixture que cria uma instância do CollectorAgent para testes."""
    agent = CollectorAgent()
    agent.db_session = db_session
    agent.whatsapp_client = mock_whatsapp_client
    return agent


def test_init_collector_agent(collector_agent):
    """Testa a inicialização do CollectorAgent."""
    assert collector_agent is not None
    assert collector_agent.db_session is not None
    assert collector_agent.whatsapp_client is not None
    assert collector_agent.check_interval == 60
    assert collector_agent.inactivity_threshold == 3600


def test_start_stop_collector_agent(collector_agent):
    """Testa os métodos start e stop do CollectorAgent."""
    collector_agent.start()
    assert collector_agent.is_running
    collector_agent.stop()
    assert not collector_agent.is_running


@pytest.mark.parametrize(
    "message_type,message_content",
    [
        ("text", {"body": "Olá, preciso de ajuda"}),
        ("image", {"caption": "Imagem do problema", "id": "123"}),
        ("document", {"caption": "Relatório", "filename": "report.pdf", "id": "456"}),
    ],
)
def test_process_message(collector_agent, message_type, message_content):
    """Testa o processamento de diferentes tipos de mensagens."""
    message = {
        "type": message_type,
        "from": "5511999999999",
        "timestamp": datetime.now().timestamp(),
        message_type: message_content,
    }

    collector_agent._process_message(message)
    
    result = collector_agent.db_session.execute(
        select(Mensagem).where(Mensagem.tipo == message_type)
    ).scalar_one_or_none()
    
    assert result is not None
    assert result.tipo == message_type
    if message_type == "text":
        assert result.conteudo == message_content["body"]
    else:
        assert json.loads(result.conteudo)["caption"] == message_content["caption"]


def test_check_inactive_conversations(collector_agent):
    """Testa a verificação de conversas inativas."""
    # Criar uma conversa antiga
    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="em_andamento",
        ultima_interacao=datetime.now() - timedelta(hours=2),
    )
    collector_agent.db_session.add(conversa)
    collector_agent.db_session.commit()

    collector_agent._check_inactive_conversations()
    
    updated_conversa = collector_agent.db_session.get(Conversa, conversa.id)
    assert updated_conversa.status == "finalizada"


def test_detect_request(collector_agent):
    """Testa a detecção de solicitações em mensagens."""
    message = {
        "type": "text",
        "from": "5511999999999",
        "timestamp": datetime.now().timestamp(),
        "text": {"body": "Preciso que você me ajude com um problema urgente"},
    }

    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="em_andamento",
    )
    collector_agent.db_session.add(conversa)
    collector_agent.db_session.commit()

    collector_agent._process_message(message)
    
    result = collector_agent.db_session.execute(
        select(Solicitacao).join(Conversa)
        .where(Conversa.cliente_telefone == "5511999999999")
    ).scalar_one_or_none()
    
    assert result is not None
    assert result.status == "pendente"
    assert "problema urgente" in result.descricao


@patch("agent.collector_agent.logger")
def test_error_handling(mock_logger, collector_agent):
    """Testa o tratamento de erros durante o processamento de mensagens."""
    collector_agent.whatsapp_client.get_messages.side_effect = Exception("Erro de API")
    
    collector_agent._fetch_new_messages()
    
    mock_logger.error.assert_called_once()


def test_conversation_metrics(collector_agent):
    """Testa o cálculo de métricas da conversa."""
    # Criar uma conversa com mensagens
    conversa = Conversa(
        cliente_nome="Cliente Teste",
        cliente_telefone="5511999999999",
        status="em_andamento",
        inicio=datetime.now() - timedelta(minutes=30),
    )
    collector_agent.db_session.add(conversa)
    
    # Adicionar mensagens
    mensagens = [
        Mensagem(
            conversa=conversa,
            remetente="cliente",
            conteudo="Olá, preciso de ajuda",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=25),
        ),
        Mensagem(
            conversa=conversa,
            remetente="atendente",
            conteudo="Olá! Como posso ajudar?",
            tipo="text",
            timestamp=datetime.now() - timedelta(minutes=20),
        ),
    ]
    collector_agent.db_session.add_all(mensagens)
    collector_agent.db_session.commit()

    collector_agent._update_conversation_metrics(conversa)
    
    assert conversa.tempo_primeira_resposta is not None
    assert conversa.tempo_medio_resposta is not None
    assert conversa.total_mensagens == 2 