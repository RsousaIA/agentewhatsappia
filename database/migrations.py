import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging
from firebase_admin import firestore
from .firebase_db import get_firestore_db
from .cache import cache_manager

logger = logging.getLogger(__name__)

class MigrationManager:
    def __init__(self):
        self.db = get_firestore_db()
        self.migrations_dir = 'migrations'
        self._ensure_migrations_dir()
        
    def _ensure_migrations_dir(self):
        """Garante que o diretório de migrações existe"""
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)
            
    def _get_migration_files(self) -> List[str]:
        """Retorna a lista de arquivos de migração ordenados"""
        files = [f for f in os.listdir(self.migrations_dir) if f.endswith('.json')]
        return sorted(files)
        
    def _load_migration(self, filename: str) -> Dict:
        """Carrega um arquivo de migração"""
        with open(os.path.join(self.migrations_dir, filename), 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def _save_migration(self, filename: str, data: Dict):
        """Salva um arquivo de migração"""
        with open(os.path.join(self.migrations_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def _get_collection_data(self, collection: str) -> List[Dict]:
        """Obtém todos os documentos de uma coleção"""
        docs = self.db.collection(collection).stream()
        return [doc.to_dict() for doc in docs]
        
    def _restore_collection_data(self, collection: str, data: List[Dict]):
        """Restaura dados em uma coleção"""
        batch = self.db.batch()
        for doc_data in data:
            doc_ref = self.db.collection(collection).document()
            batch.set(doc_ref, doc_data)
        batch.commit()
        
    def backup_all_collections(self):
        """Faz backup de todas as coleções"""
        collections = [
            'conversas',
            'mensagens',
            'solicitacoes',
            'avaliacoes',
            'consolidada_atendimentos'
        ]
        
        backup_data = {}
        for collection in collections:
            backup_data[collection] = self._get_collection_data(collection)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        self._save_migration(filename, backup_data)
        
        logger.info(f"Backup criado com sucesso: {filename}")
        return filename
        
    def restore_from_backup(self, filename: str):
        """Restaura dados de um backup"""
        backup_data = self._load_migration(filename)
        
        # Limpa o cache antes da restauração
        cache_manager.clear()
        
        for collection, data in backup_data.items():
            self._restore_collection_data(collection, data)
            
        logger.info(f"Dados restaurados com sucesso do backup: {filename}")
        
    def migrate_conversations(self):
        """Migra dados antigos de conversas para o novo formato"""
        try:
            conversations = self._get_collection_data('conversas')
            migrated_count = 0
            
            for conversation in conversations:
                # Verifica se precisa de migração
                if 'data_criacao' not in conversation:
                    conversation['data_criacao'] = firestore.SERVER_TIMESTAMP
                    conversation['ultima_atualizacao'] = firestore.SERVER_TIMESTAMP
                    
                    # Atualiza o documento
                    doc_ref = self.db.collection('conversas').document(conversation['id'])
                    doc_ref.set(conversation)
                    migrated_count += 1
                    
            logger.info(f"Migração de conversas concluída. {migrated_count} documentos migrados.")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erro na migração de conversas: {e}")
            raise
            
    def migrate_messages(self):
        """Migra dados antigos de mensagens para o novo formato"""
        try:
            messages = self._get_collection_data('mensagens')
            migrated_count = 0
            
            for message in messages:
                # Verifica se precisa de migração
                if 'timestamp' not in message:
                    message['timestamp'] = firestore.SERVER_TIMESTAMP
                    
                    # Atualiza o documento
                    doc_ref = self.db.collection('mensagens').document(message['id'])
                    doc_ref.set(message)
                    migrated_count += 1
                    
            logger.info(f"Migração de mensagens concluída. {migrated_count} documentos migrados.")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erro na migração de mensagens: {e}")
            raise
            
    def migrate_solicitacoes(self):
        """Migra dados antigos de solicitações para o novo formato"""
        try:
            solicitacoes = self._get_collection_data('solicitacoes')
            migrated_count = 0
            
            for solicitacao in solicitacoes:
                # Verifica se precisa de migração
                if 'data_criacao' not in solicitacao:
                    solicitacao['data_criacao'] = firestore.SERVER_TIMESTAMP
                    solicitacao['ultima_atualizacao'] = firestore.SERVER_TIMESTAMP
                    
                    # Atualiza o documento
                    doc_ref = self.db.collection('solicitacoes').document(solicitacao['id'])
                    doc_ref.set(solicitacao)
                    migrated_count += 1
                    
            logger.info(f"Migração de solicitações concluída. {migrated_count} documentos migrados.")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erro na migração de solicitações: {e}")
            raise
            
    def migrate_avaliacoes(self):
        """Migra dados antigos de avaliações para o novo formato"""
        try:
            avaliacoes = self._get_collection_data('avaliacoes')
            migrated_count = 0
            
            for avaliacao in avaliacoes:
                # Verifica se precisa de migração
                if 'data_criacao' not in avaliacao:
                    avaliacao['data_criacao'] = firestore.SERVER_TIMESTAMP
                    
                    # Atualiza o documento
                    doc_ref = self.db.collection('avaliacoes').document(avaliacao['id'])
                    doc_ref.set(avaliacao)
                    migrated_count += 1
                    
            logger.info(f"Migração de avaliações concluída. {migrated_count} documentos migrados.")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erro na migração de avaliações: {e}")
            raise
            
    def migrate_consolidado(self):
        """Migra dados antigos de consolidado para o novo formato"""
        try:
            consolidados = self._get_collection_data('consolidada_atendimentos')
            migrated_count = 0
            
            for consolidado in consolidados:
                # Verifica se precisa de migração
                if 'data_criacao' not in consolidado:
                    consolidado['data_criacao'] = firestore.SERVER_TIMESTAMP
                    
                    # Atualiza o documento
                    doc_ref = self.db.collection('consolidada_atendimentos').document(consolidado['id'])
                    doc_ref.set(consolidado)
                    migrated_count += 1
                    
            logger.info(f"Migração de consolidado concluída. {migrated_count} documentos migrados.")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Erro na migração de consolidado: {e}")
            raise
            
    def run_all_migrations(self):
        """Executa todas as migrações em sequência"""
        try:
            # Faz backup antes de iniciar as migrações
            backup_file = self.backup_all_collections()
            
            # Executa as migrações
            results = {
                'conversas': self.migrate_conversations(),
                'mensagens': self.migrate_messages(),
                'solicitacoes': self.migrate_solicitacoes(),
                'avaliacoes': self.migrate_avaliacoes(),
                'consolidado': self.migrate_consolidado()
            }
            
            logger.info("Todas as migrações concluídas com sucesso")
            return {
                'backup_file': backup_file,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Erro durante as migrações: {e}")
            raise

# Instância global do gerenciador de migrações
migration_manager = MigrationManager() 