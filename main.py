import os
import time
import signal
import sys
import logging
from dotenv import load_dotenv
from loguru import logger
from whatsapp.whatsapp_integration import get_whatsapp_integration
from agent.collector_agent import get_collector_agent
from agent.evaluator_agent import get_evaluator_agent

# Configura logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/app.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Configuração de logs específica para depuração
logger.add(
    "logs/debug.log",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Carrega variáveis de ambiente
load_dotenv()

# Configura o nível de log
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.level(log_level)

# Variáveis globais para controle
collector_agent = None
evaluator_agent = None
whatsapp_integration = None

def handle_interrupt(signum, frame):
    """
    Manipula sinais de interrupção (Ctrl+C).
    """
    logger.info("Recebido sinal de interrupção. Encerrando aplicação...")
    stop_application()

def stop_application():
    """
    Para a aplicação de forma segura.
    """
    global collector_agent, evaluator_agent, whatsapp_integration
    
    try:
        # Parar agente coletor
        if collector_agent:
            logger.info("Parando Agente Coletor...")
            collector_agent.stop()
            logger.info("Agente Coletor parado com sucesso")
        
        # Parar agente avaliador
        if evaluator_agent:
            logger.info("Parando Agente Avaliador...")
            evaluator_agent.stop()
            logger.info("Agente Avaliador parado com sucesso")
        
        # Parar integração com WhatsApp
        if whatsapp_integration:
            logger.info("Parando integração com WhatsApp...")
            whatsapp_integration.stop()
            logger.info("Integração com WhatsApp parada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao parar aplicação: {e}")
    
    finally:
        sys.exit(0)

def main():
    """
    Função principal da aplicação.
    """
    global collector_agent, evaluator_agent, whatsapp_integration
    
    try:
        # Configurar handler para sinais de interrupção
        signal.signal(signal.SIGINT, handle_interrupt)
        signal.signal(signal.SIGTERM, handle_interrupt)
        
        logger.info("Iniciando aplicação...")
        
        # Iniciar agente coletor
        logger.info("Iniciando Agente Coletor...")
        collector_agent = get_collector_agent()
        if collector_agent:
            collector_agent.start()
            logger.info("Agente Coletor iniciado com sucesso")
            logger.info("Agente Coletor configurado para processar mensagens")
        else:
            logger.error("Falha ao inicializar Agente Coletor")
            raise Exception("Falha ao inicializar Agente Coletor")
        
        # Iniciar agente avaliador
        logger.info("Iniciando Agente Avaliador...")
        evaluator_agent = get_evaluator_agent()
        if evaluator_agent:
            evaluator_agent.start()
            logger.info("Agente Avaliador iniciado com sucesso")
            logger.info("Agente Avaliador configurado para avaliar conversas")
        else:
            logger.error("Falha ao inicializar Agente Avaliador")
            raise Exception("Falha ao inicializar Agente Avaliador")
        
        # Iniciar integração com WhatsApp
        logger.info("Iniciando integração com WhatsApp...")
        whatsapp_integration = get_whatsapp_integration()
        if whatsapp_integration:
            whatsapp_integration.start()
            logger.info("Integração com WhatsApp iniciada com sucesso")
        else:
            logger.error("Falha ao inicializar integração com WhatsApp")
            raise Exception("Falha ao inicializar integração com WhatsApp")
        
        # Registrar o agente coletor na integração com WhatsApp para receber mensagens
        whatsapp_integration.register_message_handler(collector_agent.process_message)
        logger.info("Agente Coletor registrado para receber mensagens do WhatsApp")
        
        logger.info("Sistema completo iniciado e funcionando!")
        logger.info("Agente Avaliador verificará conversas fechadas periodicamente")
        logger.info("Agente Coletor está monitorando novas mensagens")
        
        # Manter aplicação rodando
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        logger.error("Detalhes do erro:", exc_info=True)
        stop_application()

if __name__ == "__main__":
    main() 