import datetime
import holidays
import pytz
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Obtém o fuso horário a partir das variáveis de ambiente
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

def get_current_time():
    """Retorna a data e hora atual no fuso horário configurado"""
    return datetime.datetime.now(pytz.timezone(TIMEZONE))

def is_business_day(date):
    """Verifica se a data é um dia útil (não é final de semana nem feriado)"""
    # Se for final de semana (sábado=5, domingo=6)
    if date.weekday() >= 5:
        return False
    
    # Verifica se é feriado (usando a biblioteca holidays para feriados brasileiros)
    br_holidays = holidays.Brazil()
    if date.strftime('%Y-%m-%d') in br_holidays:
        return False
    
    return True

def add_business_days(start_date, num_days):
    """
    Adiciona um número específico de dias úteis a uma data
    
    Args:
        start_date (datetime): Data inicial
        num_days (int): Número de dias úteis a adicionar
    
    Returns:
        datetime: Data resultante após adicionar os dias úteis
    """
    if not isinstance(start_date, datetime.datetime):
        raise ValueError("start_date deve ser um objeto datetime")
    
    # Se o número de dias for 0, retorna a data original
    if num_days <= 0:
        return start_date
    
    # Converte para date se for datetime
    current_date = start_date.date() if isinstance(start_date, datetime.datetime) else start_date
    
    # Adiciona dias úteis
    added_days = 0
    while added_days < num_days:
        current_date += datetime.timedelta(days=1)
        if is_business_day(current_date):
            added_days += 1
    
    # Se a entrada era datetime, retorna datetime com a mesma hora
    if isinstance(start_date, datetime.datetime):
        return datetime.datetime.combine(
            current_date, 
            start_date.time(),
            start_date.tzinfo
        )
    
    return current_date

def calculate_business_days_between(start_date, end_date):
    """
    Calcula o número de dias úteis entre duas datas
    
    Args:
        start_date (datetime): Data inicial
        end_date (datetime): Data final
    
    Returns:
        int: Número de dias úteis entre as datas
    """
    if start_date > end_date:
        return 0
    
    # Extrai apenas as datas (sem hora)
    start = start_date.date() if isinstance(start_date, datetime.datetime) else start_date
    end = end_date.date() if isinstance(end_date, datetime.datetime) else end_date
    
    # Conta os dias úteis
    business_days = 0
    current_date = start
    
    while current_date <= end:
        if is_business_day(current_date):
            business_days += 1
        current_date += datetime.timedelta(days=1)
    
    return business_days

def is_within_business_hours():
    """Verifica se o horário atual está dentro do horário comercial (8h às 18h, segunda a sexta)"""
    now = get_current_time()
    
    # Verifica se é um dia útil
    if not is_business_day(now.date()):
        return False
    
    # Verifica se está dentro do horário comercial (8h às 18h)
    return 8 <= now.hour < 18 