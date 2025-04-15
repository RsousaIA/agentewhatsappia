import pytest
import os
import sys
from pathlib import Path
import tempfile
from typing import Generator
import datetime

# Adicionar o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente para testes
os.environ['TESTING'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['TIMEZONE'] = 'America/Sao_Paulo'

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.db_setup import Base
from database.models import (
    Avaliacao,
    Conversa,
    ConsolidadaAtendimento,
    Mensagem,
    Solicitacao,
)

@pytest.fixture(scope="session")
def db_engine():
    """Cria um engine SQLite em memória para os testes."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """Cria uma fábrica de sessões do SQLAlchemy."""
    return sessionmaker(bind=db_engine)

@pytest.fixture(scope="function")
def db_session(db_session_factory) -> Generator[Session, None, None]:
    """Fornece uma sessão do SQLAlchemy para cada teste."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def temp_env_file():
    """Cria um arquivo .env temporário para os testes."""
    env_content = """
    WHATSAPP_API_TOKEN=test_token
    WHATSAPP_PHONE_NUMBER_ID=123456789
    WHATSAPP_BUSINESS_ACCOUNT_ID=987654321
    WHATSAPP_API_VERSION=v17.0
    DATABASE_URL=sqlite:///:memory:
    OLLAMA_API_URL=http://localhost:11434
    DEEPSEEK_MODEL=deepseek-coder:6.7b
    LOG_LEVEL=DEBUG
    TIMEZONE=America/Sao_Paulo
    """
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        temp_file.write(env_content)
        temp_path = temp_file.name
    
    original_env = os.environ.copy()
    try:
        yield temp_path
    finally:
        os.unlink(temp_path)
        os.environ.clear()
        os.environ.update(original_env)

@pytest.fixture(autouse=True)
def setup_database(db_engine, db_session):
    """Fixture para configurar o banco de dados antes de cada teste."""
    from database.models import Base
    from database.db_setup import init_db
    
    # Criar todas as tabelas
    init_db()
    
    yield
    
    # Limpar o banco após cada teste
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()

@pytest.fixture
def mock_logger():
    """Fixture para mock do logger."""
    import logging
    logger = logging.getLogger('test')
    logger.setLevel(logging.DEBUG)
    return logger

@pytest.fixture
def mock_time():
    """Fixture para mock do módulo time."""
    import time
    original_time = time.time
    time.time = lambda: 1234567890.0
    yield
    time.time = original_time

@pytest.fixture
def mock_datetime():
    """Fixture para mock do módulo datetime."""
    import datetime
    original_datetime = datetime.datetime
    datetime.datetime = type('datetime', (), {
        'now': lambda: original_datetime(2024, 1, 1, 12, 0, 0),
        'utcnow': lambda: original_datetime(2024, 1, 1, 15, 0, 0),
        'fromtimestamp': original_datetime.fromtimestamp,
        'strptime': original_datetime.strptime
    })
    yield
    datetime.datetime = original_datetime

@pytest.fixture
def sample_conversation(db_session):
    """Fixture para criar uma conversa de exemplo."""
    from database.models import Conversa, Mensagem
    
    conversa = Conversa(
        nome_cliente='Cliente Teste',
        nome_atendente='Atendente Teste',
        status='aberta',
        data_inicio=datetime.datetime.now(),
        data_ultima_mensagem=datetime.datetime.now()
    )
    
    db_session.add(conversa)
    db_session.commit()
    
    mensagem = Mensagem(
        conversa_id=conversa.conversa_id,
        remetente='cliente',
        conteudo='Olá, preciso de ajuda',
        data_hora=datetime.datetime.now()
    )
    
    db_session.add(mensagem)
    db_session.commit()
    
    return conversa

@pytest.fixture
def sample_request(db_session, sample_conversation):
    """Fixture para criar uma solicitação de exemplo."""
    from database.models import Solicitacao
    
    solicitacao = Solicitacao(
        conversa_id=sample_conversation.conversa_id,
        descricao='Solicitação de teste',
        status='pendente',
        prazo_prometido=datetime.datetime.now() + datetime.timedelta(days=1)
    )
    
    db_session.add(solicitacao)
    db_session.commit()
    
    return solicitacao

@pytest.fixture
def sample_evaluation(db_session, sample_conversation):
    """Fixture para criar uma avaliação de exemplo."""
    from database.models import Avaliacao
    
    avaliacao = Avaliacao(
        conversa_id=sample_conversation.conversa_id,
        status_avaliacao='pendente'
    )
    
    db_session.add(avaliacao)
    db_session.commit()
    
    return avaliacao

@pytest.fixture
def sample_consolidated(db_session, sample_conversation):
    """Fixture para criar dados consolidados de exemplo."""
    from database.models import ConsolidadaAtendimento
    
    consolidada = ConsolidadaAtendimento(
        conversa_id=sample_conversation.conversa_id,
        tempo_total=3600,
        tempo_medio_resposta=300,
        quantidade_mensagens=10,
        quantidade_solicitacoes=2,
        quantidade_solicitacoes_atendidas=1,
        quantidade_solicitacoes_atrasadas=0,
        score_geral=0.8,
        quantidade_reclamacoes=0,
        quantidade_reaberturas=0
    )
    
    db_session.add(consolidada)
    db_session.commit()
    
    return consolidada 