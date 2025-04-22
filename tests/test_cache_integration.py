import unittest
from datetime import datetime, timedelta
from database.firebase_db import (
    init_firebase,
    get_firestore_db,
    save_message,
    get_message,
    update_message,
    delete_message
)
from database.cache import cache_manager
from tests.test_config import FIREBASE_TEST_CONFIG, CACHE_TEST_CONFIG
import time

class TestCacheIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuração inicial para todos os testes"""
        init_firebase()
        cls.db = get_firestore_db()
        
    def setUp(self):
        """Configuração antes de cada teste"""
        # Limpa o cache
        cache_manager.clear()
        
    def test_cache_hit_miss(self):
        """Testa acertos e falhas do cache"""
        # Cria uma conversa
        conversation_data = {
            'cliente_id': 'test_cliente',
            'status': 'aberta'
        }
        conversation_id = create_conversation(conversation_data)
        
        # Primeira leitura (miss)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['misses'], 1)
        
        # Segunda leitura (hit)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['hits'], 1)
        
    def test_cache_invalidation(self):
        """Testa a invalidação do cache após atualização"""
        # Cria uma conversa
        conversation_data = {
            'cliente_id': 'test_cliente',
            'status': 'aberta'
        }
        conversation_id = create_conversation(conversation_data)
        
        # Lê a conversa (miss)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['misses'], 1)
        
        # Lê novamente (hit)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['hits'], 1)
        
        # Atualiza a conversa
        update_data = {
            'status': 'fechada'
        }
        update_conversation(conversation_id, update_data)
        
        # Lê após atualização (miss devido à invalidação)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['misses'], 2)
        
    def test_cache_ttl(self):
        """Testa a expiração do cache após TTL"""
        # Cria uma conversa
        conversation_data = {
            'cliente_id': 'test_cliente',
            'status': 'aberta'
        }
        conversation_id = create_conversation(conversation_data)
        
        # Lê a conversa (miss)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['misses'], 1)
        
        # Lê novamente (hit)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['hits'], 1)
        
        # Aguarda o TTL expirar
        time.sleep(CACHE_TEST_CONFIG['ttl'] + 1)
        
        # Lê após TTL expirado (miss)
        conversation = get_conversation(conversation_id)
        metrics = get_cache_metrics()
        self.assertEqual(metrics['misses'], 2)
        
    def test_cache_eviction(self):
        """Testa a remoção de itens antigos quando o cache está cheio"""
        # Cria várias conversas para encher o cache
        for i in range(CACHE_TEST_CONFIG['maxsize'] + 10):
            conversation_data = {
                'cliente_id': f'test_cliente_{i}',
                'status': 'aberta'
            }
            conversation_id = create_conversation(conversation_data)
            get_conversation(conversation_id)  # Força o cache
            
        metrics = get_cache_metrics()
        self.assertGreater(metrics['evictions'], 0)

if __name__ == '__main__':
    unittest.main() 