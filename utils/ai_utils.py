import os
import json
import requests
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from loguru import logger

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do Ollama
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder:1.5b")

# Configuração de timezone
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
tz = pytz.timezone(TIMEZONE)

def create_conversation_prompt(mensagens):
    """
    Cria um prompt para a análise da conversa pelo modelo.
    
    Args:
        mensagens (list): Lista de mensagens no formato JSON
        
    Returns:
        str: Prompt formatado para o modelo
    """
    # Formata as mensagens para o prompt
    conversa_texto = ""
    for i, msg in enumerate(mensagens):
        role = "Cliente" if msg["role"] == "cliente" else "Atendente"
        nome = msg.get("name", role)
        timestamp = msg.get("timestamp", "")
        conteudo = msg.get("content", "")
        
        conversa_texto += f"{timestamp} - {nome} ({role}): {conteudo}\n\n"
    
    # Constrói o prompt completo
    prompt = f"""Analise a seguinte conversa de WhatsApp entre um cliente e um atendente:

{conversa_texto}

Extraia as seguintes informações:
1. Nome do cliente (se mencionado)
2. Nome do atendente (se mencionado)
3. Indique se a conversa parece ter sido concluída/finalizada
4. Se concluída, indique o motivo (problema resolvido, agradecimento, etc.)

Responda APENAS no formato JSON:
{{
  "customer_name": "nome ou null se não mencionado",
  "attendant_name": "nome ou null se não mencionado",
  "is_concluded": true/false,
  "conclusion_reason": "motivo ou null se não concluída"
}}"""

    return prompt

def extract_conversation_metadata(prompt):
    """
    Extrai metadados da conversa usando o modelo Deepseek-Coder.
    
    Args:
        prompt (str): Prompt para o modelo
        
    Returns:
        dict: Dicionário com metadados extraídos
    """
    try:
        # Configuração da chamada para o Ollama
        url = f"{OLLAMA_API_URL}/generate"
        payload = {
            "model": DEEPSEEK_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1
        }
        
        # Chamada para o Ollama
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            logger.error(f"Erro ao chamar Ollama: {response.status_code} - {response.text}")
            return {
                "customer_name": None,
                "attendant_name": None,
                "is_concluded": False,
                "conclusion_reason": None
            }
        
        # Processa a resposta
        result = response.json()
        response_text = result.get("response", "")
        
        # Extrai o JSON da resposta
        try:
            # Tenta encontrar o JSON na resposta
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                data = json.loads(json_text)
                
                # Monta o resultado
                return {
                    "customer_name": data.get("customer_name") if data.get("customer_name") != "null" else None,
                    "attendant_name": data.get("attendant_name") if data.get("attendant_name") != "null" else None,
                    "conversation_closed": data.get("is_concluded", False),
                    "close_reason": data.get("conclusion_reason") if data.get("conclusion_reason") != "null" else None
                }
            else:
                logger.error(f"Não foi possível encontrar JSON na resposta: {response_text}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e} - Resposta: {response_text}")
            
    except Exception as e:
        logger.error(f"Erro ao extrair metadados da conversa: {str(e)}")
    
    # Retorno padrão em caso de erro
    return {
        "customer_name": None,
        "attendant_name": None,
        "conversation_closed": False,
        "close_reason": None
    }

def check_conversation_status(mensagens):
    """
    Verifica se uma conversa foi concluída com base nas mensagens.
    
    Args:
        mensagens (list): Lista de mensagens da conversa
        
    Returns:
        dict: Dicionário indicando se a conversa foi concluída e o motivo
    """
    try:
        # Verifica se há mensagens suficientes
        if len(mensagens) < 2:
            return {"conversation_closed": False, "close_reason": None}
        
        # Cria o prompt para o modelo
        prompt = """Analise as últimas mensagens desta conversa de WhatsApp entre cliente e atendente:

"""
        # Adiciona as mensagens ao prompt
        for msg in mensagens:
            role = "Cliente" if msg["role"] == "cliente" else "Atendente"
            prompt += f"{role}: {msg['content']}\n\n"
        
        prompt += """Determine se a conversa pode ser considerada finalizada. Uma conversa finalizada geralmente tem:
1. Uma clara resolução do problema ou solicitação inicial
2. Confirmação do cliente de que está satisfeito
3. Agradecimentos finais ou despedidas de ambas as partes
4. Ausência de perguntas pendentes do cliente

Responda APENAS no formato JSON:
{
  "conversation_closed": true/false,
  "close_reason": "Motivo do encerramento ou null se não encerrada"
}"""

        # Configuração da chamada para o Ollama
        url = f"{OLLAMA_API_URL}/generate"
        payload = {
            "model": DEEPSEEK_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1
        }
        
        # Chamada para o Ollama
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            logger.error(f"Erro ao chamar Ollama: {response.status_code} - {response.text}")
            return {"conversation_closed": False, "close_reason": None}
        
        # Processa a resposta
        result = response.json()
        response_text = result.get("response", "")
        
        # Extrai o JSON da resposta
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                data = json.loads(json_text)
                
                return {
                    "conversation_closed": data.get("conversation_closed", False),
                    "close_reason": data.get("close_reason") if data.get("close_reason") != "null" else None
                }
            else:
                logger.error(f"Não foi possível encontrar JSON na resposta: {response_text}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e} - Resposta: {response_text}")
            
    except Exception as e:
        logger.error(f"Erro ao verificar status da conversa: {str(e)}")
    
    # Retorno padrão em caso de erro
    return {"conversation_closed": False, "close_reason": None}

def analyze_request(mensagens):
    """
    Analisa se uma mensagem contém uma solicitação e identifica o prazo prometido.
    
    Args:
        mensagens (list): Lista de mensagens para análise (geralmente uma mensagem do cliente 
                         seguida de uma resposta do atendente, se disponível)
        
    Returns:
        dict: Resultado da análise contendo informações sobre a solicitação e prazo
    """
    try:
        # Cria o prompt para o modelo
        prompt = """Analise a seguinte troca de mensagens do WhatsApp:

"""
        # Adiciona as mensagens ao prompt
        for msg in mensagens:
            role = "Cliente" if msg["role"] == "cliente" else "Atendente"
            prompt += f"{role}: {msg['content']}\n\n"
        
        prompt += """Determine:
1. Se a mensagem do cliente contém uma solicitação ou pedido que requer uma ação do atendente
2. Se a resposta do atendente (se existir) menciona um prazo para atendimento da solicitação
3. Extraia o prazo mencionado, se houver (ex: "amanhã", "em 3 dias úteis", "até sexta-feira")
4. Estime quantos dias úteis o prazo representa (sendo 1 dia útil o padrão se não especificado)

Responda APENAS no formato JSON:
{
  "is_request": true/false,
  "request_description": "descrição da solicitação ou null",
  "has_deadline": true/false,
  "deadline_mentioned": "texto do prazo mencionado ou null",
  "business_days": número de dias úteis ou 1 se não especificado,
  "deadline_date": "YYYY-MM-DD" (data estimada baseada no prazo, se possível determinar, ou null)
}"""

        # Configuração da chamada para o Ollama
        url = f"{OLLAMA_API_URL}/generate"
        payload = {
            "model": DEEPSEEK_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1
        }
        
        # Chamada para o Ollama
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            logger.error(f"Erro ao chamar Ollama: {response.status_code} - {response.text}")
            return {
                "is_request": False,
                "request_description": None,
                "has_deadline": False,
                "deadline_date": None,
                "business_days": 1
            }
        
        # Processa a resposta
        result = response.json()
        response_text = result.get("response", "")
        
        # Extrai o JSON da resposta
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx != -1 and end_idx != -1:
                json_text = response_text[start_idx:end_idx]
                data = json.loads(json_text)
                
                # Processa o prazo para uma data real, se possível
                deadline_date = data.get("deadline_date")
                if data.get("has_deadline", False) and not deadline_date:
                    # Se não houver data específica, calcula com base nos dias úteis
                    dias_uteis = data.get("business_days", 1)
                    deadline_date = calculate_business_date(dias_uteis)
                
                return {
                    "is_request": data.get("is_request", False),
                    "request_description": data.get("request_description") if data.get("request_description") != "null" else None,
                    "has_deadline": data.get("has_deadline", False),
                    "deadline_date": deadline_date,
                    "business_days": data.get("business_days", 1)
                }
            else:
                logger.error(f"Não foi possível encontrar JSON na resposta: {response_text}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e} - Resposta: {response_text}")
            
    except Exception as e:
        logger.error(f"Erro ao analisar solicitação: {str(e)}")
    
    # Retorno padrão em caso de erro
    return {
        "is_request": False,
        "request_description": None,
        "has_deadline": False,
        "deadline_date": None,
        "business_days": 1
    }

def calculate_business_date(dias_uteis, data_inicio=None):
    """
    Calcula uma data futura considerando apenas dias úteis (segunda a sexta).
    
    Args:
        dias_uteis (int): Número de dias úteis a adicionar
        data_inicio (datetime, optional): Data inicial. Se None, usa a data atual.
        
    Returns:
        str: Data calculada no formato 'YYYY-MM-DD'
    """
    # Se não houver data de início, usa a data atual
    if data_inicio is None:
        data_inicio = datetime.now(tz)
    
    # Inicializa contador e data atual
    dias_adicionados = 0
    data_atual = data_inicio
    
    # Adiciona dias até atingir o número de dias úteis
    while dias_adicionados < dias_uteis:
        data_atual += timedelta(days=1)
        # Verifica se é dia útil (0 = segunda, 6 = domingo)
        if data_atual.weekday() < 5:  # Segunda a Sexta
            dias_adicionados += 1
    
    # Retorna no formato YYYY-MM-DD
    return data_atual.strftime("%Y-%m-%d") 