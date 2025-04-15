import re
from typing import List, Tuple, Dict, Any
from loguru import logger

def detect_greeting_patterns(text: str) -> bool:
    """
    Detecta padrões de saudação em um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        True se encontrar padrões de saudação, False caso contrário
    """
    greetings = [
        r'\b(olá|ola|oi|bom dia|boa tarde|boa noite)\b',
        r'\b(bem[ -]vindo|como posso ajudar)\b',
        r'\b(prazer|como vai|tudo bem)\b'
    ]
    
    text = text.lower()
    for pattern in greetings:
        if re.search(pattern, text):
            return True
    return False

def detect_farewell_patterns(text: str) -> bool:
    """
    Detecta padrões de despedida em um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        True se encontrar padrões de despedida, False caso contrário
    """
    farewells = [
        r'\b(tchau|até|adeus|até( mais| logo| breve)?)\b',
        r'\b(obrigad[oa]|agradeç[oa]|valeu)\b',
        r'\b(bom dia|boa tarde|boa noite)\b',
        r'\b(tenha um[a]? (bom|boa|ótimo|ótima))\b'
    ]
    
    text = text.lower()
    for pattern in farewells:
        if re.search(pattern, text):
            return True
    return False

def detect_request_patterns(text: str) -> Tuple[bool, str]:
    """
    Detecta padrões de solicitação em um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Tupla com (bool indicando se é solicitação, tipo de solicitação)
    """
    request_patterns = {
        'informação': [
            r'\b(como|qual|onde|quando|quem|por[ ]?que)\b.*\?',
            r'\b(gostaria|preciso|quero|pode[ria]*) (de )?saber\b',
            r'\b(tem|existe|há) (como|algum[a])\b'
        ],
        'suporte': [
            r'\b(ajuda|socorro|auxílio|suporte)\b',
            r'\b(não consigo|problema|erro|bug|falha)\b',
            r'\b(preciso|gostaria) de (ajuda|auxílio|suporte)\b'
        ],
        'reclamação': [
            r'\b(reclama[rção]*|queixa|insatisf[eação]*)\b',
            r'\b(não.*funcion[aou]|péssimo|ruim|horrível)\b',
            r'\b(demora|atraso|inaceitável|absurdo)\b'
        ]
    }
    
    text = text.lower()
    for req_type, patterns in request_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return True, req_type
    return False, ''

def detect_urgency_patterns(text: str) -> int:
    """
    Detecta padrões de urgência em um texto e retorna um nível.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Nível de urgência (0-3)
    """
    urgency_patterns = {
        3: [  # Alta urgência
            r'\b(urgente|emergência|emergencial)\b',
            r'\b(preciso|necessito).*(agora|imediato|urgente)\b',
            r'\b(não pode|impossível) esperar\b'
        ],
        2: [  # Média urgência
            r'\b(assim que possível|logo|breve)\b',
            r'\b(preciso|quero).*(hoje|amanhã)\b',
            r'\b(importante|prioritário)\b'
        ],
        1: [  # Baixa urgência
            r'\b(quando puder|sem pressa)\b',
            r'\b(nos próximos dias|essa semana)\b',
            r'\b(gostaria|se possível)\b'
        ]
    }
    
    text = text.lower()
    max_urgency = 0
    
    for level, patterns in urgency_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text):
                max_urgency = max(max_urgency, level)
                
    return max_urgency

def detect_sentiment(text: str) -> float:
    """
    Analisa o sentimento do texto e retorna um score.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Score de sentimento (-1.0 a 1.0)
    """
    positive_patterns = [
        r'\b(bom|boa|ótimo|ótima|excelente|maravilhos[oa])\b',
        r'\b(agrad[eça]*|obrigad[oa]|valeu)\b',
        r'\b(gost[eio]|ador[eio]|am[eio])\b',
        r'\b(😊|😃|👍|❤️|🙏)\b'
    ]
    
    negative_patterns = [
        r'\b(ruim|péssimo|horrível|terrível)\b',
        r'\b(insatisfeit[oa]|chatea[dor]|frustrad[oa])\b',
        r'\b(reclam[aor]|queix[ao]|problem[ao])\b',
        r'\b(😠|😡|👎|😤|😢)\b'
    ]
    
    text = text.lower()
    positive_count = sum(bool(re.search(p, text)) for p in positive_patterns)
    negative_count = sum(bool(re.search(p, text)) for p in negative_patterns)
    
    if positive_count == 0 and negative_count == 0:
        return 0.0
        
    total = positive_count + negative_count
    return (positive_count - negative_count) / total

def extract_promised_deadline(text: str) -> Tuple[int, str]:
    """
    Extrai prazo prometido de um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Tupla com (quantidade de dias úteis, texto do prazo)
    """
    deadline_patterns = {
        1: [
            r'\b(hoje|agora|imediato|nesse momento)\b',
            r'\bem até (1|uma?) hora\b',
            r'\bainda hoje\b'
        ],
        2: [
            r'\b(amanhã|próximo dia útil)\b',
            r'\bem (24|vinte e quatro) horas\b'
        ],
        3: [
            r'\bem (2|dois|3|três) dias( úteis)?\b',
            r'\baté (2|dois|3|três) dias( úteis)?\b'
        ],
        5: [
            r'\bem (4|quatro|5|cinco) dias( úteis)?\b',
            r'\baté (4|quatro|5|cinco) dias( úteis)?\b',
            r'\bessa semana\b'
        ]
    }
    
    text = text.lower()
    for days, patterns in deadline_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return days, match.group(0)
                
    return 0, ''

def analyze_response_quality(text: str) -> Dict[str, Any]:
    """
    Analisa a qualidade de uma resposta considerando múltiplos fatores.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Dicionário com métricas de qualidade
    """
    try:
        # Inicializar métricas
        metrics = {
            'has_greeting': detect_greeting_patterns(text),
            'has_farewell': detect_farewell_patterns(text),
            'sentiment_score': detect_sentiment(text),
            'word_count': len(text.split()),
            'has_question': '?' in text,
            'formality_level': 0
        }
        
        # Analisar formalidade
        formal_indicators = [
            r'\b(senhor[a]?|prezad[oa])\b',
            r'\b(por favor|por gentileza)\b',
            r'\b(cordialmente|atenciosamente)\b'
        ]
        
        informal_indicators = [
            r'\b(cara|mano|brother|blz|vlw)\b',
            r'\b(beleza|tranquilo|falou)\b',
            r'[kkk]+|[rs]+|[hue]+'
        ]
        
        text_lower = text.lower()
        formal_count = sum(bool(re.search(p, text_lower)) for p in formal_indicators)
        informal_count = sum(bool(re.search(p, text_lower)) for p in informal_indicators)
        
        # Calcular nível de formalidade (-1 a 1)
        if formal_count > 0 or informal_count > 0:
            metrics['formality_level'] = (formal_count - informal_count) / (formal_count + informal_count)
            
        return metrics
        
    except Exception as e:
        logger.error(f"Erro ao analisar qualidade da resposta: {str(e)}")
        return {
            'has_greeting': False,
            'has_farewell': False,
            'sentiment_score': 0,
            'word_count': 0,
            'has_question': False,
            'formality_level': 0
        } 