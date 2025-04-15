import os
import time
import signal
import sys
from dotenv import load_dotenv
from loguru import logger
from agent.collector_agent import CollectorAgent

# Configura logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/agente_coletor_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="INFO",
    compression="zip"
)

# Carrega variáveis de ambiente
load_dotenv()

# Configura o nível de log
log_level = os.getenv("LOG_LEVEL", "INFO")
logger.level(log_level)

def signal_handler(sig, frame):
    """
    Manipulador de sinais para interrupção (Ctrl+C)
    """
    logger.info("Recebido sinal de interrupção. Encerrando agentes...")
    if collector_agent:
        collector_agent.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Registra manipulador de sinais
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inicializa o agente coletor
    collector_agent = CollectorAgent()
    
    try:
        # Inicia o agente coletor
        logger.info("Iniciando Agente Coletor de WhatsApp...")
        collector_agent.start()
        
        # Mantém o programa em execução
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        if collector_agent:
            collector_agent.stop()
        sys.exit(1) 