"""
Serviço de integração com WhatsApp.
Gerencia a conexão, processamento e armazenamento de mensagens.
"""

import os
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Protocol
from loguru import logger
from dotenv import load_dotenv
from .whatsapp_client import WhatsAppClient
from core.db import (
    init_firebase,
    get_firestore_db,
    get_conversation,
    create_conversation,
    update_conversation,
    save_message
)

# Carrega variáveis de ambiente
load_dotenv()

class MessageHandler(Protocol):
    """Protocolo para handler de mensagens"""
    def __call__(self, message_data: Dict[str, Any]) -> None: ...

class WhatsAppService:
    """
    Serviço que gerencia a integração com WhatsApp.
    Coordena a conexão com o servidor e o processamento de mensagens.
    """
    
    def __init__(self):
        """
        Inicializa o serviço de WhatsApp.
        """
        logger.info("Inicializando serviço de WhatsApp...")
        
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
        
        # Configurar callback para mensagens
        self.client.set_message_callback(self._handle_message)
        
        # Configurar callback para status de conexão
        self.client.set_connection_callback(self._handle_connection_status)
        
        # Lista de handlers de mensagem externos
        self.message_handlers: List[MessageHandler] = []
        
        # Controle de execução
        self._stop_event = threading.Event()
        self._whatsapp_thread = None
        
        logger.info("Serviço de WhatsApp inicializado com sucesso")
    
    def start(self):
        """
        Inicia o serviço de WhatsApp.
        """
        try:
            # Iniciar cliente WhatsApp em uma nova thread
            self._whatsapp_thread = threading.Thread(target=self._run_whatsapp_client, daemon=True)
            self._whatsapp_thread.start()
            
            logger.info("Serviço de WhatsApp iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar serviço de WhatsApp: {e}")
            raise
    
    def _run_whatsapp_client(self):
        """
        Executa o cliente WhatsApp.
        Esta função é executada em uma thread separada.
        """
        try:
            # Iniciar cliente WhatsApp
            self.client.start()
            logger.info("Cliente WhatsApp iniciado em thread separada")
            
            # Manter o loop rodando até que o evento de parada seja definido
            while not self._stop_event.is_set():
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Erro na thread do WhatsApp: {e}")
    
    def stop(self):
        """
        Para o serviço de WhatsApp.
        """
        try:
            # Sinalizar para a thread do WhatsApp parar
            self._stop_event.set()
            
            # Parar cliente WhatsApp
            self.client.stop()
            
            if self._whatsapp_thread and self._whatsapp_thread.is_alive():
                self._whatsapp_thread.join(timeout=5)
                logger.info("Thread do WhatsApp finalizada")
            
            logger.info("Serviço de WhatsApp parado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao parar serviço de WhatsApp: {e}")
            raise
    
    def _handle_message(self, message_data: Dict[str, Any]):
        """
        Processa uma mensagem recebida do WhatsApp.
        
        Args:
            message_data: Dados da mensagem recebida
        """
        try:
            # Validação da mensagem
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
                    'status': 'ACTIVE',
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
            
            # Repassar mensagem para handlers externos
            for handler in self.message_handlers:
                try:
                    handler(message_data)
                except Exception as e:
                    logger.error(f"Erro em handler de mensagem: {e}")
            
            # Marcar mensagem como lida se for do cliente
            if not message_data.get('fromMe', False):
                self.client.mark_messages_as_read([message_data.get('id')])
                logger.debug(f"Mensagem {message_data.get('id')} marcada como lida")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
    
    def _handle_connection_status(self, status: str):
        """
        Processa mudanças no status de conexão.
        
        Args:
            status: Novo status da conexão
        """
        try:
            logger.info(f"Status da conexão alterado: {status}")
            
            # Implementar lógica adicional se necessário
            
        except Exception as e:
            logger.error(f"Erro ao processar status de conexão: {e}")
    
    def send_message(self, to: str, content: str, media_path: Optional[str] = None) -> bool:
        """
        Envia uma mensagem para um número específico.
        
        Args:
            to: Número do destinatário
            content: Conteúdo da mensagem
            media_path: Caminho opcional para um arquivo de mídia
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        # Verificar se o destinatário tem o sufixo necessário
        if not to.endswith('@c.us') and not to.endswith('@g.us'):
            to = f"{to}@c.us"
        
        # Enviar a mensagem
        if self.client._event_loop:
            future = asyncio.run_coroutine_threadsafe(
                self.client.send_message(to, content, media_path),
                self.client._event_loop
            )
            try:
                result = future.result(timeout=10)  # Espera até 10 segundos
                
                # Se a mensagem foi enviada com sucesso, salvar no Firebase
                if result:
                    # Extrair ID da conversa (remover sufixo @c.us ou @g.us)
                    conversation_id = to.split('@')[0]
                    
                    # Preparar dados da mensagem
                    message_data = {
                        'tipo': 'texto',
                        'conteudo': content,
                        'remetente': 'sistema',
                        'timestamp': datetime.now()
                    }
                    
                    # Salvar mensagem
                    try:
                        save_message(conversation_id, message_data)
                        logger.info(f"Mensagem enviada salva no Firebase: {conversation_id}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar mensagem enviada: {e}")
                
                return result
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem: {e}")
                return False
        else:
            logger.error("Loop de eventos do cliente não está disponível")
            return False
    
    def register_message_handler(self, handler: MessageHandler):
        """
        Registra um handler para processar mensagens.
        
        Args:
            handler: Função que será chamada quando uma mensagem for recebida
        """
        logger.info("Registrando handler de mensagens")
        
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)
            logger.info("Handler de mensagens registrado com sucesso")
        else:
            logger.warning("Handler já está registrado")

# Instância global do serviço
_whatsapp_service_instance = None

def get_whatsapp_service() -> WhatsAppService:
    """
    Retorna a instância global do serviço de WhatsApp.
    Cria uma nova instância se necessário.
    
    Returns:
        WhatsAppService: A instância do serviço
    """
    global _whatsapp_service_instance
    
    if _whatsapp_service_instance is None:
        _whatsapp_service_instance = WhatsAppService()
        
    return _whatsapp_service_instance 