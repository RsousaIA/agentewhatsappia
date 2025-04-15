import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from .models import Base

# Carrega as variáveis de ambiente
load_dotenv()

# Obtém a URL do banco de dados a partir das variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agentewhatsapp.db")

# Cria o motor de banco de dados
engine = create_engine(DATABASE_URL, echo=False)

# Cria uma fábrica de sessões
session_factory = sessionmaker(bind=engine)
SessionLocal = scoped_session(session_factory)

def init_db():
    """Inicializa o banco de dados criando todas as tabelas definidas"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Obtém uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def get_engine():
    """Retorna o motor do banco de dados"""
    return engine 