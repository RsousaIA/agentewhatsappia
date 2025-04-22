import os
import time
import pytest
from loguru import logger
from whatsapp.whatsapp_integration import get_whatsapp_integration

@pytest.fixture
def whatsapp():
    """
    Fixture que fornece uma instância da integração com WhatsApp.
    """
    integration = get_whatsapp_integration()
    yield integration
    integration.stop()

def test_whatsapp_connection(whatsapp):
    """
    Testa a conexão com o WhatsApp.
    """
    # Iniciar integração
    whatsapp.start()
    
    # Aguardar conexão
    time.sleep(5)
    
    # Verificar status
    status = whatsapp.get_connection_status()
    assert status in ['connected', 'authenticated'], f"Status inesperado: {status}"
    
    # Enviar mensagem de teste
    test_number = os.getenv("TEST_WHATSAPP_NUMBER")
    if test_number:
        success = whatsapp.send_message(
            to=test_number,
            content="Teste de integração com WhatsApp"
        )
        assert success, "Falha ao enviar mensagem de teste"

def test_message_handling(whatsapp):
    """
    Testa o processamento de mensagens.
    """
    # Iniciar integração
    whatsapp.start()
    
    # Aguardar conexão
    time.sleep(5)
    
    # Verificar se está conectado
    status = whatsapp.get_connection_status()
    assert status in ['connected', 'authenticated'], f"Status inesperado: {status}"
    
    # Enviar mensagem de teste
    test_number = os.getenv("TEST_WHATSAPP_NUMBER")
    if test_number:
        # Enviar mensagem
        success = whatsapp.send_message(
            to=test_number,
            content="Teste de processamento de mensagens"
        )
        assert success, "Falha ao enviar mensagem de teste"
        
        # Aguardar processamento
        time.sleep(2)

def test_media_handling(whatsapp):
    """
    Testa o envio e processamento de mídia.
    """
    # Iniciar integração
    whatsapp.start()
    
    # Aguardar conexão
    time.sleep(5)
    
    # Verificar se está conectado
    status = whatsapp.get_connection_status()
    assert status in ['connected', 'authenticated'], f"Status inesperado: {status}"
    
    # Enviar mídia de teste
    test_number = os.getenv("TEST_WHATSAPP_NUMBER")
    test_image = os.getenv("TEST_IMAGE_PATH")
    
    if test_number and test_image:
        # Enviar imagem
        success = whatsapp.send_message(
            to=test_number,
            content="Teste de envio de imagem",
            media_path=test_image
        )
        assert success, "Falha ao enviar imagem de teste"
        
        # Aguardar processamento
        time.sleep(2)

def test_reconnection(whatsapp):
    """
    Testa a reconexão automática.
    """
    # Iniciar integração
    whatsapp.start()
    
    # Aguardar conexão
    time.sleep(5)
    
    # Verificar status inicial
    status = whatsapp.get_connection_status()
    assert status in ['connected', 'authenticated'], f"Status inesperado: {status}"
    
    # Simular desconexão
    whatsapp.client.disconnect()
    
    # Aguardar reconexão
    time.sleep(10)
    
    # Verificar se reconectou
    status = whatsapp.get_connection_status()
    assert status in ['connected', 'authenticated'], f"Status inesperado após reconexão: {status}" 