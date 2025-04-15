"""Testes para as funções auxiliares."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from utils.helpers import (
    calculate_response_time,
    extract_mentions,
    extract_numbers,
    format_datetime,
    get_current_timezone,
    is_business_hours,
    normalize_phone_number,
    parse_datetime,
    safe_json_dumps,
    safe_json_loads,
    truncate_text,
)


def test_parse_datetime():
    """Testa a função de parsing de data e hora."""
    # Teste com formato ISO
    dt_str = "2024-01-15T10:30:00-03:00"
    result = parse_datetime(dt_str)
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 10
    assert result.minute == 30

    # Teste com timestamp
    timestamp = 1705326600  # 2024-01-15 10:30:00
    result = parse_datetime(timestamp)
    assert isinstance(result, datetime)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15

    # Teste com formato inválido
    with pytest.raises(ValueError):
        parse_datetime("formato_invalido")


def test_format_datetime():
    """Testa a função de formatação de data e hora."""
    dt = datetime(2024, 1, 15, 10, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
    
    # Teste formato padrão
    result = format_datetime(dt)
    assert isinstance(result, str)
    assert "2024-01-15" in result
    assert "10:30" in result

    # Teste formato personalizado
    result = format_datetime(dt, fmt="%d/%m/%Y")
    assert result == "15/01/2024"

    # Teste com timezone diferente
    result = format_datetime(dt, timezone="UTC")
    assert isinstance(result, str)


def test_extract_mentions():
    """Testa a função de extração de menções."""
    text = "@joao Por favor, verifique isso. cc @maria @pedro"
    mentions = extract_mentions(text)
    assert len(mentions) == 3
    assert "joao" in mentions
    assert "maria" in mentions
    assert "pedro" in mentions

    # Teste sem menções
    assert not extract_mentions("Texto sem menções")

    # Teste com texto vazio
    assert not extract_mentions("")


def test_extract_numbers():
    """Testa a função de extração de números."""
    text = "Pedido #123 para o cliente 5511999999999"
    numbers = extract_numbers(text)
    assert len(numbers) == 2
    assert "123" in numbers
    assert "5511999999999" in numbers

    # Teste sem números
    assert not extract_numbers("Texto sem números")

    # Teste com texto vazio
    assert not extract_numbers("")


def test_safe_json_loads():
    """Testa a função de carregamento seguro de JSON."""
    # Teste com JSON válido
    valid_json = '{"key": "value"}'
    result = safe_json_loads(valid_json)
    assert isinstance(result, dict)
    assert result["key"] == "value"

    # Teste com JSON inválido
    invalid_json = "invalid_json"
    result = safe_json_loads(invalid_json)
    assert result == {}

    # Teste com JSON vazio
    assert safe_json_loads("") == {}


def test_safe_json_dumps():
    """Testa a função de serialização segura de JSON."""
    # Teste com dict válido
    data = {"key": "value"}
    result = safe_json_dumps(data)
    assert isinstance(result, str)
    assert json.loads(result)["key"] == "value"

    # Teste com objeto não serializável
    class TestClass:
        pass
    obj = TestClass()
    result = safe_json_dumps(obj)
    assert result == "{}"

    # Teste com None
    assert safe_json_dumps(None) == "{}"


def test_calculate_response_time():
    """Testa a função de cálculo de tempo de resposta."""
    now = datetime.now()
    msg_time = now - timedelta(minutes=5)
    
    # Teste dentro do horário comercial
    with pytest.patch("utils.helpers.is_business_hours", return_value=True):
        time = calculate_response_time(msg_time, now)
        assert time == 300  # 5 minutos em segundos

    # Teste fora do horário comercial
    with pytest.patch("utils.helpers.is_business_hours", return_value=False):
        time = calculate_response_time(msg_time, now)
        assert time == 0


@pytest.mark.parametrize(
    "hour,expected",
    [
        (9, True),   # 9h - Horário comercial
        (14, True),  # 14h - Horário comercial
        (18, True),  # 18h - Horário comercial
        (7, False),  # 7h - Fora do horário
        (20, False), # 20h - Fora do horário
    ],
)
def test_is_business_hours(hour, expected):
    """Testa a função de verificação de horário comercial."""
    dt = datetime.now().replace(hour=hour)
    assert is_business_hours(dt) == expected


def test_normalize_phone_number():
    """Testa a função de normalização de números de telefone."""
    # Teste com número completo
    assert normalize_phone_number("5511999999999") == "5511999999999"
    
    # Teste com formatação
    assert normalize_phone_number("+55 (11) 99999-9999") == "5511999999999"
    
    # Teste com número inválido
    with pytest.raises(ValueError):
        normalize_phone_number("numero_invalido")


def test_truncate_text():
    """Testa a função de truncamento de texto."""
    text = "Este é um texto longo que precisa ser truncado"
    
    # Teste com limite maior que o texto
    assert truncate_text(text, 100) == text
    
    # Teste com truncamento
    result = truncate_text(text, 10)
    assert len(result) <= 13  # 10 caracteres + "..."
    assert result.endswith("...")
    
    # Teste com texto vazio
    assert truncate_text("", 10) == ""


def test_get_current_timezone():
    """Testa a função de obtenção do timezone atual."""
    tz = get_current_timezone()
    assert isinstance(tz, ZoneInfo)
    assert str(tz) == "America/Sao_Paulo"  # Timezone configurado no .env 