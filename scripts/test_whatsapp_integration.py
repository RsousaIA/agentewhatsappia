import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from google.cloud import firestore

# Adiciona o diretório raiz ao path para importar os módulos
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

from whatsapp.whatsapp_integration import get_whatsapp_integration
from database.firebase_db import init_firebase, get_firestore_db

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_whatsapp_connection():
    """Testa a conexão com o WhatsApp"""
    try:
        logger.info("Iniciando teste de conexão com WhatsApp...")
        whatsapp = get_whatsapp_integration()
        
        # Inicia a integração
        whatsapp.start()
        logger.info("Conexão com WhatsApp iniciada com sucesso")
        
        # Aguarda 5 segundos para verificar o status
        time.sleep(5)
        
        # Verifica o status da conexão
        status = whatsapp.get_connection_status()
        logger.info(f"Status da conexão: {status}")
        
        # Para a integração
        whatsapp.stop()
        logger.info("Conexão com WhatsApp encerrada")
        
        return status == "connected"
        
    except Exception as e:
        logger.error(f"Erro ao testar conexão com WhatsApp: {e}")
        return False

def test_message_storage():
    """Testa o armazenamento de mensagens no Firebase"""
    try:
        logger.info("Iniciando teste de armazenamento de mensagens...")
        
        # Inicializa o Firebase
        init_firebase()
        db = get_firestore_db()
        
        # Cria uma mensagem de teste
        test_message = {
            "conversation_id": "test_conversation",
            "text": "Mensagem de teste",
            "sender": "test_user",
            "timestamp": datetime.now(),
            "status": "received",
            "metadata": {
                "test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Salva a mensagem
        db.collection("mensagens").add(test_message)
        logger.info("Mensagem de teste salva com sucesso")
        
        # Recupera a mensagem
        test_messages = db.collection("mensagens")\
            .where(filter=firestore.FieldFilter("conversation_id", "==", "test_conversation"))\
            .where(filter=firestore.FieldFilter("metadata.test", "==", True))\
            .stream()
            
        for message in test_messages:
            logger.info(f"Mensagem recuperada: {message.to_dict()}")
            
        # Limpa a mensagem de teste
        for message in test_messages:
            message.reference.delete()
        logger.info("Mensagem de teste removida")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao testar armazenamento de mensagens: {e}")
        return False

def main():
    """Função principal de teste"""
    logger.info("Iniciando testes de integração...")
    
    # Testa a conexão com WhatsApp
    whatsapp_test = test_whatsapp_connection()
    logger.info(f"Teste de conexão WhatsApp: {'Sucesso' if whatsapp_test else 'Falha'}")
    
    # Testa o armazenamento de mensagens
    storage_test = test_message_storage()
    logger.info(f"Teste de armazenamento: {'Sucesso' if storage_test else 'Falha'}")
    
    # Resultado final
    if whatsapp_test and storage_test:
        logger.info("Todos os testes passaram com sucesso!")
    else:
        logger.error("Alguns testes falharam. Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    main() 