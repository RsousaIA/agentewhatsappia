import pytest
from datetime import datetime, timedelta
import pytz
from agent.core.priority_manager import PriorityManager

@pytest.fixture
def priority_manager():
    """Fixture que retorna uma instância do PriorityManager para testes."""
    return PriorityManager()

def test_priority_manager_initialization(priority_manager):
    """Testa a inicialização do PriorityManager."""
    assert priority_manager._prioridade_por_tempo['alta'] == 3600
    assert priority_manager._prioridade_por_tempo['media'] == 7200
    assert priority_manager._prioridade_por_tempo['baixa'] == 14400
    
    assert priority_manager._prioridade_por_urgencia['critica'] == 1.5
    assert priority_manager._prioridade_por_urgencia['alta'] == 1.2
    assert priority_manager._prioridade_por_urgencia['normal'] == 1.0
    
    assert priority_manager._prioridade_por_tipo['reclamacao'] == 1.3
    assert priority_manager._prioridade_por_tipo['solicitacao'] == 1.2
    assert priority_manager._prioridade_por_tipo['informacao'] == 1.0
    
    assert priority_manager._prioridade_por_reabertura[0] == 1.0
    assert priority_manager._prioridade_por_reabertura[1] == 1.2
    assert priority_manager._prioridade_por_reabertura[2] == 1.4
    assert priority_manager._prioridade_por_reabertura[3] == 1.6

def test_calcular_prioridade_conversa_tempo(priority_manager):
    """Testa o cálculo de prioridade baseado no tempo de espera."""
    # Conversa recente (menos de 1 hora)
    conversa_recente = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 0
    }
    prioridade_recente = priority_manager._calcular_prioridade_conversa(conversa_recente)
    assert prioridade_recente > 1.0  # Deve ter prioridade alta por ser recente
    
    # Conversa antiga (mais de 4 horas)
    conversa_antiga = {
        'start_time': datetime.now(pytz.UTC) - timedelta(hours=5),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 0
    }
    prioridade_antiga = priority_manager._calcular_prioridade_conversa(conversa_antiga)
    assert prioridade_antiga < prioridade_recente  # Deve ter prioridade menor

def test_calcular_prioridade_conversa_tipo(priority_manager):
    """Testa o cálculo de prioridade baseado no tipo de solicitação."""
    conversa_base = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'messages': [],
        'reopen_count': 0
    }
    
    # Teste com diferentes tipos de solicitação
    tipos = ['reclamacao', 'solicitacao', 'informacao']
    prioridades = []
    
    for tipo in tipos:
        conversa = conversa_base.copy()
        conversa['request_type'] = tipo
        prioridades.append(priority_manager._calcular_prioridade_conversa(conversa))
    
    # Verifica se as prioridades estão na ordem correta
    assert prioridades[0] > prioridades[1] > prioridades[2]

def test_calcular_prioridade_conversa_reclamacao(priority_manager):
    """Testa o cálculo de prioridade baseado em reclamações."""
    conversa_sem_reclamacao = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [
            {'role': 'client', 'content': 'Bom dia, preciso de informação'}
        ],
        'reopen_count': 0
    }
    
    conversa_com_reclamacao = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [
            {'role': 'client', 'content': 'Estou muito insatisfeito com o serviço'}
        ],
        'reopen_count': 0
    }
    
    prioridade_sem = priority_manager._calcular_prioridade_conversa(conversa_sem_reclamacao)
    prioridade_com = priority_manager._calcular_prioridade_conversa(conversa_com_reclamacao)
    
    assert prioridade_com > prioridade_sem

def test_calcular_prioridade_conversa_urgencia(priority_manager):
    """Testa o cálculo de prioridade baseado em urgência."""
    conversa_normal = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [
            {'role': 'client', 'content': 'Bom dia, preciso de informação'}
        ],
        'reopen_count': 0
    }
    
    conversa_urgente = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [
            {'role': 'client', 'content': 'URGENTE! Preciso de ajuda imediata'}
        ],
        'reopen_count': 0
    }
    
    prioridade_normal = priority_manager._calcular_prioridade_conversa(conversa_normal)
    prioridade_urgente = priority_manager._calcular_prioridade_conversa(conversa_urgente)
    
    assert prioridade_urgente > prioridade_normal

def test_calcular_prioridade_conversa_reabertura(priority_manager):
    """Testa o cálculo de prioridade baseado em reaberturas."""
    conversa_base = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': []
    }
    
    # Teste com diferentes contagens de reabertura
    prioridades = []
    for count in range(4):
        conversa = conversa_base.copy()
        conversa['reopen_count'] = count
        prioridades.append(priority_manager._calcular_prioridade_conversa(conversa))
    
    # Verifica se as prioridades aumentam com o número de reaberturas
    assert prioridades[0] < prioridades[1] < prioridades[2] < prioridades[3]

def test_sort_conversations_by_priority(priority_manager):
    """Testa a ordenação de conversas por prioridade."""
    conversas = [
        {
            'start_time': datetime.now(pytz.UTC) - timedelta(hours=5),
            'request_type': 'informacao',
            'messages': [],
            'reopen_count': 0
        },
        {
            'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
            'request_type': 'reclamacao',
            'messages': [
                {'role': 'client', 'content': 'Estou muito insatisfeito'}
            ],
            'reopen_count': 2
        },
        {
            'start_time': datetime.now(pytz.UTC) - timedelta(minutes=15),
            'request_type': 'solicitacao',
            'messages': [
                {'role': 'client', 'content': 'URGENTE! Preciso de ajuda'}
            ],
            'reopen_count': 1
        }
    ]
    
    conversas_ordenadas = priority_manager.sort_conversations_by_priority(conversas)
    
    # Verifica se a ordem está correta (maior prioridade primeiro)
    assert conversas_ordenadas[0]['request_type'] == 'reclamacao'  # Reclamação + reabertura
    assert conversas_ordenadas[1]['request_type'] == 'solicitacao'  # Urgente
    assert conversas_ordenadas[2]['request_type'] == 'informacao'  # Mais antiga

def test_calcular_prioridade_conversa_erro(priority_manager):
    """Testa o tratamento de erros no cálculo de prioridade."""
    # Conversa com dados inválidos
    conversa_invalida = {
        'start_time': 'data_invalida',
        'request_type': 'tipo_invalido',
        'messages': 'não é uma lista',
        'reopen_count': 'não é um número'
    }
    
    prioridade = priority_manager._calcular_prioridade_conversa(conversa_invalida)
    assert prioridade == 1.0  # Deve retornar prioridade padrão em caso de erro 

def test_calcular_prioridade_conversa_combinada(priority_manager):
    """Testa o cálculo de prioridade com múltiplos fatores combinados."""
    conversa = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=45),  # Tempo médio
        'request_type': 'reclamacao',  # Prioridade alta
        'messages': [
            {'role': 'client', 'content': 'URGENTE! Estou muito insatisfeito com o serviço'},  # Urgência + reclamação
            {'role': 'system', 'content': 'Entendo sua frustração'}
        ],
        'reopen_count': 2  # Reabertura múltipla
    }
    
    prioridade = priority_manager._calcular_prioridade_conversa(conversa)
    
    # Deve ter prioridade muito alta devido à combinação de fatores
    assert prioridade > 2.0

def test_calcular_prioridade_conversa_mensagens_vazias(priority_manager):
    """Testa o cálculo de prioridade com mensagens vazias."""
    conversa = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [],  # Sem mensagens
        'reopen_count': 0
    }
    
    prioridade = priority_manager._calcular_prioridade_conversa(conversa)
    assert prioridade > 0  # Deve ter alguma prioridade mesmo sem mensagens

def test_calcular_prioridade_conversa_tipo_invalido(priority_manager):
    """Testa o cálculo de prioridade com tipo de solicitação inválido."""
    conversa = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'tipo_invalido',  # Tipo não existente
        'messages': [],
        'reopen_count': 0
    }
    
    prioridade = priority_manager._calcular_prioridade_conversa(conversa)
    assert prioridade > 0  # Deve usar prioridade padrão

def test_sort_conversations_by_priority_lista_vazia(priority_manager):
    """Testa a ordenação de uma lista vazia de conversas."""
    conversas = []
    conversas_ordenadas = priority_manager.sort_conversations_by_priority(conversas)
    assert len(conversas_ordenadas) == 0

def test_sort_conversations_by_priority_erro(priority_manager):
    """Testa a ordenação com dados inválidos."""
    conversas = [
        {
            'start_time': 'data_invalida',
            'request_type': 'tipo_invalido',
            'messages': 'não é uma lista',
            'reopen_count': 'não é um número'
        }
    ]
    
    conversas_ordenadas = priority_manager.sort_conversations_by_priority(conversas)
    assert len(conversas_ordenadas) == 1  # Deve retornar a lista original em caso de erro

def test_calcular_prioridade_conversa_tempo_limite(priority_manager):
    """Testa o cálculo de prioridade nos limites de tempo."""
    # No limite de alta prioridade (1 hora)
    conversa_limite_alta = {
        'start_time': datetime.now(pytz.UTC) - timedelta(seconds=3600),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 0
    }
    
    # No limite de média prioridade (2 horas)
    conversa_limite_media = {
        'start_time': datetime.now(pytz.UTC) - timedelta(seconds=7200),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 0
    }
    
    # No limite de baixa prioridade (4 horas)
    conversa_limite_baixa = {
        'start_time': datetime.now(pytz.UTC) - timedelta(seconds=14400),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 0
    }
    
    prioridade_alta = priority_manager._calcular_prioridade_conversa(conversa_limite_alta)
    prioridade_media = priority_manager._calcular_prioridade_conversa(conversa_limite_media)
    prioridade_baixa = priority_manager._calcular_prioridade_conversa(conversa_limite_baixa)
    
    assert prioridade_alta > prioridade_media > prioridade_baixa

def test_calcular_prioridade_conversa_reabertura_maxima(priority_manager):
    """Testa o cálculo de prioridade com número máximo de reaberturas."""
    conversa = {
        'start_time': datetime.now(pytz.UTC) - timedelta(minutes=30),
        'request_type': 'informacao',
        'messages': [],
        'reopen_count': 5  # Mais que o máximo definido (3)
    }
    
    prioridade = priority_manager._calcular_prioridade_conversa(conversa)
    assert prioridade > 1.0  # Deve usar o valor máximo de reabertura 