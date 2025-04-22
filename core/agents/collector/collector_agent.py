"""
Agente Coletor para processamento de mensagens do WhatsApp.
Analisa, classifica e gerencia conversas.
"""

import os
import json
import time
from datetime import datetime
import threading
import queue
from typing import Dict, List, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from queue import Queue, Empty
from core.db import (
    init_firebase,
    get_firestore_db,
    save_message,
    get_conversation,
    update_conversation,
    create_conversation,
    get_conversations_by_status,
    get_conversation_messages
)

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT", "21600"))  # 6 horas em segundos
EVALUATION_INTERVAL = int(os.getenv("EVALUATION_INTERVAL", "3600"))  # 1 hora em segundos
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "3600"))  # 1 hora em segundos

class CollectorAgent:
    """
    Agente responsável por coletar, processar e analisar mensagens do WhatsApp.
    """
    
    def __init__(self):
        """
        Inicializa o agente coletor.
        """
        # Inicializa o Firebase
        try:
            init_firebase()
            self.db = get_firestore_db()
        except Exception as e:
            logger.error(f"Erro ao inicializar Firebase: {e}")
            raise
        
        # Fila de mensagens para processamento
        self.message_queue = Queue()
        
        # Controle de execução
        self.is_running = False
        self.threads = []
        
        # Threads de processamento
        self.message_processing_thread = None
        self.inactive_cleaning_thread = None
        
        # Intervalo de verificação
        self.cleanup_interval = CLEANUP_INTERVAL
        
        # Cache de conversas ativas
        self.active_conversations = {}
        
        logger.info("Agente Coletor inicializado")
    
    def start(self):
        """
        Inicia o agente coletor.
        """
        if self.is_running:
            logger.warning("Agente Coletor já está em execução")
            return
        
        self.is_running = True
        
        # Iniciar thread de processamento de mensagens
        self.message_processing_thread = threading.Thread(
            target=self._process_messages,
            daemon=True
        )
        self.message_processing_thread.start()
        self.threads.append(self.message_processing_thread)
        
        # Iniciar thread de limpeza de conversas inativas
        self.inactive_cleaning_thread = threading.Thread(
            target=self._clean_inactive_conversations,
            daemon=True
        )
        self.inactive_cleaning_thread.start()
        self.threads.append(self.inactive_cleaning_thread)
        
        logger.info("Todos os threads do Agente Coletor foram iniciados")
    
    def stop(self):
        """
        Para o agente coletor.
        """
        if not self.is_running:
            logger.warning("Agente Coletor já está parado")
            return
        
        self.is_running = False
        
        # Aguardar pelo término dos threads (com timeout)
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self.threads = []
        logger.info("Agente Coletor parado")
    
    def process_message(self, message_data: Dict[str, Any]):
        """
        Processa uma nova mensagem recebida.
        
        Args:
            message_data: Dados da mensagem
        """
        try:
            # Adiciona a mensagem à fila de processamento
            self.message_queue.put(message_data)
            
            logger.info(f"Mensagem {message_data.get('id')} adicionada à fila de processamento")
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem à fila: {e}")
    
    def _process_messages(self):
        """
        Processa mensagens da fila de processamento.
        Esta função é executada em uma thread separada.
        """
        logger.info("Iniciando processamento de mensagens")
        
        while self.is_running:
            try:
                # Tenta obter uma mensagem da fila com timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                    self._process_single_message(message)
                    self.message_queue.task_done()
                except Empty:
                    # Fila vazia, continuar
                    pass
            except Exception as e:
                logger.error(f"Erro no processamento de mensagens: {e}")
                time.sleep(1)  # Pausa breve para evitar loop infinito em caso de erro
    
    def _process_single_message(self, message_data: Dict[str, Any]):
        """
        Processa uma única mensagem.
        
        Args:
            message_data: Dados da mensagem
        """
        try:
            # Extrair informações básicas
            message_id = message_data.get('id')
            if not message_id:
                logger.warning("Mensagem sem ID, gerando ID aleatório")
                message_id = f"generated_{time.time()}"
            
            # Extrair remetente
            sender = message_data.get('from', '').replace('@c.us', '')
            
            # Extrair conteúdo
            content = message_data.get('body', '')
            
            # Definir ID da conversa (assumindo que é o número do remetente)
            conversation_id = sender
            
            # Verificar se a conversa existe
            conversation = get_conversation(conversation_id)
            
            if not conversation:
                # Criar nova conversa
                logger.info(f"Criando nova conversa para {sender}")
                
                conversation_data = {
                    'cliente': {
                        'nome': message_data.get('contact_name', ''),
                        'telefone': sender
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
                
                # Adicionar ao cache de conversas ativas
                self.active_conversations[conversation_id] = {
                    'last_activity': time.time()
                }
            
            # Atualizar timestamp de última atividade
            if conversation_id in self.active_conversations:
                self.active_conversations[conversation_id]['last_activity'] = time.time()
            else:
                self.active_conversations[conversation_id] = {
                    'last_activity': time.time()
                }
            
            # Analisar a mensagem (implementação simples aqui, expansível no futuro)
            analysis = self._analyze_message(content)
            
            # Atualizar a conversa no Firebase
            update_conversation(conversation_id, {
                'ultimaMensagem': datetime.now(),
                'ultimaAnalise': analysis
            })
            
            logger.info(f"Mensagem {message_id} processada para a conversa {conversation_id}")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
    
    def _analyze_message(self, message: str) -> Dict[str, Any]:
        """
        Analisa o conteúdo de uma mensagem.
        Versão simplificada, pode ser expandida no futuro.
        
        Args:
            message: Conteúdo da mensagem
            
        Returns:
            Dict: Resultado da análise
        """
        # Implementação simples
        analysis = {
            'length': len(message),
            'timestamp': datetime.now().isoformat()
        }
        
        # Detecção de sentimento (implementação básica)
        positive_words = ['obrigado', 'bom', 'legal', 'gostei', 'feliz']
        negative_words = ['ruim', 'problema', 'chateado', 'insatisfeito', 'erro']
        
        message_lower = message.lower()
        
        pos_count = sum(1 for word in positive_words if word in message_lower)
        neg_count = sum(1 for word in negative_words if word in message_lower)
        
        if pos_count > neg_count:
            sentiment = 'positive'
        elif neg_count > pos_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        analysis['sentiment'] = sentiment
        
        return analysis
    
    def _clean_inactive_conversations(self):
        """
        Verifica e marca como encerradas conversas inativas.
        Esta função é executada em uma thread separada.
        """
        logger.info("Iniciando limpeza de conversas inativas")
        
        while self.is_running:
            try:
                # Obter o timestamp atual
                current_time = time.time()
                
                # Conversas a serem fechadas
                to_close = []
                
                # Verificar cada conversa ativa
                for conversation_id, data in list(self.active_conversations.items()):
                    last_activity = data.get('last_activity', 0)
                    elapsed = current_time - last_activity
                    
                    # Se o tempo sem atividade for maior que o timeout, fechar a conversa
                    if elapsed > INACTIVITY_TIMEOUT:
                        to_close.append(conversation_id)
                
                # Fechar conversas inativas
                for conversation_id in to_close:
                    try:
                        # Atualizar status no Firebase
                        update_conversation(conversation_id, {
                            'status': 'CLOSED',
                            'dataHoraEncerramento': datetime.now()
                        })
                        
                        # Remover do cache de conversas ativas
                        if conversation_id in self.active_conversations:
                            del self.active_conversations[conversation_id]
                        
                        logger.info(f"Conversa {conversation_id} fechada por inatividade")
                    except Exception as e:
                        logger.error(f"Erro ao fechar conversa {conversation_id}: {e}")
                
                # Pausar antes da próxima verificação
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Erro na limpeza de conversas inativas: {e}")
                time.sleep(60)  # Pausa maior em caso de erro

# Instância global do agente
_collector_agent_instance = None

def get_collector_agent() -> CollectorAgent:
    """
    Retorna a instância global do Agente Coletor.
    Cria uma nova instância se necessário.
    
    Returns:
        CollectorAgent: A instância do agente
    """
    global _collector_agent_instance
    
    if _collector_agent_instance is None:
        _collector_agent_instance = CollectorAgent()
        
    return _collector_agent_instance 