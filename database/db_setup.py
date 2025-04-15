import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from loguru import logger

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///whatsapp_monitor.db')

# Criar engine do SQLAlchemy com configurações específicas para cada tipo de banco
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False}  # Necessário para SQLite
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )

# Criar fábrica de sessões
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# Criar base declarativa para os modelos
Base = declarative_base()

def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas necessárias.
    """
    try:
        # Importar todos os modelos para que sejam registrados
        from .models import Conversa, Mensagem, Solicitacao, Avaliacao, ConsolidadaAtendimento
        
        # Criar todas as tabelas
        Base.metadata.create_all(engine)
        logger.info("Banco de dados inicializado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise

def get_session():
    """
    Retorna uma nova sessão do banco de dados.
    
    Returns:
        Session: Sessão do SQLAlchemy
    """
    return Session()

def cleanup_session():
    """
    Limpa a sessão atual do registro de thread.
    Deve ser chamado ao final de cada operação.
    """
    Session.remove()

class DatabaseManager:
    """
    Gerenciador de conexão com o banco de dados usando context manager.
    """
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        """
        Inicia uma nova sessão do banco de dados.
        
        Returns:
            Session: Sessão do SQLAlchemy
        """
        self.session = get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Fecha a sessão do banco de dados.
        
        Args:
            exc_type: Tipo da exceção, se houver
            exc_val: Valor da exceção
            exc_tb: Traceback da exceção
        """
        try:
            if exc_type is not None:
                # Se houve exceção, fazer rollback
                self.session.rollback()
                logger.warning(f"Rollback realizado devido a erro: {exc_val}")
            else:
                # Se não houve exceção, commit
                self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Erro ao finalizar transação: {e}")
            raise
            
        finally:
            # Sempre fechar a sessão
            self.session.close()
            cleanup_session()

# Função auxiliar para usar o DatabaseManager
def with_db_session(func):
    """
    Decorator para gerenciar sessões do banco de dados.
    
    Args:
        func: Função a ser decorada
        
    Returns:
        wrapper: Função decorada
    """
    def wrapper(*args, **kwargs):
        with DatabaseManager() as session:
            return func(session, *args, **kwargs)
    return wrapper 