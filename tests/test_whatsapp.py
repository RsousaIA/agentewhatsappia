"""Testes para o cliente WhatsApp."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from whatsapp.api_client import WhatsAppAPIClient


@pytest.fixture
def mock_response():
    """Mock de resposta da API."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "messages": [
            {
                "id": "wamid.123",
                "from": "5511999999999",
                "timestamp": datetime.now().timestamp(),
                "type": "text",
                "text": {"body": "Olá, preciso de ajuda"},
            }
        ]
    }
    return response


@pytest.fixture
def whatsapp_client():
    """Fixture que cria uma instância do WhatsAppAPIClient para testes."""
    return WhatsAppAPIClient(
        api_token="test_token",
        phone_number_id="123456789",
        business_account_id="987654321",
        api_version="v17.0",
    )


def test_init_whatsapp_client(whatsapp_client):
    """Testa a inicialização do cliente WhatsApp."""
    assert whatsapp_client.api_token == "test_token"
    assert whatsapp_client.phone_number_id == "123456789"
    assert whatsapp_client.business_account_id == "987654321"
    assert whatsapp_client.api_version == "v17.0"
    assert whatsapp_client.base_url == "https://graph.facebook.com/v17.0"


def test_get_messages(whatsapp_client, mock_response):
    """Testa a obtenção de mensagens."""
    with patch("requests.get", return_value=mock_response):
        messages = whatsapp_client.get_messages()
        assert len(messages) == 1
        assert messages[0]["type"] == "text"
        assert messages[0]["from"] == "5511999999999"
        assert "Olá, preciso de ajuda" in messages[0]["text"]["body"]


def test_send_text_message(whatsapp_client, mock_response):
    """Testa o envio de mensagem de texto."""
    with patch("requests.post", return_value=mock_response):
        response = whatsapp_client.send_text_message(
            to="5511999999999",
            text="Olá! Como posso ajudar?",
        )
        assert response.status_code == 200


def test_send_template_message(whatsapp_client, mock_response):
    """Testa o envio de mensagem de template."""
    with patch("requests.post", return_value=mock_response):
        response = whatsapp_client.send_template_message(
            to="5511999999999",
            template_name="welcome_message",
            language_code="pt_BR",
            components=[],
        )
        assert response.status_code == 200


def test_mark_message_as_read(whatsapp_client, mock_response):
    """Testa a marcação de mensagem como lida."""
    with patch("requests.post", return_value=mock_response):
        response = whatsapp_client.mark_message_as_read(
            message_id="wamid.123",
        )
        assert response.status_code == 200


def test_api_error_handling(whatsapp_client):
    """Testa o tratamento de erros da API."""
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.json.return_value = {
        "error": {
            "message": "Invalid OAuth access token",
            "type": "OAuthException",
            "code": 190,
        }
    }

    with patch("requests.get", return_value=error_response):
        with pytest.raises(requests.exceptions.HTTPError):
            whatsapp_client.get_messages()


def test_network_error_handling(whatsapp_client):
    """Testa o tratamento de erros de rede."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(requests.exceptions.ConnectionError):
            whatsapp_client.get_messages()


def test_rate_limit_handling(whatsapp_client):
    """Testa o tratamento de rate limit."""
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.headers = {"Retry-After": "60"}

    with patch("requests.get", return_value=rate_limit_response):
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            whatsapp_client.get_messages()
        assert "429" in str(exc_info.value)


@pytest.mark.parametrize(
    "message_type,message_content",
    [
        ("text", {"body": "Olá, preciso de ajuda"}),
        ("image", {"caption": "Imagem do problema", "id": "123"}),
        ("document", {"caption": "Relatório", "filename": "report.pdf", "id": "456"}),
    ],
)
def test_different_message_types(whatsapp_client, message_type, message_content):
    """Testa o processamento de diferentes tipos de mensagens."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "messages": [
            {
                "id": "wamid.123",
                "from": "5511999999999",
                "timestamp": datetime.now().timestamp(),
                "type": message_type,
                message_type: message_content,
            }
        ]
    }

    with patch("requests.get", return_value=response):
        messages = whatsapp_client.get_messages()
        assert len(messages) == 1
        assert messages[0]["type"] == message_type
        assert messages[0][message_type] == message_content


def test_authentication_headers(whatsapp_client):
    """Testa os headers de autenticação."""
    with patch("requests.get") as mock_get:
        whatsapp_client.get_messages()
        headers = mock_get.call_args.kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json" 