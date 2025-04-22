from functools import lru_cache, wraps
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import logging
from firebase_admin import firestore
from collections import defaultdict

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        """
        Inicializa o gerenciador de cache
        
        Args:
            maxsize: Tamanho máximo do cache
            ttl: Time To Live em segundos
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._metrics = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0
        }
        self._pattern_cache = defaultdict(set)
        
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém um valor do cache
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor armazenado ou None se expirado/não encontrado
        """
        if key not in self._cache:
            self._metrics['misses'] += 1
            return None
            
        if self._is_expired(key):
            self.delete(key)
            self._metrics['misses'] += 1
            return None
            
        self._metrics['hits'] += 1
        return self._cache[key]
        
    def set(self, key: str, value: Any):
        """
        Armazena um valor no cache
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
        """
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
        
        # Limitar tamanho do cache
        if len(self._cache) > self.maxsize:
            self._evict_oldest()
            
    def delete(self, key: str):
        """
        Remove um valor do cache
        
        Args:
            key: Chave do cache
        """
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
            
    def clear(self):
        """Limpa todo o cache"""
        self._cache.clear()
        self._timestamps.clear()
        self._pattern_cache.clear()
        
    def _is_expired(self, key: str) -> bool:
        """
        Verifica se um item do cache expirou
        
        Args:
            key: Chave do cache
            
        Returns:
            bool: True se expirado
        """
        if key not in self._timestamps:
            return True
            
        age = (datetime.now() - self._timestamps[key]).total_seconds()
        return age > self.ttl
        
    def _evict_oldest(self):
        """Remove o item mais antigo do cache"""
        if not self._timestamps:
            return
            
        oldest_key = min(self._timestamps.items(), key=lambda x: x[1])[0]
        self.delete(oldest_key)
        self._metrics['evictions'] += 1
        
    def invalidate_pattern(self, pattern: str):
        """
        Invalida todas as chaves que correspondem ao padrão
        
        Args:
            pattern: Padrão de chaves a serem invalidadas
        """
        if pattern in self._pattern_cache:
            for key in self._pattern_cache[pattern]:
                self.delete(key)
            del self._pattern_cache[pattern]
        self._metrics['invalidations'] += 1
        
    def get_metrics(self) -> Dict[str, int]:
        """
        Retorna as métricas do cache
        
        Returns:
            Dict com métricas do cache
        """
        return self._metrics.copy()
        
    def register_pattern(self, pattern: str, key: str):
        """
        Registra uma chave em um padrão para invalidação
        
        Args:
            pattern: Padrão de invalidação
            key: Chave do cache
        """
        self._pattern_cache[pattern].add(key)

# Instância global do cache
cache_manager = CacheManager()

def cached(ttl: int = 300, pattern: Optional[str] = None):
    """
    Decorador para cache de funções
    
    Args:
        ttl: Time To Live em segundos
        pattern: Padrão para invalidação do cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave única para o cache
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Registrar padrão se fornecido
            if pattern:
                cache_manager.register_pattern(pattern, key)
            
            # Tentar obter do cache
            cached_value = cache_manager.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value
                
            # Executar função e armazenar resultado
            logger.debug(f"Cache miss: {key}")
            result = func(*args, **kwargs)
            cache_manager.set(key, result)
            return result
            
        return wrapper
    return decorator

def invalidate_cache(*patterns: str):
    """
    Decorador para invalidar cache após operações de escrita
    
    Args:
        patterns: Padrões de chaves do cache a serem invalidadas
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidar caches especificados
            for pattern in patterns:
                cache_manager.invalidate_pattern(pattern)
                
            return result
            
        return wrapper
    return decorator

# Exemplos de uso:
"""
@cached(ttl=300, pattern='conversation:*')
def get_conversation(conversation_id: str) -> Optional[Dict]:
    # Implementação existente
    pass

@invalidate_cache('conversation:*')
def update_conversation(conversation_id: str, data: Dict) -> bool:
    # Implementação existente
    pass
""" 