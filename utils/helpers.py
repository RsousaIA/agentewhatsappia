import re
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import pytz
from loguru import logger
import os

def parse_datetime(date_str: str) -> datetime:
    """
    Converte uma string de data/hora para objeto datetime.
    
    Args:
        date_str: String contendo a data/hora
        
    Returns:
        Objeto datetime correspondente
    """
    try:
        # Tentar diferentes formatos comuns
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d/%m/%Y %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        raise ValueError(f"Formato de data não reconhecido: {date_str}")
        
    except Exception as e:
        logger.error(f"Erro ao converter data {date_str}: {str(e)}")
        raise

def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Formata um objeto datetime para string.
    
    Args:
        dt: Objeto datetime
        fmt: Formato desejado (opcional)
        
    Returns:
        String formatada com a data/hora
    """
    try:
        return dt.strftime(fmt)
    except Exception as e:
        logger.error(f"Erro ao formatar data {dt}: {str(e)}")
        raise

def extract_mentions(text: str) -> List[str]:
    """
    Extrai menções (@usuario) de um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Lista de menções encontradas
    """
    mentions = re.findall(r'@(\w+)', text)
    return mentions

def extract_numbers(text: str) -> List[str]:
    """
    Extrai números de telefone de um texto.
    
    Args:
        text: Texto a ser analisado
        
    Returns:
        Lista de números encontrados
    """
    # Padrão para números brasileiros
    pattern = r'(?:55)?(?:\s|-)*((?:(?:\d{2})|(?:\(\d{2}\)))(?:\s|-)*(?:9?\d{4})(?:\s|-)*(?:\d{4}))'
    numbers = re.findall(pattern, text)
    return [re.sub(r'\D', '', num) for num in numbers]

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """
    Converte string JSON para dicionário de forma segura.
    
    Args:
        json_str: String JSON
        
    Returns:
        Dicionário com os dados do JSON
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON: {str(e)}")
        return {}

def safe_json_dumps(obj: Any) -> str:
    """
    Converte objeto para string JSON de forma segura.
    
    Args:
        obj: Objeto a ser convertido
        
    Returns:
        String JSON
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao codificar JSON: {str(e)}")
        return "{}"

def calculate_response_time(start_time: datetime, end_time: datetime) -> int:
    """
    Calcula o tempo de resposta em segundos entre duas datas.
    
    Args:
        start_time: Data/hora inicial
        end_time: Data/hora final
        
    Returns:
        Tempo em segundos
    """
    try:
        delta = end_time - start_time
        return int(delta.total_seconds())
    except Exception as e:
        logger.error(f"Erro ao calcular tempo de resposta: {str(e)}")
        return 0

def is_business_hours(dt: datetime = None, start_hour: int = 8, end_hour: int = 18) -> bool:
    """
    Verifica se um determinado momento está dentro do horário comercial.
    
    Args:
        dt: Data/hora a verificar (opcional, usa hora atual se não informado)
        start_hour: Hora inicial do expediente
        end_hour: Hora final do expediente
        
    Returns:
        True se estiver em horário comercial, False caso contrário
    """
    if dt is None:
        dt = datetime.now()
        
    # Verificar se é fim de semana
    if dt.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
        return False
        
    return start_hour <= dt.hour < end_hour

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Trunca um texto para um tamanho máximo, adicionando reticências.
    
    Args:
        text: Texto a ser truncado
        max_length: Tamanho máximo desejado
        
    Returns:
        Texto truncado
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def normalize_phone_number(phone: str) -> str:
    """
    Normaliza um número de telefone removendo caracteres especiais.
    
    Args:
        phone: Número de telefone
        
    Returns:
        Número normalizado
    """
    # Remover todos os caracteres não numéricos
    normalized = re.sub(r'\D', '', phone)
    
    # Garantir que começa com 55 (Brasil)
    if not normalized.startswith('55'):
        normalized = '55' + normalized
        
    return normalized

def get_current_timezone():
    """
    Obtém o timezone configurado ou usa America/Sao_Paulo como padrão.
    
    Returns:
        Objeto timezone
    """
    try:
        tz_name = os.getenv('TIMEZONE', 'America/Sao_Paulo')
        return pytz.timezone(tz_name)
    except Exception as e:
        logger.error(f"Erro ao obter timezone: {str(e)}")
        return pytz.timezone('America/Sao_Paulo') 