import os
import json
import requests
import time
import re
import traceback
from typing import Dict, Any, Optional, List
from loguru import logger
from dotenv import load_dotenv
from .prompts_library import (
    get_default_message_analysis_prompt,
    get_default_request_detection_prompt,
    get_default_conversation_closure_prompt,
    get_default_complaint_detection_prompt,
    get_default_evaluation_prompt,
    get_default_summary_prompt
)

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral")
# Modo de simulação quando Ollama não está disponível
SIMULATION_MODE = os.getenv("OLLAMA_SIMULATION_MODE", "false").lower() == "true"

class OllamaIntegration:
    """
    Classe responsável pela integração com o Ollama para análise de mensagens.
    """
    
    def __init__(self):
        """
        Inicializa a integração com o Ollama.
        """
        self.base_url = OLLAMA_URL
        self.model = MODEL_NAME
        self.simulation_mode = SIMULATION_MODE
        
        # Configurações do modelo
        self.max_prompt_length = 4096
        self.temperature = 0.7
        self.top_p = 0.9
        self.top_k = 40
        self.repeat_penalty = 1.1
        self.context_window = 4096
        self.max_tokens = 2048
        self.timeout = 30
        
        # Verifica se Ollama está disponível
        if not self.simulation_mode:
            try:
                response = requests.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    logger.warning(f"Ollama não disponível em {self.base_url}, ativando modo de simulação")
                    self.simulation_mode = True
            except Exception as e:
                logger.warning(f"Erro ao conectar com Ollama: {e}, ativando modo de simulação")
                self.simulation_mode = True
        
        if self.simulation_mode:
            logger.info("Ollama em modo de simulação - as respostas serão simuladas")
        
    def generate(self, prompt: str, max_retries: int = 3) -> str:
        """
        Gera uma resposta utilizando o modelo Ollama.
        
        Args:
            prompt: Texto do prompt
            max_retries: Número máximo de tentativas em caso de falha
            
        Returns:
            Resposta gerada pelo modelo
        """
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Se o prompt for muito grande, trunca
                if len(prompt) > self.max_prompt_length:
                    trimmed_prompt = prompt[-self.max_prompt_length:]
                    logger.warning(f"Prompt truncado de {len(prompt)} para {len(trimmed_prompt)} caracteres")
                    prompt = trimmed_prompt
                
                # Faz a chamada ao modelo
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "top_p": self.top_p,
                            "top_k": self.top_k,
                            "repeat_penalty": self.repeat_penalty,
                            "num_ctx": self.context_window,
                            "num_predict": self.max_tokens
                        }
                    },
                    timeout=self.timeout
                )
                
                # Verifica resposta
                response.raise_for_status()
                
                # Processa resposta
                response_data = response.json()
                text_response = response_data.get("response", "")
                
                # Verifica se é resposta de avaliação e processa
                if "Nota de comunicação" in prompt or "Responda com:" in prompt and "Nota de comunicação (0-10)" in prompt:
                    # Tenta processar como uma resposta de avaliação
                    logger.debug("Processando resposta como avaliação")
                    lines = text_response.strip().split('\n')
                    processed_lines = []

                    # Garantir que temos notas numéricas
                    for i, line in enumerate(lines):
                        # Para os primeiros 8 itens que são notas
                        if i < 8 and ':' in line:
                            # Extrai a parte numérica
                            parts = line.split(':')
                            if len(parts) >= 2:
                                prefix = parts[0]
                                # Extrai o primeiro número da string, mesmo se estiver em um texto descritivo
                                value = parts[1].strip()
                                numeric_val = self._extract_number(value)
                                if numeric_val is not None:
                                    processed_lines.append(f"{prefix}: {numeric_val}")
                                else:
                                    # Se não consegir extrair um número, usa valor padrão
                                    processed_lines.append(f"{prefix}: 5")
                            else:
                                # Linha malformada, usa valor padrão
                                processed_lines.append(f"Item {i+1}: 5")
                        else:
                            # Passar outros itens como estão (listas, etc.)
                            processed_lines.append(line)
                    
                    text_response = '\n'.join(processed_lines)
                
                # Verifica tempo de processamento
                process_time = time.time() - start_time
                logger.debug(f"Resposta gerada em {process_time:.2f}s")
                
                logger.debug(f"Resposta do Ollama: {text_response[:100]}...")
                return text_response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro ao chamar API Ollama (tentativa {current_retry+1}/{max_retries}): {e}")
                current_retry += 1
                time.sleep(1)  # Aguarda 1 segundo antes de tentar novamente
                
            except Exception as e:
                logger.error(f"Erro inesperado na integração com Ollama: {e}")
                traceback.print_exc()
                break
                
        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Falha ao gerar resposta após {max_retries} tentativas")
        return "Erro na geração de resposta. Por favor, tente novamente mais tarde."
    
    def _extract_number(self, text: str) -> Optional[float]:
        """
        Extrai um número de um texto, mesmo que esteja em um formato como "7 (bom)"
        
        Args:
            text: Texto contendo um número
            
        Returns:
            Número extraído ou None se não for possível extrair
        """
        # Primeiro tenta extrair um número no início do texto
        match = re.search(r'^(\d+(\.\d+)?)', text)
        if match:
            return float(match.group(1))
            
        # Se não encontrar, tenta qualquer número no texto
        match = re.search(r'(\d+(\.\d+)?)', text)
        if match:
            return float(match.group(1))
            
        return None
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extrai dados JSON da resposta do modelo.
        
        Args:
            response: Texto da resposta do modelo
            
        Returns:
            Dicionário com os dados JSON extraídos ou dicionário vazio em caso de erro
        """
        if not response:
            return {}
            
        try:
            # Tenta extrair apenas o JSON da resposta
            json_str = response.strip()
            
            # Remove marcadores de código se existirem
            if json_str.startswith("```json"):
                json_end = json_str.rfind("```")
                if json_end > 7:  # Comprimento de "```json"
                    json_str = json_str[7:json_end].strip()
            elif json_str.startswith("```"):
                json_end = json_str.rfind("```")
                if json_end > 3:  # Comprimento de "```"
                    json_str = json_str[3:json_end].strip()
            
            # Tenta fazer parse do JSON
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da resposta: {e}")
            logger.debug(f"Resposta recebida: {response}")
            return {}
        except Exception as e:
            logger.error(f"Erro ao extrair JSON: {e}")
            return {}

    def analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analisa uma mensagem para identificar intenções e sentimentos.
        
        Args:
            message: Texto da mensagem a ser analisada
            
        Returns:
            Dicionário com os resultados da análise
        """
        try:
            # Usa o prompt da biblioteca de prompts
            prompt = get_default_message_analysis_prompt(message)
            response = self.generate(prompt)
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "intent": "unknown",
                    "sentiment": "neutral",
                    "urgency": "baixa",
                    "is_complaint": False,
                    "has_request": False,
                    "has_deadline": False,
                    "deadline_info": None,
                    "is_closing": False,
                    "topics": []
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Erro ao analisar mensagem: {e}")
            return {
                "intent": "error",
                "sentiment": "neutral",
                "urgency": "baixa",
                "is_complaint": False,
                "has_request": False,
                "has_deadline": False,
                "deadline_info": None,
                "is_closing": False,
                "topics": []
            }
    
    def detect_requests(self, conversation_context: str, message: str) -> Dict[str, Any]:
        """
        Detecta solicitações e prazos em uma mensagem.
        
        Args:
            conversation_context: Contexto recente da conversa
            message: Texto da mensagem atual
            
        Returns:
            Dicionário com informações sobre solicitações detectadas
        """
        try:
            prompt = get_default_request_detection_prompt(conversation_context, message)
            response = self.generate(prompt)
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "has_request": False,
                    "requests": [],
                    "priority": "baixa"
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Erro ao detectar solicitações: {e}")
            return {
                "has_request": False,
                "requests": [],
                "priority": "baixa"
            }
    
    def should_close_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verifica se uma conversa deve ser encerrada.
        
        Args:
            messages: Lista das últimas mensagens da conversa
            
        Returns:
            Dicionário com informações sobre se a conversa deve ser encerrada
        """
        try:
            prompt = get_default_conversation_closure_prompt(messages)
            response = self.generate(prompt)
            
            if not response:
                return {
                    "should_close": False,
                    "confidence": 0,
                    "reason": "sem_resposta"
                }
                
            # Processar o formato de texto em vez de JSON
            lines = response.strip().split('\n')
            if len(lines) >= 3:
                try:
                    should_close_line = next((line for line in lines if line.strip().startswith('SHOULD_CLOSE:')), '')
                    confidence_line = next((line for line in lines if line.strip().startswith('CONFIDENCE:')), '')
                    reason_line = next((line for line in lines if line.strip().startswith('REASON:')), '')
                    
                    should_close = 'sim' in should_close_line.split(':', 1)[1].strip().lower() if ':' in should_close_line else False
                    confidence = int(confidence_line.split(':', 1)[1].strip()) if ':' in confidence_line else 0
                    reason = reason_line.split(':', 1)[1].strip() if ':' in reason_line else 'não especificado'
                    
                    logger.info(f"Análise de encerramento processada: should_close={should_close}, confidence={confidence}")
                    
                    return {
                        "should_close": should_close,
                        "confidence": confidence,
                        "reason": reason
                    }
                except Exception as e:
                    logger.error(f"Erro ao processar resposta de formato texto: {e}")
            
            # Tenta extrair JSON como fallback
            result = self.extract_json_from_response(response)
            if result:
                return result
                
            logger.warning(f"Não foi possível processar a resposta como texto ou JSON: {response[:100]}...")
            return {
                "should_close": False,
                "confidence": 0,
                "reason": "erro_analise"
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar encerramento de conversa: {e}")
            return {
                "should_close": False,
                "confidence": 0,
                "reason": "erro_processamento"
            }
    
    def detect_complaints(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta reclamações em uma conversa.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            Dicionário com informações sobre reclamações detectadas
        """
        try:
            prompt = get_default_complaint_detection_prompt(messages)
            response = self.generate(prompt)
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "has_complaints": False,
                    "complaints": [],
                    "sentiment": "neutro",
                    "satisfaction_score": 5
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Erro ao detectar reclamações: {e}")
            return {
                "has_complaints": False,
                "complaints": [],
                "sentiment": "neutro",
                "satisfaction_score": 5
            }
    
    def evaluate_conversation(self, conversation_data: Dict[str, Any], 
                              messages: List[Dict[str, Any]], 
                              requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Avalia uma conversa completa.
        
        Args:
            conversation_data: Dados da conversa
            messages: Lista completa de mensagens da conversa
            requests: Lista de solicitações identificadas
            
        Returns:
            Dicionário com a avaliação completa da conversa
        """
        try:
            prompt = get_default_evaluation_prompt(conversation_data, messages, requests)
            response = self.generate(prompt)
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "comunicacao_nota": 0,
                    "conhecimento_nota": 0,
                    "empatia_nota": 0,
                    "profissionalismo_nota": 0,
                    "resultados_nota": 0,
                    "emocional_nota": 0,
                    "cumprimento_prazos_nota": 0,
                    "nota_geral": 0,
                    "reclamacoes_detectadas": ["Erro ao processar avaliação"],
                    "solicitacoes_nao_atendidas": [],
                    "solicitacoes_atrasadas": [],
                    "pontos_positivos": [],
                    "pontos_negativos": ["Falha no processamento da avaliação"],
                    "sugestoes_melhoria": ["Revisar manualmente"]
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa: {e}")
            return {
                "comunicacao_nota": 0,
                "conhecimento_nota": 0,
                "empatia_nota": 0,
                "profissionalismo_nota": 0,
                "resultados_nota": 0,
                "emocional_nota": 0,
                "cumprimento_prazos_nota": 0,
                "nota_geral": 0,
                "reclamacoes_detectadas": [f"Erro: {str(e)}"],
                "solicitacoes_nao_atendidas": [],
                "solicitacoes_atrasadas": [],
                "pontos_positivos": [],
                "pontos_negativos": ["Erro técnico na avaliação"],
                "sugestoes_melhoria": ["Verificar sistema de avaliação"]
            }
    
    def generate_summary(self, conversation_data: Dict[str, Any], 
                        messages: List[Dict[str, Any]], 
                        evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera um resumo do atendimento.
        
        Args:
            conversation_data: Dados da conversa
            messages: Lista de mensagens da conversa
            evaluation_data: Dados da avaliação
            
        Returns:
            Dicionário com o resumo do atendimento
        """
        try:
            prompt = get_default_summary_prompt(conversation_data, messages, evaluation_data)
            response = self.generate(prompt)
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "resumo": "Não foi possível gerar um resumo automaticamente.",
                    "problema_principal": "Indeterminado",
                    "solucao_aplicada": "Indeterminada",
                    "status_final": "indeterminado",
                    "proximos_passos": [],
                    "tags": ["erro_processamento"]
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return {
                "resumo": f"Erro ao gerar resumo: {str(e)}",
                "problema_principal": "Erro técnico",
                "solucao_aplicada": "Indeterminada",
                "status_final": "erro",
                "proximos_passos": ["Verificar sistema de resumo"],
                "tags": ["erro_tecnico", "revisao_manual"]
            }

# Funções auxiliares para uso fora da classe
def analyze_message(message: str) -> Dict[str, Any]:
    """
    Função de conveniência para analisar uma mensagem.
    
    Args:
        message: Texto da mensagem a ser analisada
        
    Returns:
        Dicionário com os resultados da análise
    """
    ollama = OllamaIntegration()
    return ollama.analyze_message(message)

def detect_requests(context: str, message: str) -> Dict[str, Any]:
    """
    Função de conveniência para detectar solicitações.
    
    Args:
        context: Contexto recente da conversa
        message: Texto da mensagem atual
        
    Returns:
        Dicionário com informações sobre solicitações detectadas
    """
    ollama = OllamaIntegration()
    return ollama.detect_requests(context, message)

def should_close_conversation(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Função de conveniência para verificar se uma conversa deve ser encerrada.
    
    Args:
        messages: Lista das últimas mensagens da conversa
        
    Returns:
        Dicionário com informações sobre se a conversa deve ser encerrada
    """
    ollama = OllamaIntegration()
    return ollama.should_close_conversation(messages)

def detect_complaints(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Função de conveniência para detectar reclamações.
    
    Args:
        messages: Lista de mensagens da conversa
        
    Returns:
        Dicionário com informações sobre reclamações detectadas
    """
    ollama = OllamaIntegration()
    return ollama.detect_complaints(messages) 