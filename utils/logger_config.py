import os
import sys
from datetime import datetime
from loguru import logger

def setup_logger():
    """
    Configura o logger do sistema com os níveis e formatos apropriados.
    """
    # Remover o handler padrão
    logger.remove()
    
    # Obter o nível de log das variáveis de ambiente ou usar INFO como padrão
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Criar diretório de logs se não existir
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Nome do arquivo de log com data
    log_file = os.path.join(log_dir, f"whatsapp_monitor_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Formato do log
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Adicionar handler para console
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Adicionar handler para arquivo
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="00:00",  # Criar novo arquivo à meia-noite
        retention="30 days",  # Manter logs por 30 dias
        compression="zip",  # Comprimir logs antigos
        enqueue=True  # Thread-safe
    )
    
    # Configurar captura de exceções não tratadas
    def handle_exception(exc_type, exc_value, exc_traceback):
        """
        Handler para exceções não tratadas
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Não logar KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Exceção não tratada:")
    
    sys.excepthook = handle_exception
    
    logger.info("Logger configurado com sucesso")

# Níveis de log personalizados
logger.level("REQUEST", no=15, color="<cyan>")
logger.level("RESPONSE", no=25, color="<yellow>")

def log_request(message: str, **kwargs):
    """
    Registra uma mensagem de requisição com nível personalizado.
    
    Args:
        message: Mensagem a ser registrada
        **kwargs: Argumentos adicionais para o logger
    """
    logger.log("REQUEST", message, **kwargs)

def log_response(message: str, **kwargs):
    """
    Registra uma mensagem de resposta com nível personalizado.
    
    Args:
        message: Mensagem a ser registrada
        **kwargs: Argumentos adicionais para o logger
    """
    logger.log("RESPONSE", message, **kwargs)

# Configurar logger ao importar o módulo
setup_logger() 