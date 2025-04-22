import os
import json
import requests
from datetime import datetime
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from loguru import logger

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do servidor Node.js
NODE_SERVER_URL = os.getenv("NODE_SERVER_URL", "http://localhost:3000")

class WhatsAppNodeClient:
    """
    Cliente Python para comunicação com o servidor Node.js do WhatsApp.
    """
    
    def __init__(self):
        """
        Inicializa o cliente do WhatsApp.
        """
        self.base_url = NODE_SERVER_URL
        logger.info(f"Cliente WhatsApp Node.js inicializado: {self.base_url}")
        self._message_callback = None
        self._qr_callback = None
        self._status_check_interval = 5  # 5 segundos
        self._connected = False
        self._running = False
        self._check_thread = None
    
    def get_new_messages(self, since: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém novas mensagens do WhatsApp.
        
        Args:
            since (datetime, optional): Timestamp da última mensagem processada
            limit (int): Número máximo de mensagens a recuperar
            
        Returns:
            list: Lista de mensagens obtidas
        """
        # Esta funcionalidade será gerenciada pelos callbacks do Node.js
        # As mensagens serão recebidas em tempo real
        return []
    
    def mark_messages_as_read(self, message_ids: List[str]) -> bool:
        """
        Marca mensagens como lidas.
        
        Args:
            message_ids (list): Lista de IDs de mensagens a marcar como lidas
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        try:
            response = requests.post(
                f"{self.base_url}/mark-as-read",
                json={"messageIds": message_ids}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
            else:
                logger.error(f"Erro ao marcar mensagens como lidas: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao marcar mensagens como lidas: {str(e)}")
            return False
    
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
            response = requests.post(
                f"{self.base_url}/send-message",
                json={
                    "to": to,
                    "message": message
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("messageId")
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
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
            response = requests.get(
                f"{self.base_url}/chat-history/{phone_number}",
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("messages", [])
            else:
                logger.error(f"Erro ao obter histórico: {response.status_code} - {response.text}")
            
            return []
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {str(e)}")
            return []
    
    def set_message_callback(self, callback):
        """
        Define o callback para receber mensagens em tempo real.
        Esta função será chamada pelo Node.js quando uma nova mensagem for recebida.
        
        Args:
            callback: Função que será chamada com os dados da mensagem
        """
        self._message_callback = callback
        
        # Registra o callback no servidor Node.js
        try:
            response = requests.post(
                f"{self.base_url}/register-message-callback"
            )
            
            if response.status_code == 200:
                logger.info("Callback de mensagens registrado no servidor Node.js")
            else:
                logger.error(f"Erro ao registrar callback: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Erro ao registrar callback: {str(e)}")
    
    def set_qr_callback(self, callback):
        """
        Define o callback para receber o código QR quando necessário.
        Esta função será chamada pelo Node.js quando um novo código QR for gerado.
        
        Args:
            callback: Função que será chamada com o código QR
        """
        self._qr_callback = callback
        
    def start(self, message_callback=None, qr_callback=None):
        """
        Inicia o cliente do WhatsApp.
        
        Args:
            message_callback: Função para processar mensagens recebidas
            qr_callback: Função para processar o código QR
        """
        logger.info("Iniciando cliente WhatsApp Node.js")
        
        # Registrar callbacks se fornecidos
        if message_callback:
            self.set_message_callback(message_callback)
        
        if qr_callback:
            self.set_qr_callback(qr_callback)
            
        # Verificar status do servidor Node.js e se conectar
        self._running = True
        self._check_connection()
    
    def stop(self):
        """
        Para o cliente do WhatsApp.
        """
        logger.info("Parando cliente WhatsApp Node.js")
        self._running = False
    
    def _check_connection(self):
        """
        Verifica a conexão com o servidor Node.js.
        """
        while self._running:
            try:
                # Verificar status
                response = requests.get(f"{self.base_url}/status")
                
                if response.status_code == 200:
                    data = response.json()
                    is_connected = data.get("status") == "connected"
                    
                    # Atualizar status da conexão
                    if is_connected and not self._connected:
                        logger.info("Conectado ao servidor WhatsApp Node.js")
                        self._connected = True
                    elif not is_connected and self._connected:
                        logger.warning("Desconectado do servidor WhatsApp Node.js")
                        self._connected = False
                else:
                    logger.error(f"Erro ao verificar status: {response.status_code}")
                    self._connected = False
            except Exception as e:
                logger.error(f"Erro ao verificar conexão: {e}")
                self._connected = False
            
            # Aguardar próxima verificação
            time.sleep(self._status_check_interval) 