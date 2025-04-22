import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do Firebase para testes
FIREBASE_TEST_CONFIG = {
    'apiKey': 'test-api-key',
    'authDomain': 'test-project.firebaseapp.com',
    'projectId': 'test-project',
    'storageBucket': 'test-project.appspot.com',
    'messagingSenderId': '123456789',
    'appId': '1:123456789:web:abcdef123456789',
    'measurementId': 'G-ABCDEF123'
}

# Prefixo para documentos de teste
TEST_PREFIX = 'test_'

# Configurações de cache para testes
CACHE_TEST_CONFIG = {
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Configurações de coleções para testes
COLLECTIONS = {
    'conversations': 'conversas',
    'messages': 'mensagens',
    'requests': 'solicitacoes',
    'evaluations': 'avaliacoes',
    'reports': 'relatorios'
}

# Status das conversas
CONVERSATION_STATUS = {
    'ACTIVE': 'ACTIVE',
    'CLOSED': 'CLOSED',
    'PENDING': 'PENDING',
    'ARCHIVED': 'ARCHIVED'
}

# Tipos de mensagem
MESSAGE_TYPES = {
    'USER': 'USER',
    'SYSTEM': 'SYSTEM',
    'AGENT': 'AGENT',
    'NOTIFICATION': 'NOTIFICATION'
}

# Tipos de solicitação
REQUEST_TYPES = {
    'SUPPORT': 'SUPPORT',
    'COMPLAINT': 'COMPLAINT',
    'INFORMATION': 'INFORMATION',
    'TECHNICAL': 'TECHNICAL'
}

# Configurações de timeout
TIMEOUTS = {
    'CONVERSATION_INACTIVE': 1800,  # 30 minutos
    'CLEANUP_INTERVAL': 300,        # 5 minutos
    'EVALUATION_INTERVAL': 600,     # 10 minutos
    'REQUEST_TIMEOUT': 3600         # 1 hora
}

# Configurações de avaliação
EVALUATION_CONFIG = {
    'weights': {
        'communication': 0.2,
        'technical': 0.2,
        'empathy': 0.15,
        'professionalism': 0.15,
        'results': 0.2,
        'emotional_intelligence': 0.1
    },
    'thresholds': {
        'min_score': 0.0,
        'max_score': 1.0,
        'warning_score': 0.6,
        'critical_score': 0.4
    }
}

# Configurações de prioridade
PRIORITY_CONFIG = {
    'weights': {
        'wait_time': 0.3,
        'urgency': 0.3,
        'type': 0.2,
        'reopens': 0.2
    },
    'thresholds': {
        'urgent_wait_time': 1800,   # 30 minutos
        'critical_wait_time': 3600  # 1 hora
    }
} 