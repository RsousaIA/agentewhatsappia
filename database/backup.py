import os
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import firebase_admin
from firebase_admin import firestore, storage
from .firebase_db import get_firestore_db

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, backup_dir: str = 'backups'):
        """
        Inicializa o gerenciador de backup
        
        Args:
            backup_dir: Diretório para armazenar backups locais
        """
        self.backup_dir = backup_dir
        self.db = get_firestore_db()
        self.bucket = storage.bucket()
        
        # Criar diretório de backup se não existir
        os.makedirs(backup_dir, exist_ok=True)
        
    def create_backup(self, collections: List[str] = None) -> Dict:
        """
        Cria um backup completo do Firebase
        
        Args:
            collections: Lista de coleções para backup (None para todas)
            
        Returns:
            Dict com informações do backup
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_id = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_id)
            
            # Criar diretório do backup
            os.makedirs(backup_path, exist_ok=True)
            
            # Lista de coleções para backup
            if collections is None:
                collections = ['conversas', 'mensagens', 'solicitacoes', 
                             'avaliacoes', 'relatorios', 'consolidada_atendimentos']
            
            backup_data = {
                'id': backup_id,
                'timestamp': timestamp,
                'collections': collections,
                'status': 'em_progresso'
            }
            
            # Salvar metadados do backup
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Fazer backup de cada coleção
            for collection in collections:
                self._backup_collection(collection, backup_path)
            
            # Fazer backup de arquivos do Storage
            self._backup_storage(backup_path)
            
            # Atualizar status do backup
            backup_data['status'] = 'concluido'
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Upload do backup para o Firebase Storage
            self._upload_backup(backup_path)
            
            logger.info(f"Backup {backup_id} criado com sucesso")
            return backup_data
            
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            raise
    
    def _backup_collection(self, collection_name: str, backup_path: str):
        """
        Faz backup de uma coleção específica
        
        Args:
            collection_name: Nome da coleção
            backup_path: Caminho do backup
        """
        try:
            collection_path = os.path.join(backup_path, f"{collection_name}.json")
            docs = []
            
            # Obter todos os documentos da coleção
            for doc in self.db.collection(collection_name).stream():
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                docs.append(doc_data)
            
            # Salvar documentos em arquivo JSON
            with open(collection_path, 'w') as f:
                json.dump(docs, f, indent=2)
                
            logger.info(f"Coleção {collection_name} backup concluído")
            
        except Exception as e:
            logger.error(f"Erro ao fazer backup da coleção {collection_name}: {e}")
            raise
    
    def _backup_storage(self, backup_path: str):
        """
        Faz backup dos arquivos do Storage
        
        Args:
            backup_path: Caminho do backup
        """
        try:
            storage_path = os.path.join(backup_path, 'storage')
            os.makedirs(storage_path, exist_ok=True)
            
            # Listar todos os arquivos do bucket
            blobs = self.bucket.list_blobs()
            
            for blob in blobs:
                # Ignorar backups anteriores
                if blob.name.startswith('backups/'):
                    continue
                    
                # Criar diretório se necessário
                file_path = os.path.join(storage_path, blob.name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Download do arquivo
                blob.download_to_filename(file_path)
                
            logger.info("Backup do Storage concluído")
            
        except Exception as e:
            logger.error(f"Erro ao fazer backup do Storage: {e}")
            raise
    
    def _upload_backup(self, backup_path: str):
        """
        Upload do backup para o Firebase Storage
        
        Args:
            backup_path: Caminho do backup local
        """
        try:
            backup_id = os.path.basename(backup_path)
            storage_path = f"backups/{backup_id}"
            
            # Upload de cada arquivo
            for root, _, files in os.walk(backup_path):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, backup_path)
                    blob_path = f"{storage_path}/{relative_path}"
                    
                    blob = self.bucket.blob(blob_path)
                    blob.upload_from_filename(local_path)
            
            logger.info(f"Backup {backup_id} enviado para o Storage")
            
        except Exception as e:
            logger.error(f"Erro ao fazer upload do backup: {e}")
            raise
    
    def restore_backup(self, backup_id: str):
        """
        Restaura um backup específico
        
        Args:
            backup_id: ID do backup a ser restaurado
        """
        try:
            # Download do backup do Storage
            backup_path = os.path.join(self.backup_dir, backup_id)
            self._download_backup(backup_id, backup_path)
            
            # Verificar metadados
            metadata_path = os.path.join(backup_path, 'metadata.json')
            if not os.path.exists(metadata_path):
                raise ValueError(f"Metadados do backup {backup_id} não encontrados")
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Restaurar cada coleção
            for collection in metadata['collections']:
                self._restore_collection(collection, backup_path)
            
            # Restaurar arquivos do Storage
            self._restore_storage(backup_path)
            
            logger.info(f"Backup {backup_id} restaurado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            raise
    
    def _download_backup(self, backup_id: str, backup_path: str):
        """
        Download do backup do Firebase Storage
        
        Args:
            backup_id: ID do backup
            backup_path: Caminho local para download
        """
        try:
            storage_path = f"backups/{backup_id}"
            
            # Listar arquivos do backup
            blobs = self.bucket.list_blobs(prefix=storage_path)
            
            for blob in blobs:
                # Criar diretório se necessário
                relative_path = os.path.relpath(blob.name, storage_path)
                file_path = os.path.join(backup_path, relative_path)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Download do arquivo
                blob.download_to_filename(file_path)
            
            logger.info(f"Backup {backup_id} baixado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao baixar backup: {e}")
            raise
    
    def _restore_collection(self, collection_name: str, backup_path: str):
        """
        Restaura uma coleção específica
        
        Args:
            collection_name: Nome da coleção
            backup_path: Caminho do backup
        """
        try:
            collection_path = os.path.join(backup_path, f"{collection_name}.json")
            
            if not os.path.exists(collection_path):
                logger.warning(f"Arquivo de backup para coleção {collection_name} não encontrado")
                return
            
            # Ler documentos do backup
            with open(collection_path, 'r') as f:
                docs = json.load(f)
            
            # Restaurar documentos
            batch = self.db.batch()
            batch_size = 0
            max_batch_size = 500
            
            for doc in docs:
                doc_id = doc.pop('id')
                doc_ref = self.db.collection(collection_name).document(doc_id)
                batch.set(doc_ref, doc)
                batch_size += 1
                
                if batch_size >= max_batch_size:
                    batch.commit()
                    batch = self.db.batch()
                    batch_size = 0
            
            if batch_size > 0:
                batch.commit()
            
            logger.info(f"Coleção {collection_name} restaurada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar coleção {collection_name}: {e}")
            raise
    
    def _restore_storage(self, backup_path: str):
        """
        Restaura arquivos do Storage
        
        Args:
            backup_path: Caminho do backup
        """
        try:
            storage_path = os.path.join(backup_path, 'storage')
            
            if not os.path.exists(storage_path):
                logger.warning("Diretório de backup do Storage não encontrado")
                return
            
            # Upload de cada arquivo
            for root, _, files in os.walk(storage_path):
                for file in files:
                    local_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_path, storage_path)
                    
                    blob = self.bucket.blob(relative_path)
                    blob.upload_from_filename(local_path)
            
            logger.info("Storage restaurado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao restaurar Storage: {e}")
            raise
    
    def list_backups(self) -> List[Dict]:
        """
        Lista todos os backups disponíveis
        
        Returns:
            Lista de backups
        """
        try:
            backups = []
            
            # Listar backups do Storage
            blobs = self.bucket.list_blobs(prefix='backups/')
            backup_dirs = set()
            
            for blob in blobs:
                backup_id = blob.name.split('/')[1]
                backup_dirs.add(backup_id)
            
            # Obter metadados de cada backup
            for backup_id in backup_dirs:
                metadata_blob = self.bucket.blob(f"backups/{backup_id}/metadata.json")
                
                if metadata_blob.exists():
                    metadata = json.loads(metadata_blob.download_as_text())
                    backups.append(metadata)
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar backups: {e}")
            return []
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Deleta um backup específico
        
        Args:
            backup_id: ID do backup a ser deletado
            
        Returns:
            bool: True se deletado com sucesso
        """
        try:
            # Deletar do Storage
            blobs = self.bucket.list_blobs(prefix=f"backups/{backup_id}")
            
            for blob in blobs:
                blob.delete()
            
            # Deletar localmente
            backup_path = os.path.join(self.backup_dir, backup_id)
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            
            logger.info(f"Backup {backup_id} deletado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar backup: {e}")
            return False 