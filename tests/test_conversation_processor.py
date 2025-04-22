import pytest
from unittest.mock import Mock, patch
from agent.core.conversation_processor import ConversationProcessor

@pytest.fixture
def conversation_processor():
    """Fixture que retorna uma instância do ConversationProcessor para testes."""
    return ConversationProcessor()

def test_analyze_communication(conversation_processor):
    """Testa a análise de comunicação."""
    messages = [
        {'role': 'system', 'content': 'Bom dia! Como posso ajudar?'},
        {'role': 'user', 'content': 'Preciso de ajuda com o sistema'},
        {'role': 'system', 'content': 'Claro, conte-me mais sobre o problema'}
    ]
    
    score = conversation_processor.analyze_communication(messages)
    assert 0 <= score <= 1

def test_analyze_technical_knowledge(conversation_processor):
    """Testa a análise de conhecimento técnico."""
    messages = [
        {'role': 'user', 'content': 'O sistema está lento'},
        {'role': 'system', 'content': 'Você pode tentar limpar o cache do navegador'},
        {'role': 'user', 'content': 'Como faço isso?'},
        {'role': 'system', 'content': 'Pressione Ctrl+Shift+Delete e selecione "Cache"'}
    ]
    
    score = conversation_processor.analyze_technical_knowledge(messages)
    assert 0 <= score <= 1

def test_analyze_empathy(conversation_processor):
    """Testa a análise de empatia."""
    messages = [
        {'role': 'user', 'content': 'Estou muito frustrado com o serviço'},
        {'role': 'system', 'content': 'Entendo sua frustração. Vou ajudar a resolver isso'},
        {'role': 'user', 'content': 'Obrigado pela compreensão'}
    ]
    
    score = conversation_processor.analyze_empathy(messages)
    assert 0 <= score <= 1

def test_analyze_professionalism(conversation_processor):
    """Testa a análise de profissionalismo."""
    messages = [
        {'role': 'system', 'content': 'Bom dia, sou o atendente João'},
        {'role': 'user', 'content': 'Olá'},
        {'role': 'system', 'content': 'Como posso ser útil hoje?'}
    ]
    
    score = conversation_processor.analyze_professionalism(messages)
    assert 0 <= score <= 1

def test_analyze_results(conversation_processor):
    """Testa a análise de resultados."""
    messages = [
        {'role': 'user', 'content': 'O problema foi resolvido?'},
        {'role': 'system', 'content': 'Sim, o sistema está funcionando normalmente agora'},
        {'role': 'user', 'content': 'Perfeito, obrigado!'}
    ]
    
    score = conversation_processor.analyze_results(messages)
    assert 0 <= score <= 1

def test_analyze_emotional_intelligence(conversation_processor):
    """Testa a análise de inteligência emocional."""
    messages = [
        {'role': 'user', 'content': 'Estou muito irritado com isso'},
        {'role': 'system', 'content': 'Percebo que você está frustrado. Vamos resolver isso juntos'},
        {'role': 'user', 'content': 'Obrigado por entender'}
    ]
    
    score = conversation_processor.analyze_emotional_intelligence(messages)
    assert 0 <= score <= 1

def test_detect_complaint(conversation_processor):
    """Testa a detecção de reclamações."""
    # Mensagem com reclamação
    message = 'Estou muito insatisfeito com o serviço prestado'
    assert conversation_processor.detect_complaint(message) is True
    
    # Mensagem sem reclamação
    message = 'Bom dia, preciso de ajuda'
    assert conversation_processor.detect_complaint(message) is False

def test_extract_requests(conversation_processor):
    """Testa a extração de solicitações."""
    messages = [
        {'role': 'user', 'content': 'Preciso de ajuda para configurar o email'},
        {'role': 'system', 'content': 'Claro, posso ajudar com isso'},
        {'role': 'user', 'content': 'Também quero saber como mudar a senha'}
    ]
    
    requests = conversation_processor.extract_requests(messages)
    assert len(requests) == 2
    assert 'configurar o email' in requests
    assert 'mudar a senha' in requests

def test_check_request_addressed(conversation_processor):
    """Testa a verificação de solicitações atendidas."""
    request = 'configurar o email'
    messages = [
        {'role': 'user', 'content': 'Preciso de ajuda para configurar o email'},
        {'role': 'system', 'content': 'Vou te ajudar a configurar o email. Primeiro, abra as configurações...'}
    ]
    
    assert conversation_processor.check_request_addressed(request, messages) is True

def test_analyze_communication_empty(conversation_processor):
    """Testa a análise de comunicação com mensagens vazias."""
    messages = []
    score = conversation_processor.analyze_communication(messages)
    assert score == 0

def test_analyze_technical_knowledge_complex(conversation_processor):
    """Testa a análise de conhecimento técnico com problemas complexos."""
    messages = [
        {'role': 'user', 'content': 'O servidor está retornando erro 500'},
        {'role': 'system', 'content': 'Vamos verificar os logs do servidor. Execute o comando: journalctl -u apache2'},
        {'role': 'user', 'content': 'Encontrei o erro: PHP Fatal error'},
        {'role': 'system', 'content': 'Isso indica um problema de memória. Vamos ajustar o memory_limit no php.ini'}
    ]
    
    score = conversation_processor.analyze_technical_knowledge(messages)
    assert score > 0.5  # Deve ter uma pontuação alta por lidar com problema complexo

def test_analyze_empathy_negative(conversation_processor):
    """Testa a análise de empatia com respostas negativas."""
    messages = [
        {'role': 'user', 'content': 'Estou muito chateado com o serviço'},
        {'role': 'system', 'content': 'Isso não é problema nosso'},
        {'role': 'user', 'content': 'Que péssimo atendimento'}
    ]
    
    score = conversation_processor.analyze_empathy(messages)
    assert score < 0.5  # Deve ter uma pontuação baixa por falta de empatia

def test_analyze_professionalism_informal(conversation_processor):
    """Testa a análise de profissionalismo com linguagem informal."""
    messages = [
        {'role': 'system', 'content': 'E aí, beleza?'},
        {'role': 'user', 'content': 'Oi'},
        {'role': 'system', 'content': 'Tá precisando de ajuda com o que?'}
    ]
    
    score = conversation_processor.analyze_professionalism(messages)
    assert score < 0.5  # Deve ter uma pontuação baixa por linguagem informal

def test_analyze_results_unsolved(conversation_processor):
    """Testa a análise de resultados com problema não resolvido."""
    messages = [
        {'role': 'user', 'content': 'O problema ainda não foi resolvido'},
        {'role': 'system', 'content': 'Vou encaminhar para o time técnico'},
        {'role': 'user', 'content': 'Ok, aguardo retorno'}
    ]
    
    score = conversation_processor.analyze_results(messages)
    assert score < 0.5  # Deve ter uma pontuação baixa por problema não resolvido

def test_analyze_emotional_intelligence_escalation(conversation_processor):
    """Testa a análise de inteligência emocional com escalação."""
    messages = [
        {'role': 'user', 'content': 'Estou extremamente irritado!'},
        {'role': 'system', 'content': 'Entendo sua frustração. Vou escalar para um supervisor'},
        {'role': 'user', 'content': 'Obrigado, preciso falar com alguém mais experiente'}
    ]
    
    score = conversation_processor.analyze_emotional_intelligence(messages)
    assert score > 0.5  # Deve ter uma pontuação alta por lidar bem com a situação 