import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

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

def parse_arguments():
    parser = argparse.ArgumentParser(description='Script de migração de dados')
    parser.add_argument('--backup-dir', type=str, default='backups',
                        help='Diretório para armazenar os backups')
    parser.add_argument('--rollback', action='store_true',
                        help='Executa rollback do último backup')
    parser.add_argument('--force', action='store_true',
                        help='Força a execução sem confirmação')
    return parser.parse_args()

def ensure_backup_dir(backup_dir):
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    return backup_dir

def confirm_execution():
    response = input("Deseja continuar com a migração? (s/n): ")
    return response.lower() == 's'

def main():
    args = parse_arguments()
    
    try:
        if args.rollback:
            logger.info("Iniciando rollback...")
            if not args.force and not confirm_execution():
                logger.info("Rollback cancelado pelo usuário")
                return
            
            backup_dir = ensure_backup_dir(args.backup_dir)
            migration_manager.restore_from_backup(backup_dir)
            logger.info("Rollback concluído com sucesso!")
            return
            
        logger.info("Iniciando processo de migração...")
        if not args.force and not confirm_execution():
            logger.info("Migração cancelada pelo usuário")
            return
            
        backup_dir = ensure_backup_dir(args.backup_dir)
        result = migration_manager.run_all_migrations(backup_dir)
        
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