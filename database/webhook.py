import os
import json
import logging
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from threading import Thread
from queue import Queue
from .firebase_db import get_firestore_db, init_firebase

# Configuração de logging
logger = logging.getLogger(__name__)

# Inicializa o Firebase
init_firebase()

# Fila de notificações
notification_queue = Queue()

class WebhookManager:
    def __init__(self):
        self.app = Flask(__name__)
        self.setup_routes()
        self.processing_thread = None
        self.running = False
        
    def setup_routes(self):
        """Configura as rotas do webhook"""
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                # Adiciona à fila de processamento
                notification_queue.put(data)
                
                return jsonify({'status': 'received'}), 200
            except Exception as e:
                logger.error(f"Erro no webhook: {e}")
                return jsonify({'error': str(e)}), 500
    
    def start_processing(self):
        """Inicia a thread de processamento de notificações"""
        self.running = True
        self.processing_thread = Thread(target=self._process_notifications)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """Para a thread de processamento"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()
    
    def _process_notifications(self):
        """Processa as notificações da fila"""
        while self.running:
            try:
                # Obtém a próxima notificação
                notification = notification_queue.get(timeout=1)
                
                # Processa a notificação
                self._handle_notification(notification)
                
                # Marca como processada
                notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Erro ao processar notificação: {e}")
    
    def _handle_notification(self, notification: Dict):
        """Processa uma notificação específica"""
        try:
            event_type = notification.get('type')
            data = notification.get('data', {})
            
            if event_type == 'new_message':
                self._handle_new_message(data)
            elif event_type == 'conversation_closed':
                self._handle_conversation_closed(data)
            elif event_type == 'conversation_reopened':
                self._handle_conversation_reopened(data)
            elif event_type == 'evaluation_completed':
                self._handle_evaluation_completed(data)
            else:
                logger.warning(f"Tipo de evento desconhecido: {event_type}")
                
        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}")
    
    def _handle_new_message(self, data: Dict):
        """Processa notificação de nova mensagem"""
        conversation_id = data.get('conversation_id')
        message_id = data.get('message_id')
        
        # Notifica o Agente Coletor
        # Implementar lógica específica aqui
    
    def _handle_conversation_closed(self, data: Dict):
        """Processa notificação de conversa encerrada"""
        conversation_id = data.get('conversation_id')
        
        # Notifica o Agente Avaliador
        # Implementar lógica específica aqui
    
    def _handle_conversation_reopened(self, data: Dict):
        """Processa notificação de conversa reaberta"""
        conversation_id = data.get('conversation_id')
        
        # Notifica o Agente Coletor
        # Implementar lógica específica aqui
    
    def _handle_evaluation_completed(self, data: Dict):
        """Processa notificação de avaliação concluída"""
        conversation_id = data.get('conversation_id')
        evaluation_id = data.get('evaluation_id')
        
        # Atualiza métricas e estatísticas
        # Implementar lógica específica aqui

def start_webhook():
    """Inicia o servidor webhook"""
    webhook_manager = WebhookManager()
    webhook_manager.start_processing()
    
    # Configura o host e porta
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.getenv('WEBHOOK_PORT', '5000'))
    
    # Inicia o servidor Flask
    webhook_manager.app.run(host=host, port=port) 