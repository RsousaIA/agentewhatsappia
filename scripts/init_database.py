import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from database.schema import FirebaseSchema

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Iniciando configuração do banco de dados...")
        
        # Inicializa o schema
        schema = FirebaseSchema()
        
        # Configura a estrutura inicial
        success = schema.setup_database()
        
        if success:
            logger.info("Banco de dados configurado com sucesso!")
        else:
            logger.error("Falha ao configurar banco de dados")
            
    except Exception as e:
        logger.error(f"Erro durante a configuração: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 