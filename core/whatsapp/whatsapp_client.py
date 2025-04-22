"""
Cliente para conexão com o servidor WhatsApp.
Gerencia a conexão WebSocket com o servidor de WhatsApp.
"""

import os
import json
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable, Protocol
from loguru import logger
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class MessageCallback(Protocol):
    """Protocolo para callbacks de mensagens"""
    def __call__(self, message_data: Dict[str, Any]) -> None: ...

class ConnectionCallback(Protocol):
    """Protocolo para callbacks de status de conexão"""
    def __call__(self, status: str) -> None: ...

class WhatsAppClient:
    """
    Cliente para conexão com o servidor de WhatsApp.
    """
    def __init__(self):
        """
        Inicializa o cliente WhatsApp.
        """
        port = os.getenv('WHATSAPP_SERVER_PORT', '5000')
        self.server_url = f"ws://localhost:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.message_callback: Optional[MessageCallback] = None
        self.connection_callback: Optional[ConnectionCallback] = None
        self.connected = False
        self.my_number = None
        self._event_loop = None
        self._stop_requested = False

    def start(self):
        """
        Inicia a conexão com o servidor WebSocket.
        """
        try:
            # Verificar se já existe um loop rodando
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            self._event_loop = loop
            self._stop_requested = False
            loop.run_until_complete(self.connect())
            logger.info("Cliente WhatsApp iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar cliente WhatsApp: {e}")
            raise

    def stop(self):
        """
        Encerra a conexão com o servidor WebSocket.
        """
        try:
            self._stop_requested = True
            if self._event_loop:
                self._event_loop.run_until_complete(self.disconnect())
                logger.info("Cliente WhatsApp encerrado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao encerrar cliente WhatsApp: {e}")
            raise

    async def connect(self):
        """
        Estabelece conexão com o servidor WebSocket.
        """
        try:
            # Cria uma nova conexão com o servidor
            logger.info(f"Tentando conectar ao servidor WebSocket: {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info("Conectado ao servidor WhatsApp")
            
            # Inicia a escuta de mensagens em uma nova task
            asyncio.create_task(self._listen_messages())
            
            # Notifica mudança de status
            if self.connection_callback:
                self.connection_callback('connected')
        except Exception as e:
            logger.error(f"Erro ao conectar ao servidor: {e}")
            self.connected = False
            if self.connection_callback:
                self.connection_callback('disconnected')
            raise

    async def disconnect(self):
        """
        Fecha a conexão com o servidor.
        """
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Desconectado do servidor WhatsApp")
            if self.connection_callback:
                self.connection_callback('disconnected')

    async def send_message(self, to: str, message: str, media_path: Optional[str] = None) -> bool:
        """
        Envia uma mensagem para um número específico.
        
        Args:
            to: Número do destinatário
            message: Conteúdo da mensagem
            media_path: Caminho opcional para arquivo de mídia
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        if not self.connected:
            logger.error("Cliente não está conectado ao servidor")
            return False

        try:
            data = {
                "to": to,
                "message": message
            }
            
            # Se houver mídia, adicionar caminho
            if media_path:
                data["mediaPath"] = media_path
            
            await self.websocket.send(json.dumps(data))
            logger.info(f"Mensagem enviada para {to}: {message}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    async def _listen_messages(self):
        """
        Escuta mensagens do servidor WebSocket.
        """
        try:
            while self.connected and self.websocket and not self._stop_requested:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    if self.message_callback:
                        self.message_callback(data)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Conexão WebSocket fechada")
                    self.connected = False
                    break
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {e}")
                    continue
        except Exception as e:
            logger.error(f"Erro no loop de escuta: {e}")
        finally:
            if self.connection_callback and not self._stop_requested:
                self.connection_callback('disconnected')

    def set_message_callback(self, callback: MessageCallback):
        """
        Define a função de callback para processar mensagens recebidas.
        
        Args:
            callback: Função de callback que recebe os dados da mensagem
        """
        self.message_callback = callback
        
    def set_connection_callback(self, callback: ConnectionCallback):
        """
        Define a função de callback para mudanças no status da conexão.
        
        Args:
            callback: Função de callback que recebe o status da conexão
        """
        self.connection_callback = callback

    def mark_messages_as_read(self, message_ids: List[str]) -> bool:
        """
        Marca mensagens como lidas.
        
        Args:
            message_ids: Lista de IDs de mensagens a serem marcadas como lidas
            
        Returns:
            bool: True se as mensagens foram marcadas como lidas com sucesso
        """
        if not self.connected:
            logger.error("Cliente não está conectado ao servidor")
            return False

        try:
            if self._event_loop:
                data = {
                    "action": "markAsRead",
                    "messageIds": message_ids
                }
                
                future = asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(data)), 
                    self._event_loop
                )
                future.result(timeout=5)  # Espera até 5 segundos
                
                logger.info(f"Mensagens marcadas como lidas: {message_ids}")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao marcar mensagens como lidas: {e}")
            return False 