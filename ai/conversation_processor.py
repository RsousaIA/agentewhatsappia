import os
import json
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
from loguru import logger
from dotenv import load_dotenv
import re

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do modelo de IA DeepSeek R1
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:10b")


class ConversationProcessor:
    """
    Processador de conversas que analisa e extrai informações das mensagens.
    """
    
    def __init__(self):
        """
        Inicializa o processador de conversas.
        """
        self.api_url = OLLAMA_API_URL
        self.model = DEEPSEEK_MODEL
        
        # Expressões regulares para detecção de solicitações
        self.request_patterns = [
            r'(?i)preciso\s+(?:de|que|do)',
            r'(?i)(?:pode(?:ria)?|poderia)\s+(?:me\s+)?(?:ajudar|fazer|verificar)',
            r'(?i)gostaria\s+(?:de|que)',
            r'(?i)necessito\s+(?:de|que)',
            r'(?i)quero\s+(?:que|saber)',
            r'(?i)solicito',
            r'(?i)por\s+favor',
            r'(?i)urgente',
            r'(?i)quando\s+(?:pode|vai|será)',
            r'(?i)qual\s+(?:o\s+prazo|previsão)'
        ]
        
        # Expressões regulares para detecção de prazos
        self.deadline_patterns = [
            (r'(?i)hoje', 0),
            (r'(?i)amanh[ãa]', 1),
            (r'(?i)em\s+(\d+)\s+dias?(?:\s+[úu]teis)?', None),  # Valor extraído do grupo
            (r'(?i)(?:na\s+)?(?:segunda|terça|quarta|quinta|sexta|sábado|domingo)', None),
            (r'(?i)pr[óo]xim[oa]\s+(?:semana|m[êe]s)', 7),
            (r'(?i)at[ée]\s+(?:o\s+)?(?:fim|final)\s+d[aoe]\s+(?:semana|m[êe]s)', None)
        ]
        
        # Expressões para identificação de nomes
        self.name_patterns = {
            'saudacao': r'(?i)(?:oi|olá|bom\s+dia|boa\s+tarde|boa\s+noite)[\s,]+([A-ZÀ-Ú][a-zà-ú]+)',
            'apresentacao': r'(?i)(?:me\s+chamo|sou\s+(?:o|a))\s+([A-ZÀ-Ú][a-zà-ú]+)',
            'atendente': r'(?i)(?:atendente|meu\s+nome\s+[ée])\s+([A-ZÀ-Ú][a-zà-ú]+)'
        }
        
        # Verificar conexão com Ollama
        try:
            self._check_model_availability()
            logger.info(f"Conexão com Ollama estabelecida. Modelo {self.model} disponível.")
        except Exception as e:
            logger.error(f"Erro ao conectar com Ollama: {e}")
            raise
        
        logger.info("Processador de conversas inicializado")
    
    def _check_model_availability(self) -> bool:
        """
        Verifica se o modelo está disponível no Ollama.
        
        Returns:
            bool: True se o modelo estiver disponível
        """
        try:
            response = requests.get(f"{self.api_url}/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    if model.get("name") == self.model:
                        return True
                
                logger.warning(f"Modelo {self.model} não encontrado. Modelos disponíveis: {[m['name'] for m in models]}")
                return False
            else:
                logger.error(f"Erro ao verificar modelos: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exceção ao verificar modelos: {e}")
            raise
    
    def generate_completion(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> str:
        """
        Gera uma resposta do modelo DeepSeek R1 via Ollama.
        
        Args:
            prompt: Texto de entrada para o modelo
            temperature: Controle de aleatoriedade (0.0 a 1.0)
            max_tokens: Número máximo de tokens na resposta
            
        Returns:
            str: Resposta gerada pelo modelo
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            start_time = time.time()
            response = requests.post(f"{self.api_url}/generate", json=payload)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "").strip()
                logger.debug(f"Resposta gerada em {elapsed_time:.2f}s")
                return generated_text
            else:
                logger.error(f"Erro ao gerar resposta: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Exceção ao gerar resposta: {e}")
            raise
    
    def detect_request_and_deadline(self, message: Dict[str, Any], previous_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta solicitações e prazos em uma mensagem.
        
        Args:
            message: Mensagem atual
            previous_messages: Mensagens anteriores para contexto
            
        Returns:
            dict: Dicionário com informações da solicitação detectada
        """
        try:
            content = message.get('conteudo', '').strip()
            if not content:
                return None
            
            # Verificar se contém padrões de solicitação
            contains_request = any(re.search(pattern, content) for pattern in self.request_patterns)
            
            if not contains_request:
                return None
            
            # Extrair descrição da solicitação
            description = self._extract_request_description(content)
            
            # Verificar prazo na mensagem atual e respostas do atendente
            deadline_info = self._extract_deadline_from_message(content)
            
            if not deadline_info and previous_messages:
                # Buscar prazo nas respostas do atendente
                attendant_responses = [
                    msg for msg in previous_messages
                    if msg.get('remetente') == 'atendente'
                ]
                
                if attendant_responses:
                    deadline_info = self._extract_deadline_from_responses(
                        content, attendant_responses
                    )
            
            return {
                'contém_solicitação': True,
                'descrição_solicitação': description,
                'prazo_detectado': bool(deadline_info),
                'prazo': deadline_info.get('prazo') if deadline_info else None,
                'dias_uteis': deadline_info.get('dias_uteis') if deadline_info else 1  # Padrão: 1 dia útil
            }
            
        except Exception as e:
            logger.error(f"Erro ao detectar solicitação: {e}")
            return None
    
    def _extract_request_description(self, content: str) -> str:
        """
        Extrai a descrição da solicitação do texto.
        
        Args:
            content: Texto da mensagem
            
        Returns:
            str: Descrição da solicitação
        """
        # Remover pontuação excessiva e normalizar espaços
        content = re.sub(r'[.!?]+', '.', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Tentar extrair a frase que contém a solicitação
        sentences = content.split('.')
        for sentence in sentences:
            if any(re.search(pattern, sentence) for pattern in self.request_patterns):
                return sentence.strip()
        
        # Se não encontrar uma frase específica, retornar o texto completo
        return content
    
    def _extract_deadline_from_message(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extrai informações de prazo de uma mensagem.
        
        Args:
            content: Texto da mensagem
            
        Returns:
            dict: Informações do prazo detectado
        """
        for pattern, days in self.deadline_patterns:
            match = re.search(pattern, content)
            if match:
                if days is not None:
                    # Prazo fixo
                    prazo = datetime.datetime.now() + datetime.timedelta(days=days)
                    return {
                        'prazo': prazo,
                        'dias_uteis': self._calculate_business_days(days)
                    }
                else:
                    # Extrair valor do grupo
                    if 'dias' in pattern:
                        dias = int(match.group(1))
                        prazo = datetime.datetime.now() + datetime.timedelta(days=dias)
                        return {
                            'prazo': prazo,
                            'dias_uteis': self._calculate_business_days(dias)
                        }
                    elif any(dia in match.group(0).lower() for dia in ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']):
                        prazo = self._calculate_next_weekday(match.group(0).lower())
                        if prazo:
                            dias = (prazo - datetime.datetime.now()).days
                            return {
                                'prazo': prazo,
                                'dias_uteis': self._calculate_business_days(dias)
                            }
        
        return None
    
    def _extract_deadline_from_responses(self, request_content: str, responses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Extrai informações de prazo das respostas do atendente.
        
        Args:
            request_content: Texto da solicitação
            responses: Lista de respostas do atendente
            
        Returns:
            dict: Informações do prazo detectado
        """
        for response in responses:
            content = response.get('conteudo', '')
            deadline_info = self._extract_deadline_from_message(content)
            if deadline_info:
                return deadline_info
        
        return None
    
    def _calculate_business_days(self, total_days: int) -> int:
        """
        Calcula o número de dias úteis em um período.
        
        Args:
            total_days: Número total de dias
            
        Returns:
            int: Número de dias úteis
        """
        if total_days <= 0:
            return 0
        
        current_date = datetime.datetime.now()
        end_date = current_date + datetime.timedelta(days=total_days)
        
        business_days = 0
        current = current_date
        
        while current <= end_date:
            # Segunda = 0, Domingo = 6
            if current.weekday() < 5:  # Segunda a Sexta
                business_days += 1
            current += datetime.timedelta(days=1)
        
        return business_days
    
    def _calculate_next_weekday(self, day_name: str) -> Optional[datetime.datetime]:
        """
        Calcula a data do próximo dia da semana especificado.
        
        Args:
            day_name: Nome do dia da semana
            
        Returns:
            datetime: Data calculada
        """
        weekdays = {
            'segunda': 0,
            'terça': 1,
            'terca': 1,
            'quarta': 2,
            'quinta': 3,
            'sexta': 4,
            'sábado': 5,
            'sabado': 5,
            'domingo': 6
        }
        
        target_day = None
        for name, day_number in weekdays.items():
            if name in day_name:
                target_day = day_number
                break
        
        if target_day is None:
            return None
        
        current = datetime.datetime.now()
        days_ahead = target_day - current.weekday()
        
        if days_ahead <= 0:  # Se for o mesmo dia ou já passou, vai para próxima semana
            days_ahead += 7
        
        return current + datetime.timedelta(days=days_ahead)
    
    def extract_names_from_conversation(self, messages: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai nomes do cliente e atendente da conversa.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            tuple: (nome_cliente, nome_atendente)
        """
        client_name = None
        attendant_name = None
        
        for message in messages:
            content = message.get('conteudo', '').strip()
            is_client = message.get('remetente') == 'cliente'
            
            # Verificar padrões de nome
            for pattern_type, pattern in self.name_patterns.items():
                match = re.search(pattern, content)
                if match:
                    name = match.group(1)
                    
                    if pattern_type == 'atendente' or (not is_client and pattern_type in ['saudacao', 'apresentacao']):
                        attendant_name = name
                    elif is_client:
                        client_name = name
            
            if client_name and attendant_name:
                break
        
        return client_name, attendant_name
    
    def is_conversation_closed(self, messages: List[Dict[str, Any]], inactivity_threshold_hours: int = 6) -> bool:
        """
        Verifica se uma conversa pode ser considerada encerrada.
        
        Args:
            messages: Lista de mensagens da conversa
            inactivity_threshold_hours: Horas de inatividade para considerar encerrada
            
        Returns:
            bool: True se a conversa pode ser considerada encerrada
        """
        if not messages:
            return False
        
        # Verificar tempo de inatividade
        last_message = messages[-1]
        last_timestamp = datetime.datetime.fromtimestamp(last_message.get('timestamp', 0) / 1000)
        
        time_diff = datetime.datetime.now() - last_timestamp
        if time_diff.total_seconds() / 3600 >= inactivity_threshold_hours:
            return True
        
        # Verificar padrões de encerramento nas últimas mensagens
        closing_patterns = [
            r'(?i)obrigad[oa]',
            r'(?i)at[ée]\s+(?:mais|logo|breve)',
            r'(?i)tenha\s+um\s+(?:bom|boa)',
            r'(?i)tchau',
            r'(?i)adeus',
            r'(?i)encerrar\s+(?:o\s+)?atendimento'
        ]
        
        # Verificar as últimas 3 mensagens
        recent_messages = messages[-3:]
        for message in recent_messages:
            content = message.get('conteudo', '').strip().lower()
            
            if any(re.search(pattern, content) for pattern in closing_patterns):
                # Verificar se houve resposta do outro participante
                if message.get('remetente') == 'cliente':
                    # Procurar resposta do atendente
                    for response in messages[messages.index(message)+1:]:
                        if response.get('remetente') == 'atendente':
                            return True
                else:
                    # Procurar resposta do cliente
                    for response in messages[messages.index(message)+1:]:
                        if response.get('remetente') == 'cliente':
                            return True
        
        return False 