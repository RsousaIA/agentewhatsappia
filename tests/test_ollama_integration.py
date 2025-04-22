import pytest
from unittest.mock import Mock, patch, MagicMock
from agent.core.ollama_integration import OllamaIntegration
from agent.prompts_library import get_default_conversation_closure_prompt

@pytest.fixture
def ollama_integration():
    """Fixture que retorna uma instância do OllamaIntegration para testes."""
    with patch('requests.post'), \
         patch('requests.get'):
        integration = OllamaIntegration()
        return integration

def test_ollama_integration_initialization(ollama_integration):
    """Testa a inicialização do OllamaIntegration."""
    assert ollama_integration.base_url == 'http://localhost:11434'
    assert ollama_integration.model == 'llama2'
    assert ollama_integration.temperature == 0.7
    assert ollama_integration.max_tokens == 1000

def test_generate_response(ollama_integration):
    """Testa a geração de resposta."""
    prompt = "Qual é a capital do Brasil?"
    expected_response = "A capital do Brasil é Brasília."
    
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            'response': expected_response
        }
        
        response = ollama_integration.generate_response(prompt)
        assert response == expected_response
        
        # Verifica se a requisição foi feita corretamente
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args['json']['prompt'] == prompt
        assert call_args['json']['model'] == ollama_integration.model
        assert call_args['json']['temperature'] == ollama_integration.temperature
        assert call_args['json']['max_tokens'] == ollama_integration.max_tokens

def test_generate_response_error(ollama_integration):
    """Testa o tratamento de erro na geração de resposta."""
    prompt = "Qual é a capital do Brasil?"
    
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Erro de conexão")
        
        response = ollama_integration.generate_response(prompt)
        assert response is None

def test_check_model_availability(ollama_integration):
    """Testa a verificação de disponibilidade do modelo."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'llama2'}]
        }
        
        assert ollama_integration.check_model_availability() is True
        
        # Verifica se a requisição foi feita corretamente
        mock_get.assert_called_once_with(f"{ollama_integration.base_url}/api/tags")

def test_check_model_availability_error(ollama_integration):
    """Testa o tratamento de erro na verificação de disponibilidade."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Erro de conexão")
        
        assert ollama_integration.check_model_availability() is False

def test_generate_response_with_context(ollama_integration):
    """Testa a geração de resposta com contexto."""
    prompt = "Qual é a capital do Brasil?"
    context = "O Brasil é um país da América do Sul."
    expected_response = "A capital do Brasil é Brasília."
    
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            'response': expected_response
        }
        
        response = ollama_integration.generate_response(prompt, context)
        assert response == expected_response
        
        # Verifica se o contexto foi incluído no prompt
        call_args = mock_post.call_args[1]
        assert context in call_args['json']['prompt']

def test_generate_response_with_temperature(ollama_integration):
    """Testa a geração de resposta com temperatura personalizada."""
    prompt = "Qual é a capital do Brasil?"
    temperature = 0.5
    
    with patch('requests.post') as mock_post:
        ollama_integration.generate_response(prompt, temperature=temperature)
        
        # Verifica se a temperatura foi alterada
        call_args = mock_post.call_args[1]
        assert call_args['json']['temperature'] == temperature

def test_generate_response_with_max_tokens(ollama_integration):
    """Testa a geração de resposta com número máximo de tokens personalizado."""
    prompt = "Qual é a capital do Brasil?"
    max_tokens = 500
    
    with patch('requests.post') as mock_post:
        ollama_integration.generate_response(prompt, max_tokens=max_tokens)
        
        # Verifica se o número máximo de tokens foi alterado
        call_args = mock_post.call_args[1]
        assert call_args['json']['max_tokens'] == max_tokens

def test_generate_response_with_different_model(ollama_integration):
    """Testa a geração de resposta com modelo diferente."""
    prompt = "Qual é a capital do Brasil?"
    model = "mistral"
    
    with patch('requests.post') as mock_post:
        ollama_integration.generate_response(prompt, model=model)
        
        # Verifica se o modelo foi alterado
        call_args = mock_post.call_args[1]
        assert call_args['json']['model'] == model

def test_generate_response_with_empty_prompt(ollama_integration):
    """Testa a geração de resposta com prompt vazio."""
    prompt = ""
    
    with patch('requests.post') as mock_post:
        response = ollama_integration.generate_response(prompt)
        assert response is None
        mock_post.assert_not_called()

def test_generate_response_with_long_prompt(ollama_integration):
    """Testa a geração de resposta com prompt muito longo."""
    prompt = "a" * 10000  # Prompt muito longo
    
    with patch('requests.post') as mock_post:
        response = ollama_integration.generate_response(prompt)
        assert response is None
        mock_post.assert_not_called()

def test_generate_response_with_special_characters(ollama_integration):
    """Testa a geração de resposta com caracteres especiais."""
    prompt = "Qual é a capital do Brasil? @#$%^&*()"
    
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            'response': "A capital do Brasil é Brasília."
        }
        
        response = ollama_integration.generate_response(prompt)
        assert response is not None
        mock_post.assert_called_once()

def test_generate_response_with_unicode(ollama_integration):
    """Testa a geração de resposta com caracteres Unicode."""
    prompt = "Qual é a capital do Brasil? çãõé"
    
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            'response': "A capital do Brasil é Brasília."
        }
        
        response = ollama_integration.generate_response(prompt)
        assert response is not None
        mock_post.assert_called_once()

def test_should_close_conversation_with_farewell():
    """Testa a detecção de encerramento quando há despedida clara."""
    # Mensagens com despedida clara
    messages = [
        {"remetente": "cliente", "conteudo": "Obrigado pela ajuda!"},
        {"remetente": "atendente", "conteudo": "Disponha, foi um prazer atendê-lo."},
        {"remetente": "cliente", "conteudo": "Tenha um bom dia, tchau!"},
        {"remetente": "atendente", "conteudo": "Igualmente, até mais!"}
    ]
    
    expected_result = {
        "should_close": True,
        "confidence": 95,
        "reason": "despedida"
    }
    
    ollama = OllamaIntegration()
    
    # Mock para o método generate
    with patch.object(ollama, 'generate') as mock_generate:
        # Simula a resposta do modelo
        mock_generate.return_value = """```json
{
  "should_close": true,
  "confidence": 95,
  "reason": "despedida"
}
```"""
        
        # Executa o método
        result = ollama.should_close_conversation(messages)
        
        # Verifica se o prompt correto foi gerado
        prompt = get_default_conversation_closure_prompt(messages)
        mock_generate.assert_called_once_with(prompt)
        
        # Verifica o resultado
        assert result == expected_result

def test_should_close_conversation_active_conversation():
    """Testa a detecção quando a conversa ainda está ativa."""
    # Mensagens sem indicação de encerramento
    messages = [
        {"remetente": "cliente", "conteudo": "Gostaria de saber sobre o produto X"},
        {"remetente": "atendente", "conteudo": "Claro, o produto X custa R$50"},
        {"remetente": "cliente", "conteudo": "E quanto tempo demora para entregar?"},
    ]
    
    expected_result = {
        "should_close": False,
        "confidence": 80,
        "reason": "conversa ativa"
    }
    
    ollama = OllamaIntegration()
    
    # Mock para o método generate
    with patch.object(ollama, 'generate') as mock_generate:
        # Simula a resposta do modelo
        mock_generate.return_value = """```json
{
  "should_close": false,
  "confidence": 80,
  "reason": "conversa ativa"
}
```"""
        
        # Executa o método
        result = ollama.should_close_conversation(messages)
        
        # Verifica o resultado
        assert result == expected_result

def test_should_close_conversation_error_handling():
    """Testa o tratamento de erros durante a verificação de encerramento."""
    messages = [
        {"remetente": "cliente", "conteudo": "Obrigado!"},
        {"remetente": "atendente", "conteudo": "De nada!"},
    ]
    
    expected_result = {
        "should_close": False,
        "confidence": 0,
        "reason": "erro_processamento"
    }
    
    ollama = OllamaIntegration()
    
    # Mock para o método generate que lança exceção
    with patch.object(ollama, 'generate') as mock_generate:
        mock_generate.side_effect = Exception("Erro de conexão")
        
        # Executa o método
        result = ollama.should_close_conversation(messages)
        
        # Verifica se o resultado padrão foi retornado
        assert result == expected_result

def test_should_close_conversation_invalid_json():
    """Testa quando o modelo retorna uma resposta que não é um JSON válido."""
    messages = [
        {"remetente": "cliente", "conteudo": "Obrigado pela ajuda"},
        {"remetente": "atendente", "conteudo": "Por nada!"},
    ]
    
    expected_result = {
        "should_close": False,
        "confidence": 0,
        "reason": "erro_analise"
    }
    
    ollama = OllamaIntegration()
    
    # Mock para o método generate que retorna texto sem JSON
    with patch.object(ollama, 'generate') as mock_generate:
        mock_generate.return_value = "A conversa parece estar chegando ao fim."
        
        # Executa o método
        result = ollama.should_close_conversation(messages)
        
        # Verifica se o resultado padrão foi retornado
        assert result == expected_result

def test_should_close_function():
    """Testa a função de conveniência should_close_conversation."""
    from agent.ollama_integration import should_close_conversation
    
    messages = [
        {"remetente": "cliente", "conteudo": "Obrigado!"},
        {"remetente": "atendente", "conteudo": "De nada!"},
    ]
    
    expected_result = {
        "should_close": True,
        "confidence": 90,
        "reason": "despedida"
    }
    
    # Mock para a classe OllamaIntegration
    with patch('agent.ollama_integration.OllamaIntegration') as mock_class:
        # Configura o mock para retornar uma instância mockada
        instance = mock_class.return_value
        instance.should_close_conversation.return_value = expected_result
        
        # Executa a função
        result = should_close_conversation(messages)
        
        # Verifica se o método foi chamado corretamente
        instance.should_close_conversation.assert_called_once_with(messages)
        
        # Verifica o resultado
        assert result == expected_result 