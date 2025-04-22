import os
import json
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable
from loguru import logger
from dotenv import load_dotenv
from database.firebase_db import save_message, upload_media

# Carrega variáveis de ambiente
load_dotenv()

class WhatsAppClient:
    def __init__(self):
        port = os.getenv('WHATSAPP_SERVER_PORT', '5000')  # Atualizando para porta 5000
        self.server_url = f"ws://localhost:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.message_callback = None
        self.connection_callback = None
        self.connected = False
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.my_number = None
        self._event_loop = None

    def start(self):
        """
        Inicia a conexão com o servidor WebSocket
        """
        try:
            # Verificar se já existe um loop rodando
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            self._event_loop = loop
            loop.run_until_complete(self.connect())
            logger.info("Cliente WhatsApp iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar cliente WhatsApp: {e}")
            raise

    def stop(self):
        """
        Encerra a conexão com o servidor WebSocket
        """
        try:
            if self._event_loop:
                self._event_loop.run_until_complete(self.disconnect())
                logger.info("Cliente WhatsApp encerrado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao encerrar cliente WhatsApp: {e}")
            raise

    async def connect(self):
        """Estabelece conexão com o servidor WebSocket"""
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
                if asyncio.iscoroutinefunction(self.connection_callback):
                    # Se for uma coroutine, cria uma task para executá-la
                    asyncio.create_task(self.connection_callback('connected'))
                else:
                    # Se for uma função normal, chama diretamente
                    self.connection_callback('connected')
        except Exception as e:
            logger.error(f"Erro ao conectar ao servidor: {e}")
            self.connected = False
            if self.connection_callback:
                if asyncio.iscoroutinefunction(self.connection_callback):
                    # Se for uma coroutine, cria uma task para executá-la
                    asyncio.create_task(self.connection_callback('disconnected'))
                else:
                    # Se for uma função normal, chama diretamente
                    self.connection_callback('disconnected')
            raise

    async def disconnect(self):
        """Fecha a conexão com o servidor"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Desconectado do servidor WhatsApp")
            if self.connection_callback:
                if asyncio.iscoroutinefunction(self.connection_callback):
                    await self.connection_callback('disconnected')
                else:
                    self.connection_callback('disconnected')

    async def send_message(self, to: str, message: str, media_path: Optional[str] = None) -> bool:
        """
        Envia uma mensagem para um número específico
        
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
            
            # Se houver mídia, fazer upload e adicionar URL
            if media_path:
                try:
                    # Determinar content type baseado na extensão
                    content_type = self._get_content_type(media_path)
                    # Fazer upload da mídia
                    media_url = await upload_media(media_path, content_type, to)
                    data["mediaUrl"] = media_url
                    data["mediaType"] = content_type
                    logger.info(f"Mídia enviada para Firebase: {media_url}")
                except Exception as e:
                    logger.error(f"Erro ao fazer upload de mídia: {e}")
                    return False
            
            await self.websocket.send(json.dumps(data))
            logger.info(f"Mensagem enviada para {to}: {message}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Processa uma mensagem recebida e a adiciona à conversa correspondente
        
        Args:
            message: Dados da mensagem recebida
        """
        try:
            # Salvar mensagem no Firebase
            save_message(message)
            
            # Obtém o ID da conversa
            conversation_id = message.get('conversation_id')
            if not conversation_id:
                logger.warning("Mensagem sem ID de conversa")
                return

            # Inicializa a conversa se não existir
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []

            # Adiciona a mensagem à conversa
            self.conversations[conversation_id].append(message)

            # Ordena as mensagens por timestamp
            self.conversations[conversation_id].sort(key=lambda x: x['timestamp'])

            # Log da mensagem processada
            direction = "Recebida" if message.get('direction') == 'received' else "Enviada"
            message_type = message.get('type', 'text')
            
            if message_type == 'audio':
                logger.info(f"{direction} - Áudio: {message.get('text', '[Áudio]')}")
            elif message_type == 'media':
                logger.info(f"{direction} - Mídia: {message.get('mimetype', 'Tipo desconhecido')}")
            else:
                logger.info(f"{direction} - Texto: {message.get('body', '')}")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def _listen_messages(self):
        """Escuta mensagens do servidor WebSocket"""
        try:
            while self.connected and self.websocket:
                try:
                    message = await self.websocket.recv()
                    data = json.loads(message)
                    
                    if self.message_callback:
                        # Verificar se o callback é uma coroutine
                        if asyncio.iscoroutinefunction(self.message_callback):
                            await self.message_callback(data)
                        else:
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
            if self.connection_callback:
                if asyncio.iscoroutinefunction(self.connection_callback):
                    await self.connection_callback('disconnected')
                else:
                    self.connection_callback('disconnected')

    def set_message_callback(self, callback):
        """Define a função de callback para processar mensagens recebidas"""
        self.message_callback = callback
        
    def set_connection_callback(self, callback):
        """Define a função de callback para mudanças no status da conexão"""
        self.connection_callback = callback

    def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Retorna todas as mensagens de uma conversa específica
        
        Args:
            conversation_id: ID da conversa
            
        Returns:
            List[Dict[str, Any]]: Lista de mensagens da conversa
        """
        return self.conversations.get(conversation_id, [])

    def get_all_conversations(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retorna todas as conversas
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dicionário com todas as conversas
        """
        return self.conversations
        
    def get_my_number(self) -> Optional[str]:
        """
        Retorna o número do WhatsApp do cliente
        
        Returns:
            str: Número do WhatsApp ou None se não disponível
        """
        return self.my_number
        
    def mark_messages_as_read(self, message_ids: List[str]) -> bool:
        """
        Marca mensagens como lidas
        
        Args:
            message_ids: Lista de IDs das mensagens
            
        Returns:
            bool: True se todas as mensagens foram marcadas como lidas
        """
        try:
            data = {
                "action": "mark_as_read",
                "message_ids": message_ids
            }
            asyncio.create_task(self.websocket.send(json.dumps(data)))
            logger.debug(f"Mensagens marcadas como lidas: {message_ids}")
            return True
        except Exception as e:
            logger.error(f"Erro ao marcar mensagens como lidas: {e}")
            return False
            
    def _get_content_type(self, file_path: str) -> str:
        """
        Determina o content type baseado na extensão do arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            str: Content type do arquivo
        """
        extension = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.webm': 'video/webm'
        }
        return content_types.get(extension, 'application/octet-stream') 