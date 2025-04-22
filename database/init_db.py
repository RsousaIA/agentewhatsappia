#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from loguru import logger

# Adicionar o diretório raiz ao path
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Importar modelos
from database.models import Base
from database.db_setup import init_db as setup_init_db

def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas necessárias.
    Esta função é chamada pelo script de inicialização.
    """
    try:
        # Inicializar banco de dados usando a função do db_setup
        setup_init_db()
        logger.info("Banco de dados inicializado com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise

if __name__ == "__main__":
    # Se executado diretamente, inicializa o banco de dados
    init_db()
    print("Banco de dados inicializado com sucesso!") 