import os
import sys
import pytest
from loguru import logger

def main():
    """
    Executa os testes da aplicação.
    """
    try:
        logger.info("Iniciando testes...")
        
        # Configurar logger para os testes
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.add(
            "logs/tests.log",
            rotation="1 day",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Executar testes
        pytest.main([
            "-v",  # Verbose
            "--tb=short",  # Formato curto do traceback
            "--log-cli-level=INFO",  # Nível de log no console
            "tests/"  # Diretório dos testes
        ])
        
    except Exception as e:
        logger.error(f"Erro ao executar testes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 