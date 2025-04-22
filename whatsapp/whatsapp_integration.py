import os
import json
import time
import logging
import asyncio
import threading
from typing import Dict, Any, Optional, Callable
from loguru import logger
from .whatsapp_client import WhatsAppClient
from agent.collector_agent import get_collector_agent
from database.firebase_db import (
    init_firebase,
    get_firestore_db,
    save_message,
    get_conversation,
    get_messages_by_conversation,
    upload_media,
    create_conversation,
    update_conversation
)
from datetime import datetime

class WhatsAppIntegration:
    """
    Classe responsável por gerenciar a integração entre o Collector Agent e o WhatsApp Web.
    """
    
    def __init__(self):
        """
        Inicializa a integração com o WhatsApp.
        """
        logger.info("Inicializando integração com WhatsApp...")
        
        # Inicializar Firebase
        try:
            init_firebase()
            self.db = get_firestore_db()
            logger.info("Firebase inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar Firebase: {e}")
            raise
        
        # Inicializar cliente WhatsApp
        self.client = WhatsAppClient()
        
        # Obter instância do Collector Agent
        self.collector_agent = get_collector_agent()
        
        # Configurar callback para mensagens
        self.client.set_message_callback(self._handle_message)
        
        # Configurar callback para status de conexão
        self.client.set_connection_callback(self._handle_connection_status)
        
        # Eventos para controle de execução
        self._stop_event = threading.Event()
        self._whatsapp_thread = None
        
        logger.info("Integração com WhatsApp inicializada com sucesso")
    
    def start(self):
        """
        Inicia a integração com o WhatsApp.
        """
        try:
            # Iniciar Collector Agent
            self.collector_agent.start()
            logger.info("Collector Agent iniciado")
            
            # Iniciar cliente WhatsApp em uma nova thread
            self._whatsapp_thread = threading.Thread(target=self._run_whatsapp_client, daemon=True)
            self._whatsapp_thread.start()
            
        except Exception as e:
            logger.error(f"Erro ao iniciar integração: {e}")
            raise
    
    def _run_whatsapp_client(self):
        """
        Executa o cliente WhatsApp em um loop separado.
        Esta função é executada em uma thread separada.
        """
        try:
            # Criar um novo loop de eventos para esta thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Iniciar cliente WhatsApp
            self.client.start()
            logger.info("Cliente WhatsApp iniciado em thread separada")
            
            # Manter o loop rodando até que o evento de parada seja definido
            while not self._stop_event.is_set():
                loop.run_until_complete(asyncio.sleep(0.1))
                
            # Limpar recursos
            loop.close()
            
        except Exception as e:
            logger.error(f"Erro na thread do WhatsApp: {e}")
    
    def stop(self):
        """
        Para a integração com o WhatsApp.
        """
        try:
            # Parar Collector Agent
            self.collector_agent.stop()
            logger.info("Collector Agent parado")
            
            # Sinalizar para a thread do WhatsApp parar
            self._stop_event.set()
            
            if self._whatsapp_thread and self._whatsapp_thread.is_alive():
                self._whatsapp_thread.join(timeout=5)
                logger.info("Thread do WhatsApp finalizada")
            
            # Parar cliente WhatsApp
            self.client.stop()
            logger.info("Cliente WhatsApp parado")
            
        except Exception as e:
            logger.error(f"Erro ao parar integração: {e}")
            raise
    
    def _handle_message(self, message_data: Dict[str, Any]):
        """
        Callback para processar mensagens recebidas do WhatsApp.
        
        Args:
            message_data: Dados da mensagem recebida
        """
        try:
            # Validação mais robusta da mensagem
            if not message_data:
                logger.warning("Mensagem recebida está vazia")
                return
                
            # Garantir que temos os campos obrigatórios
            if not message_data.get('from'):
                # Se não tiver remetente, tentar extrair do ID
                if message_data.get('id'):
                    parts = message_data['id'].split('_')
                    if len(parts) > 1:
                        message_data['from'] = f"{parts[1]}@c.us"
                    else:
                        message_data['from'] = 'unknown@c.us'
                else:
                    message_data['from'] = 'unknown@c.us'
                logger.debug(f"Remetente não encontrado, usando: {message_data['from']}")

            if not message_data.get('body'):
                # Se não tiver corpo, usar valor padrão
                message_data['body'] = '(Mensagem sem conteúdo)'
                logger.debug("Corpo da mensagem não encontrado, usando valor padrão")

            if not message_data.get('id'):
                # Se não tiver ID, gerar um baseado no timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                message_data['id'] = f"gerado_{message_data['from'].split('@')[0]}_{timestamp}"
                logger.debug(f"ID não encontrado, gerando novo: {message_data['id']}")
                
            logger.info(f"Mensagem recebida: {message_data.get('id')}")
            
            # Gerar ID da conversa baseado no número do remetente
            conversation_id = message_data['from'].replace('@c.us', '')
            
            # Verificar se a conversa existe, se não, criar
            conversation = get_conversation(conversation_id)
            if not conversation:
                # Criar nova conversa
                conversation_data = {
                    'cliente': {
                        'nome': message_data.get('contact_name', ''),
                        'telefone': conversation_id
                    },
                    'status': 'novo',
                    'dataHoraInicio': datetime.now(),
                    'dataHoraEncerramento': None,
                    'foiReaberta': False,
                    'agentesEnvolvidos': [],
                    'tempoTotal': 0,
                    'tempoRespostaMedio': 0,
                    'ultimaMensagem': datetime.now()
                }
                create_conversation(conversation_id, conversation_data)
                logger.info(f"Nova conversa criada: {conversation_id}")
            
            # Preparar dados da mensagem
            message_to_save = {
                'tipo': message_data.get('type', 'texto'),
                'conteudo': message_data.get('body', ''),
                'remetente': 'cliente' if not message_data.get('fromMe') else 'sistema',
                'timestamp': datetime.now()
            }
            
            # Se tiver mídia, processar
            if message_data.get('hasMedia'):
                media_url = message_data.get('mediaUrl')
                if media_url:
                    message_to_save['conteudo'] = media_url
            
            # Salvar mensagem no Firebase
            try:
                save_message(conversation_id, message_to_save)
                logger.info(f"Mensagem salva no Firebase para conversa {conversation_id}")
                
                # Atualizar última mensagem da conversa
                update_conversation(conversation_id, {
                    'ultimaMensagem': datetime.now()
                })
            except Exception as e:
                logger.error(f"Erro ao salvar mensagem no Firebase: {e}")
            
            # Processar mensagem no Collector Agent
            self.collector_agent._handle_whatsapp_message(message_data)
            
            # Marcar mensagem como lida se for do cliente
            if not message_data.get('fromMe', False):
                self.client.mark_messages_as_read([message_data.get('id')])
                logger.debug(f"Mensagem {message_data.get('id')} marcada como lida")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
    
    async def _handle_connection_status(self, status: str):
        """
        Callback para processar mudanças no status de conexão.
        
        Args:
            status: Novo status da conexão
        """
        try:
            logger.info(f"Status da conexão alterado: {status}")
            
            if status == 'disconnected':
                # Tentar reconectar após um delay
                await asyncio.sleep(5)
                
                # Criar um loop para executar o connect
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.client.connect())
                else:
                    # Se não tiver um loop rodando, criar um novo
                    await self.client.connect()
                
                logger.info("Tentando reconectar ao WhatsApp...")
            
        except Exception as e:
            logger.error(f"Erro ao processar status de conexão: {e}")
    
    def send_message(self, to: str, content: str, media_path: Optional[str] = None) -> bool:
        """
        Envia uma mensagem através do WhatsApp.
        
        Args:
            to: Número do destinatário
            content: Conteúdo da mensagem
            media_path: Caminho opcional para arquivo de mídia
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        try:
            # Se houver mídia, fazer upload para o Firebase primeiro
            media_url = None
            if media_path:
                try:
                    # Determinar content type baseado na extensão
                    content_type = self._get_content_type(media_path)
                    # Fazer upload da mídia
                    media_url = upload_media(media_path, content_type, to)
                    logger.info(f"Mídia enviada para Firebase: {media_url}")
                except Exception as e:
                    logger.error(f"Erro ao fazer upload de mídia: {e}")
                    return False
            
            # Enviar mensagem
            message_id = self.client.send_message(to, content, media_url)
            
            if message_id:
                # Salvar mensagem enviada no Firebase
                message_data = {
                    'id': message_id,
                    'from': self.client.get_my_number(),
                    'to': to,
                    'body': content,
                    'timestamp': time.time(),
                    'fromMe': True,
                    'type': 'image' if media_url else 'text',
                    'mediaUrl': media_url
                }
                
                try:
                    save_message(message_data)
                    logger.info(f"Mensagem enviada salva no Firebase: {message_id}")
                except Exception as e:
                    logger.error(f"Erro ao salvar mensagem enviada no Firebase: {e}")
                
                return True
            
            logger.error("Falha ao enviar mensagem")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
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
    
    def get_connection_status(self) -> str:
        """
        Obtém o status atual da conexão com o WhatsApp.
        
        Returns:
            str: Status da conexão
        """
        return self.client.get_connection_status()
    
    def register_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Registra um handler para processar mensagens recebidas.
        
        Args:
            handler: Função callback que será chamada com os dados da mensagem
        """
        try:
            logger.info("Registrando handler de mensagens")
            # Substituir o callback atual pelo novo handler
            self.message_handler = handler
            # Atualizar o callback do cliente WhatsApp
            self.client.set_message_callback(self._message_callback_wrapper)
            logger.info("Handler de mensagens registrado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao registrar handler de mensagens: {e}")
            raise
    
    def _message_callback_wrapper(self, message_data: Dict[str, Any]) -> None:
        """
        Wrapper para o callback de mensagens que chama o handler registrado.
        
        Args:
            message_data: Dados da mensagem recebida
        """
        try:
            # Processar internamente a mensagem
            self._handle_message(message_data)
            
            # Chamar o handler externo se estiver definido
            if hasattr(self, 'message_handler') and self.message_handler is not None:
                self.message_handler(message_data)
                
        except Exception as e:
            logger.error(f"Erro no wrapper do callback de mensagens: {e}")

# Singleton para acesso global
whatsapp_integration = None

def get_whatsapp_integration():
    """
    Obtém a instância global da integração com WhatsApp.
    
    Returns:
        WhatsAppIntegration: Instância da integração
    """
    global whatsapp_integration
    if whatsapp_integration is None:
        whatsapp_integration = WhatsAppIntegration()
    
    return whatsapp_integration 