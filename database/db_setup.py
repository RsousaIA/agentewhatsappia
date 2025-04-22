# Stub para SQLAlchemy - desabilitado temporariamente para permitir execução do sistema
# devido a incompatibilidade com Python 3.13

import os
from dotenv import load_dotenv
from loguru import logger
import contextlib

# Carrega variáveis de ambiente
load_dotenv()

# Classe stub para simular DatabaseManager
class DatabaseManager:
    def __init__(self):
        self.connected = False
    
    def connect(self):
        logger.warning("SQLAlchemy stub sendo utilizado - recursos de banco de dados SQL estão desabilitados")
        self.connected = True
        return self
        
    def disconnect(self):
        self.connected = False
        return self
    
    def is_connected(self):
        return self.connected

# Inicializa o banco de dados
def init_db():
    """
    Stub para inicializar o banco de dados.
    """
    logger.warning("SQLAlchemy desabilitado - usando apenas Firebase")
    return True

# Obtém uma sessão do banco de dados
def get_session():
    """
    Stub para obter uma sessão do banco de dados.
    """
    logger.warning("SQLAlchemy desabilitado - usando apenas Firebase")
    return None

# Contexto de sessão de banco de dados
@contextlib.contextmanager
def with_db_session():
    """
    Stub para gerenciador de contexto de sessão.
    """
    logger.warning("SQLAlchemy desabilitado - usando apenas Firebase")
    yield None 