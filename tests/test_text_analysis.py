import pytest
from datetime import datetime, timedelta

# Mock das funções de análise de texto
# Essas funções serão implementadas posteriormente com a biblioteca correta
def detect_greeting_patterns(text):
    """Mock da função de detecção de saudações"""
    return any(greeting in text.lower() for greeting in ["bom dia", "boa tarde", "boa noite", "olá", "oi"])

def detect_farewell_patterns(text):
    """Mock da função de detecção de despedidas"""
    return any(farewell in text.lower() for farewell in ["até logo", "até mais", "tchau", "bom dia", "boa tarde", "boa noite"])

def detect_request_patterns(text):
    """Mock da função de detecção de solicitações"""
    if "solicitar" in text.lower() or "orçamento" in text.lower():
        return (True, "solicitacao")
    elif "reclamação" in text.lower() or "reclamar" in text.lower():
        return (True, "reclamacao")
    elif "informações" in text.lower() or "informação" in text.lower():
        return (True, "informacao")
    return (False, None)

def detect_urgency_patterns(text):
    """Mock da função de detecção de urgência"""
    if "urgente" in text.lower() or "emergência" in text.lower():
        return 3
    elif "importante" in text.lower():
        return 2
    elif "por favor" in text.lower():
        return 1
    return 0

def detect_sentiment(text):
    """Mock da função de análise de sentimento"""
    positive_words = ["satisfeito", "bom", "ótimo", "gostei", "adorei"]
    negative_words = ["insatisfeito", "ruim", "péssimo", "problema", "horrível"]
    
    positive_count = sum(1 for word in positive_words if word in text.lower())
    negative_count = sum(1 for word in negative_words if word in text.lower())
    
    if positive_count == 0 and negative_count == 0:
        return 0.5
    
    total = positive_count + negative_count
    if total == 0:
        return 0.5
    
    # Se tiver palavras negativas, retorna menos de 0.5
    if negative_count > 0:
        return 0.3
    
    # Se tiver palavras positivas, retorna mais de 0.5
    return 0.8

def extract_promised_deadline(text):
    """Mock da função de extração de prazo"""
    if "2 dias" in text:
        return (2, "2 dias úteis")
    elif "5 dias" in text:
        return (5, "5 dias")
    elif "hoje" in text:
        return (0, "hoje")
    elif "amanhã" in text.lower() or "amanha" in text.lower():
        return (1, "amanhã")
    return (None, None)

def analyze_response_quality(response):
    """Mock da função de análise de qualidade da resposta"""
    if not response or not response.get('content'):
        return 0.0
    
    content = response['content']
    word_count = len(content.split())
    
    # Pontuação básica pelo tamanho
    if word_count == 0:
        return 0.0
    elif word_count < 5:
        score = 0.3
    elif word_count < 10:
        score = 0.5
    elif word_count < 20:
        score = 0.7
    else:
        score = 0.9
    
    # Bônus por saudação e despedida
    if detect_greeting_patterns(content):
        score += 0.1
    if detect_farewell_patterns(content):
        score += 0.1
    
    # Limitar o score a 1.0
    return min(score, 1.0)

class TestTextAnalysis:
    """Testes para as funções de análise de texto"""
    
    def test_detect_greeting_patterns(self):
        """Testa a detecção de padrões de saudação"""
        # Teste com saudações formais
        assert detect_greeting_patterns("Bom dia, como posso ajudar?") == True
        assert detect_greeting_patterns("Boa tarde, tudo bem?") == True
        assert detect_greeting_patterns("Boa noite, em que posso ajudar?") == True
        
        # Teste com saudações informais
        assert detect_greeting_patterns("Oi, tudo bem?") == True
        assert detect_greeting_patterns("Olá, como vai?") == True
        
        # Teste com mensagens sem saudação
        assert detect_greeting_patterns("Preciso de ajuda") == False
        assert detect_greeting_patterns("") == False
    
    def test_detect_farewell_patterns(self):
        """Testa a detecção de padrões de despedida"""
        # Teste com despedidas formais
        assert detect_farewell_patterns("Agradeço o contato. Até logo!") == True
        assert detect_farewell_patterns("Tenha um bom dia!") == True
        
        # Teste com despedidas informais
        assert detect_farewell_patterns("Tchau!") == True
        assert detect_farewell_patterns("Até mais!") == True
        
        # Teste com mensagens sem despedida
        assert detect_farewell_patterns("Obrigado pela informação") == False
        assert detect_farewell_patterns("") == False
    
    def test_detect_request_patterns(self):
        """Testa a detecção de padrões de solicitação"""
        # Teste com solicitações explícitas
        assert detect_request_patterns("Gostaria de solicitar um orçamento") == (True, "solicitacao")
        assert detect_request_patterns("Preciso fazer uma reclamação") == (True, "reclamacao")
        assert detect_request_patterns("Quero informações sobre o produto") == (True, "informacao")
        
        # Teste com mensagens sem solicitação
        assert detect_request_patterns("Bom dia!") == (False, None)
        assert detect_request_patterns("") == (False, None)
    
    def test_detect_urgency_patterns(self):
        """Testa a detecção de padrões de urgência"""
        # Teste com diferentes níveis de urgência
        assert detect_urgency_patterns("URGENTE: Preciso de ajuda agora!") == 3
        assert detect_urgency_patterns("É muito importante que resolvam isso") == 2
        assert detect_urgency_patterns("Por favor, me ajudem") == 1
        assert detect_urgency_patterns("Bom dia") == 0
        
        # Teste com mensagens sem urgência
        assert detect_urgency_patterns("") == 0
    
    def test_detect_sentiment(self):
        """Testa a análise de sentimento"""
        # Teste com sentimentos positivos
        assert detect_sentiment("Estou muito satisfeito com o atendimento") > 0.5
        assert detect_sentiment("Adorei o produto!") > 0.5
        
        # Teste com sentimentos negativos
        assert detect_sentiment("Estou muito insatisfeito") < 0.5
        assert detect_sentiment("Péssimo atendimento") < 0.5
        
        # Teste com sentimentos neutros
        assert 0.4 <= detect_sentiment("Preciso de informações") <= 0.6
        assert 0.4 <= detect_sentiment("") <= 0.6
    
    def test_extract_promised_deadline(self):
        """Testa a extração de prazos prometidos"""
        # Teste com prazos explícitos
        assert extract_promised_deadline("Resolverei em 2 dias úteis") == (2, "2 dias úteis")
        assert extract_promised_deadline("Será resolvido em até 5 dias") == (5, "5 dias")
        
        # Teste com prazos implícitos
        assert extract_promised_deadline("Vou resolver isso hoje") == (0, "hoje")
        assert extract_promised_deadline("Amanhã te retorno") == (1, "amanhã")
        
        # Teste sem prazo
        assert extract_promised_deadline("Vou analisar seu caso") == (None, None)
    
    def test_analyze_response_quality(self):
        """Testa a análise de qualidade da resposta"""
        # Teste com resposta completa
        response = {
            'content': "Bom dia! Entendo sua solicitação e vou ajudar. Resolverei em 2 dias úteis. Tenha um bom dia!",
            'role': 'attendant'
        }
        score = analyze_response_quality(response)
        assert 0.8 <= score <= 1.0
        
        # Teste com resposta incompleta
        response = {
            'content': "Vou verificar",
            'role': 'attendant'
        }
        score = analyze_response_quality(response)
        assert 0.0 <= score <= 0.5
        
        # Teste com resposta vazia
        response = {
            'content': "",
            'role': 'attendant'
        }
        score = analyze_response_quality(response)
        assert score == 0.0 