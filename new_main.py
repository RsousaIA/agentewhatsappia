"""
Ponto de entrada principal da aplicação.
Gerencia a inicialização e coordenação dos agentes de análise.
"""

import os
import time
import signal
import sys
import argparse
from dotenv import load_dotenv
from loguru import logger
from agent import init_agents
from database.firebase_db import init_firebase

# Configuração de logs
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
logger.add(
    "logs/debug.log",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
logger.add(
    "logs/error.log",
    level="ERROR",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de nível de log
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.level(log_level)

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
    try:
        # Parar agentes
        collector.stop()
        evaluator.stop()
        logger.info("Agentes parados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao parar aplicação: {e}")
    finally:
        logger.info("Aplicação encerrada")
        sys.exit(0)

def main():
    """
    Função principal da aplicação.
    """
    global collector, evaluator
    
    try:
        # Configurar handler para sinais de interrupção
        signal.signal(signal.SIGINT, handle_interrupt)
        signal.signal(signal.SIGTERM, handle_interrupt)
        
        # Inicializa o Firebase
        logger.info("Inicializando conexão com o Firebase...")
        init_firebase()
        logger.info("Conexão com o Firebase estabelecida com sucesso")
        
        # Inicia os agentes usando a função init_agents que configura a fila compartilhada
        logger.info("Iniciando agentes de análise...")
        collector, evaluator = init_agents()
        
        collector.start()
        evaluator.start()
        
        logger.info("Agentes iniciados com sucesso!")
        
        try:
            # Mantém o programa rodando
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nEncerrando agentes...")
            collector.stop()
            evaluator.stop()
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        stop_application()

if __name__ == "__main__":
    main() 