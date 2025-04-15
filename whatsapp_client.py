import os
import json
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

class WhatsAppClient:
    def __init__(self):
        port = os.getenv('WHATSAPP_SERVER_PORT', '3000')
        self.server_url = f"ws://localhost:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.message_callback = None
        self.connected = False
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self):
        """Estabelece conexão com o servidor WebSocket"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info("Conectado ao servidor WhatsApp")
            
            # Inicia a escuta de mensagens
            asyncio.create_task(self._listen_messages())
        except Exception as e:
            logger.error(f"Erro ao conectar ao servidor: {e}")
            self.connected = False

    async def disconnect(self):
        """Fecha a conexão com o servidor"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Desconectado do servidor WhatsApp")

    async def send_message(self, to: str, message: str) -> bool:
        """
        Envia uma mensagem para um número específico
        
        Args:
            to: Número do destinatário
            message: Conteúdo da mensagem
            
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

    async def _listen_messages(self):
        """Escuta mensagens recebidas do servidor"""
        while self.connected:
            try:
                message = await self.websocket.recv()
                logger.debug(f"Mensagem recebida do servidor: {message}")
                
                try:
                    data = json.loads(message)
                    self._process_message(data)
                    if self.message_callback:
                        await self.message_callback(data)
                except json.JSONDecodeError:
                    logger.warning(f"Mensagem não é um JSON válido: {message}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.error("Conexão com o servidor foi fechada")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")

    def set_message_callback(self, callback):
        """Define a função de callback para processar mensagens recebidas"""
        self.message_callback = callback

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

async def main():
    # Exemplo de uso
    client = WhatsAppClient()
    
    async def handle_message(message: Dict[str, Any]):
        """Callback para processar mensagens recebidas"""
        logger.info(f"Mensagem recebida: {message}")
    
    client.set_message_callback(handle_message)
    
    await client.connect()
    
    if client.connected:
        try:
            # Mantém o cliente rodando
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await client.disconnect()
    else:
        logger.error("Não foi possível conectar ao servidor")

if __name__ == "__main__":
    asyncio.run(main()) 