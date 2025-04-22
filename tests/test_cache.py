import unittest
from datetime import datetime, timedelta
from database.cache import CacheManager, cached, invalidate_cache
import time

class TestCache(unittest.TestCase):
    def setUp(self):
        self.cache_manager = CacheManager()
        self.cache_manager.clear()

    def test_cache_set_get(self):
        """Testa a funcionalidade básica de set e get do cache"""
        self.cache_manager.set('test_key', 'test_value')
        self.assertEqual(self.cache_manager.get('test_key'), 'test_value')

    def test_cache_ttl(self):
        """Testa se o cache expira corretamente após o TTL"""
        self.cache_manager.set('test_key', 'test_value', ttl=1)
        time.sleep(2)
        self.assertIsNone(self.cache_manager.get('test_key'))

    def test_cache_delete(self):
        """Testa a remoção de itens do cache"""
        self.cache_manager.set('test_key', 'test_value')
        self.cache_manager.delete('test_key')
        self.assertIsNone(self.cache_manager.get('test_key'))

    def test_cache_clear(self):
        """Testa a limpeza completa do cache"""
        self.cache_manager.set('key1', 'value1')
        self.cache_manager.set('key2', 'value2')
        self.cache_manager.clear()
        self.assertIsNone(self.cache_manager.get('key1'))
        self.assertIsNone(self.cache_manager.get('key2'))

    def test_cache_decorator(self):
        """Testa o decorador @cached"""
        @cached(ttl=1)
        def test_function():
            return datetime.now()

        first_call = test_function()
        time.sleep(0.5)
        second_call = test_function()
        self.assertEqual(first_call, second_call)

        time.sleep(1)
        third_call = test_function()
        self.assertNotEqual(first_call, third_call)

    def test_invalidate_cache_decorator(self):
        """Testa o decorador @invalidate_cache"""
        @cached(ttl=60)
        def get_data():
            return datetime.now()

        @invalidate_cache('data:*')
        def update_data():
            return datetime.now()

        first_call = get_data()
        update_data()
        second_call = get_data()
        self.assertNotEqual(first_call, second_call)

    def test_cache_eviction(self):
        """Testa a remoção automática de itens antigos quando o cache está cheio"""
        for i in range(1100):  # Mais que o limite de 1000
            self.cache_manager.set(f'key{i}', f'value{i}')

        # Verifica se os itens mais antigos foram removidos
        self.assertIsNone(self.cache_manager.get('key0'))
        self.assertIsNotNone(self.cache_manager.get('key1099'))

    def test_cache_pattern_invalidation(self):
        """Testa a invalidação de cache por padrão"""
        self.cache_manager.set('test:1', 'value1')
        self.cache_manager.set('test:2', 'value2')
        self.cache_manager.set('other:1', 'value3')

        self.cache_manager.invalidate_pattern('test:*')
        self.assertIsNone(self.cache_manager.get('test:1'))
        self.assertIsNone(self.cache_manager.get('test:2'))
        self.assertIsNotNone(self.cache_manager.get('other:1'))

    def test_cache_metrics(self):
        """Testa as métricas do cache"""
        # Testa hits
        self.cache_manager.set('key1', 'value1')
        self.cache_manager.get('key1')
        self.assertEqual(self.cache_manager.get_metrics()['hits'], 1)

        # Testa misses
        self.cache_manager.get('non_existent_key')
        self.assertEqual(self.cache_manager.get_metrics()['misses'], 1)

        # Testa evictions
        for i in range(1100):
            self.cache_manager.set(f'key{i}', f'value{i}')
        self.assertGreater(self.cache_manager.get_metrics()['evictions'], 0)

        # Testa invalidations
        self.cache_manager.invalidate_pattern('test:*')
        self.assertEqual(self.cache_manager.get_metrics()['invalidations'], 1)

if __name__ == '__main__':
    unittest.main() 