import os
import json
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from loguru import logger

# Carrega variáveis de ambiente
load_dotenv()

# Configurações da API do WhatsApp
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v16.0")

class WhatsAppClient:
    """
    Cliente para a API oficial do WhatsApp Business.
    """
    
    def __init__(self):
        """
        Inicializa o cliente da API do WhatsApp.
        """
        # Verifica configurações da API
        if not WHATSAPP_API_TOKEN:
            raise ValueError("Token da API do WhatsApp não configurado")
            
        if not WHATSAPP_PHONE_NUMBER_ID:
            raise ValueError("ID do número de telefone do WhatsApp não configurado")
            
        self.api_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = WHATSAPP_BUSINESS_ACCOUNT_ID
        
        # Configuração de headers
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Cliente da API do WhatsApp inicializado: Número {self.phone_number_id}")
        
    def get_new_messages(self, since: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém novas mensagens do WhatsApp.
        
        Args:
            since (datetime, optional): Timestamp da última mensagem processada
            limit (int): Número máximo de mensagens a recuperar
            
        Returns:
            list: Lista de mensagens obtidas da API
        """
        try:
            # Endpoint para obter mensagens
            endpoint = f"{self.api_url}/{self.phone_number_id}/messages"
            
            # Parâmetros da solicitação
            params = {
                "limit": limit,
                "fields": "from,to,id,timestamp,text,type,status"
            }
            
            # Adiciona filtro por data, se fornecido
            if since:
                # Formato ISO para a API
                after_timestamp = since.isoformat()
                params["after"] = after_timestamp
                
            # Faz a solicitação à API
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                messages = data.get("data", [])
                logger.info(f"Obtidas {len(messages)} mensagens da API do WhatsApp")
                return messages
            else:
                logger.error(f"Erro ao obter mensagens: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao obter mensagens da API do WhatsApp: {str(e)}")
            return []
            
    def mark_messages_as_read(self, message_ids: List[str]) -> bool:
        """
        Marca mensagens como lidas na API do WhatsApp.
        
        Args:
            message_ids (list): Lista de IDs de mensagens a marcar como lidas
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        if not message_ids:
            return True
            
        success_count = 0
        
        for msg_id in message_ids:
            try:
                # Endpoint para marcar mensagem como lida
                endpoint = f"{self.api_url}/{self.phone_number_id}/messages"
                
                # Dados da solicitação
                data = {
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": msg_id
                }
                
                # Faz a solicitação à API
                response = requests.post(endpoint, headers=self.headers, json=data)
                
                # Verifica se a resposta foi bem-sucedida
                if response.status_code == 200:
                    success_count += 1
                else:
                    logger.error(f"Erro ao marcar mensagem {msg_id} como lida: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Erro ao marcar mensagem {msg_id} como lida: {str(e)}")
                
        logger.info(f"Marcadas {success_count}/{len(message_ids)} mensagens como lidas")
        return success_count == len(message_ids)
        
    def send_message(self, to: str, message: str) -> Optional[str]:
        """
        Envia uma mensagem de texto pelo WhatsApp.
        
        Args:
            to (str): Número de telefone de destino no formato internacional (ex: 5511999999999)
            message (str): Conteúdo da mensagem
            
        Returns:
            str: ID da mensagem enviada ou None em caso de erro
        """
        try:
            # Endpoint para enviar mensagem
            endpoint = f"{self.api_url}/{self.phone_number_id}/messages"
            
            # Dados da solicitação
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            }
            
            # Faz a solicitação à API
            response = requests.post(endpoint, headers=self.headers, json=data)
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"Mensagem enviada com sucesso para {to}, ID: {message_id}")
                return message_id
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem via API do WhatsApp: {str(e)}")
            return None
            
    def get_conversation_history(self, phone_number: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de conversas com um número específico.
        
        Args:
            phone_number (str): Número de telefone no formato internacional
            limit (int): Número máximo de mensagens a recuperar
            
        Returns:
            list: Lista de mensagens da conversa
        """
        try:
            # Endpoint para obter mensagens
            endpoint = f"{self.api_url}/{self.phone_number_id}/messages"
            
            # Parâmetros da solicitação
            params = {
                "limit": limit,
                "phone_number": phone_number,
                "fields": "from,to,id,timestamp,text,type,status"
            }
            
            # Faz a solicitação à API
            response = requests.get(endpoint, headers=self.headers, params=params)
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                messages = data.get("data", [])
                logger.info(f"Obtidas {len(messages)} mensagens do histórico com {phone_number}")
                return messages
            else:
                logger.error(f"Erro ao obter histórico: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao obter histórico de conversa: {str(e)}")
            return []
            
    def get_message_templates(self) -> List[Dict[str, Any]]:
        """
        Obtém os modelos de mensagem disponíveis na conta.
        
        Returns:
            list: Lista de modelos de mensagem
        """
        try:
            if not self.business_account_id:
                logger.error("ID da conta de negócios não configurado")
                return []
                
            # Endpoint para obter modelos
            endpoint = f"{self.api_url}/{self.business_account_id}/message_templates"
            
            # Faz a solicitação à API
            response = requests.get(endpoint, headers=self.headers)
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                templates = data.get("data", [])
                logger.info(f"Obtidos {len(templates)} modelos de mensagem")
                return templates
            else:
                logger.error(f"Erro ao obter modelos: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao obter modelos de mensagem: {str(e)}")
            return []
            
    def send_template_message(self, to: str, template_name: str, components: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """
        Envia uma mensagem utilizando um modelo (template).
        
        Args:
            to (str): Número de telefone de destino no formato internacional
            template_name (str): Nome do modelo a ser utilizado
            components (list, optional): Componentes da mensagem (cabeçalho, corpo, botões, etc.)
            
        Returns:
            str: ID da mensagem enviada ou None em caso de erro
        """
        try:
            # Endpoint para enviar mensagem
            endpoint = f"{self.api_url}/{self.phone_number_id}/messages"
            
            # Dados da solicitação
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "pt_BR"
                    }
                }
            }
            
            # Adiciona componentes do template, se fornecidos
            if components:
                data["template"]["components"] = components
                
            # Faz a solicitação à API
            response = requests.post(endpoint, headers=self.headers, json=data)
            
            # Verifica se a resposta foi bem-sucedida
            if response.status_code == 200:
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"Mensagem de modelo enviada com sucesso para {to}, ID: {message_id}")
                return message_id
            else:
                logger.error(f"Erro ao enviar mensagem de modelo: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem de modelo via API do WhatsApp: {str(e)}")
            return None 