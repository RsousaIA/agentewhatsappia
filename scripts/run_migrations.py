import os
import sys
import logging
from datetime import datetime

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.migrations import migration_manager

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Iniciando processo de migração...")
        
        # Executa todas as migrações
        result = migration_manager.run_all_migrations()
        
        logger.info(f"Backup criado: {result['backup_file']}")
        logger.info("Resultados das migrações:")
        for collection, count in result['results'].items():
            logger.info(f"- {collection}: {count} documentos migrados")
            
        logger.info("Processo de migração concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o processo de migração: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 