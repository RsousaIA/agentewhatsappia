import os
import json
import requests
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
        
    def generate(self, prompt: str) -> Optional[str]:
        """
        Gera uma resposta usando o modelo Ollama.
        
        Args:
            prompt: Texto do prompt para o modelo
            
        Returns:
            Optional[str]: Resposta gerada ou None em caso de erro
        """
        # Se estiver em modo de simulação, retorna uma resposta simulada
        if self.simulation_mode:
            return self._simulate_response(prompt)
            
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json().get('response')
            else:
                logger.error(f"Erro na chamada do Ollama: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao gerar resposta do Ollama: {e}")
            return None
    
    def _simulate_response(self, prompt: str) -> str:
        """
        Simula uma resposta para o prompt quando Ollama não está disponível.
        
        Args:
            prompt: Texto do prompt
            
        Returns:
            Resposta simulada
        """
        # Identificar o tipo de prompt e gerar uma resposta apropriada
        if "intent: intenção principal" in prompt:
            # Prompt de análise de mensagem
            return """
            {
              "intent": "solicitação",
              "sentiment": "negativo",
              "urgency": "média",
              "is_complaint": true,
              "has_request": true,
              "has_deadline": true,
              "deadline_info": "5 dias úteis já passados",
              "is_closing": false,
              "topics": ["pedido", "entrega", "atraso"]
            }
            """
        elif "has_request: true/false se contém uma solicitação" in prompt:
            # Prompt de detecção de solicitações
            return """
            {
              "has_request": true,
              "requests": [
                {
                  "description": "Verificar status do pedido #12345",
                  "has_deadline": true,
                  "deadline_type": "implícito",
                  "deadline_value": 1,
                  "deadline_unit": "dias",
                  "business_days": true
                }
              ],
              "priority": "alta"
            }
            """
        elif "should_close: true/false se a conversa deve ser encerrada" in prompt:
            # Prompt de encerramento de conversa
            if "Não, obrigado por toda ajuda!" in prompt and "Foi um prazer ajudar" in prompt:
                return """
                {
                  "should_close": true,
                  "confidence": 95,
                  "reason": "despedida"
                }
                """
            else:
                return """
                {
                  "should_close": false,
                  "confidence": 30,
                  "reason": "conversa ainda ativa"
                }
                """
        elif "has_complaints: true/false" in prompt:
            # Prompt de detecção de reclamações
            return """
            {
              "has_complaints": true,
              "complaints": [
                {
                  "text": "Ainda não recebi e já se passaram 5 dias úteis",
                  "severity": "média",
                  "topic": "atraso na entrega"
                }
              ],
              "sentiment": "negativo",
              "satisfaction_score": 3
            }
            """
        elif "comunicacao_nota: nota para comunicação" in prompt:
            # Prompt de avaliação
            return """
            {
              "comunicacao_nota": 7.5,
              "conhecimento_nota": 8.0,
              "empatia_nota": 6.5,
              "profissionalismo_nota": 8.5,
              "resultados_nota": 7.0,
              "emocional_nota": 7.5,
              "cumprimento_prazos_nota": 5.0,
              "nota_geral": 7.2,
              "reclamacoes_detectadas": ["Atraso na entrega do pedido"],
              "solicitacoes_nao_atendidas": [],
              "solicitacoes_atrasadas": ["Entrega do pedido #12345"],
              "pontos_positivos": ["Comunicação clara", "Boa educação"],
              "pontos_negativos": ["Demora no atendimento"],
              "sugestoes_melhoria": ["Agilizar processos de entrega"]
            }
            """
        else:
            # Resposta genérica para outros tipos de prompt
            return '{"result": "Resposta simulada para o prompt fornecido"}'
    
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
            
            result = self.extract_json_from_response(response)
            
            # Se não conseguiu extrair JSON, retorna valores padrão
            if not result:
                return {
                    "should_close": False,
                    "confidence": 0,
                    "reason": "erro_analise"
                }
                
            return result
            
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