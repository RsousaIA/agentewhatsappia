"""
Agente Avaliador para análise de conversas do WhatsApp.
Avalia a qualidade do atendimento e gera estatísticas e relatórios.
"""

import os
import json
import time
from datetime import datetime
import threading
from typing import Dict, List, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from core.db import (
    init_firebase,
    get_firestore_db,
    get_conversation,
    get_conversations_by_status,
    get_conversation_messages,
    update_conversation
)

# Carrega variáveis de ambiente
load_dotenv()

# Configurações
EVALUATION_INTERVAL = int(os.getenv("EVALUATION_INTERVAL", "3600"))  # 1 hora em segundos

class EvaluatorAgent:
    """
    Agente responsável por avaliar conversas encerradas.
    """
    
    def __init__(self):
        """
        Inicializa o agente avaliador.
        """
        # Inicializa o Firebase
        try:
            init_firebase()
            self.db = get_firestore_db()
        except Exception as e:
            logger.error(f"Erro ao inicializar Firebase: {e}")
            raise
        
        # Controle de execução
        self.is_running = False
        self.threads = []
        
        # Thread de avaliação
        self.evaluation_thread = None
        
        # Intervalo de avaliação
        self.evaluation_interval = EVALUATION_INTERVAL
        
        logger.info("Agente Avaliador inicializado")
    
    def start(self):
        """
        Inicia o agente avaliador.
        """
        if self.is_running:
            logger.warning("Agente Avaliador já está em execução")
            return
        
        self.is_running = True
        
        # Iniciar thread de avaliação de conversas
        self.evaluation_thread = threading.Thread(
            target=self._evaluate_conversations,
            daemon=True
        )
        self.evaluation_thread.start()
        self.threads.append(self.evaluation_thread)
        
        logger.info("Thread de avaliação do Agente Avaliador iniciado")
    
    def stop(self):
        """
        Para o agente avaliador.
        """
        if not self.is_running:
            logger.warning("Agente Avaliador já está parado")
            return
        
        self.is_running = False
        
        # Aguardar pelo término dos threads (com timeout)
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self.threads = []
        logger.info("Agente Avaliador parado")
    
    def _evaluate_conversations(self):
        """
        Avalia conversas encerradas periodicamente.
        Esta função é executada em uma thread separada.
        """
        logger.info("Iniciando avaliação periódica de conversas")
        
        while self.is_running:
            try:
                # Buscar conversas encerradas que não foram avaliadas
                closed_conversations = get_conversations_by_status('CLOSED')
                
                # Filtrar apenas as que não foram avaliadas
                unevaluated = [conv for conv in closed_conversations if not conv.get('foiAvaliada', False)]
                
                logger.info(f"Encontradas {len(unevaluated)} conversas para avaliar")
                
                # Avaliar cada conversa
                for conversation in unevaluated:
                    try:
                        self._evaluate_single_conversation(conversation)
                    except Exception as e:
                        logger.error(f"Erro ao avaliar conversa {conversation.get('id')}: {e}")
                
                # Aguardar antes da próxima verificação
                time.sleep(self.evaluation_interval)
                
            except Exception as e:
                logger.error(f"Erro na avaliação de conversas: {e}")
                time.sleep(60)  # Pausa maior em caso de erro
    
    def _evaluate_single_conversation(self, conversation: Dict[str, Any]):
        """
        Avalia uma única conversa.
        
        Args:
            conversation: Dados da conversa
        """
        conversation_id = conversation.get('id')
        if not conversation_id:
            logger.warning("Conversa sem ID, ignorando")
            return
        
        logger.info(f"Avaliando conversa {conversation_id}")
        
        try:
            # Obter mensagens da conversa
            messages = get_conversation_messages(conversation_id)
            
            if not messages:
                logger.warning(f"Conversa {conversation_id} não possui mensagens")
                return
            
            # Realizar avaliação básica
            evaluation = self._perform_evaluation(conversation, messages)
            
            # Atualizar a conversa no Firebase com a avaliação
            update_conversation(conversation_id, {
                'avaliacao': evaluation,
                'foiAvaliada': True,
                'dataAvaliacao': datetime.now()
            })
            
            logger.info(f"Conversa {conversation_id} avaliada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa {conversation_id}: {e}")
    
    def _perform_evaluation(self, conversation: Dict[str, Any], messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Realiza a avaliação de uma conversa.
        
        Args:
            conversation: Dados da conversa
            messages: Lista de mensagens da conversa
            
        Returns:
            Dict: Resultado da avaliação
        """
        # Criar estrutura básica da avaliação
        evaluation = {
            'timestamp': datetime.now().isoformat(),
            'totalMensagens': len(messages),
            'tempoResposta': 0,
            'satisfacaoEstimada': 'neutra'
        }
        
        # Calcular tempo de resposta médio
        if len(messages) >= 2:
            response_times = []
            last_client_time = None
            
            for message in messages:
                is_client = message.get('remetente') == 'cliente'
                timestamp = message.get('timestamp')
                
                # Verificar se é timestamp válido
                if not timestamp:
                    continue
                
                # Converter para objeto datetime se for string
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except (ValueError, TypeError):
                        continue
                
                if is_client:
                    # Mensagem do cliente
                    last_client_time = timestamp
                elif last_client_time and not is_client:
                    # Mensagem do atendente após cliente
                    response_time = (timestamp - last_client_time).total_seconds()
                    response_times.append(response_time)
                    last_client_time = None
            
            # Calcular tempo médio de resposta
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                evaluation['tempoResposta'] = avg_response_time
        
        # Análise de sentimento básica
        client_sentiments = []
        
        for message in messages:
            is_client = message.get('remetente') == 'cliente'
            content = message.get('conteudo', '')
            
            if is_client and content:
                # Palavras positivas e negativas para análise simples
                positive_words = ['obrigado', 'bom', 'legal', 'gostei', 'feliz', 'resolvido']
                negative_words = ['ruim', 'problema', 'chateado', 'insatisfeito', 'erro', 'não funciona']
                
                content_lower = content.lower()
                
                pos_count = sum(1 for word in positive_words if word in content_lower)
                neg_count = sum(1 for word in negative_words if word in content_lower)
                
                if pos_count > neg_count:
                    client_sentiments.append('positive')
                elif neg_count > pos_count:
                    client_sentiments.append('negative')
                else:
                    client_sentiments.append('neutral')
        
        # Determinar satisfação geral
        if client_sentiments:
            pos_count = client_sentiments.count('positive')
            neg_count = client_sentiments.count('negative')
            neutral_count = client_sentiments.count('neutral')
            
            if pos_count > neg_count and pos_count > neutral_count:
                evaluation['satisfacaoEstimada'] = 'positiva'
            elif neg_count > pos_count and neg_count > neutral_count:
                evaluation['satisfacaoEstimada'] = 'negativa'
            else:
                evaluation['satisfacaoEstimada'] = 'neutra'
        
        return evaluation

# Instância global do agente
_evaluator_agent_instance = None

def get_evaluator_agent() -> EvaluatorAgent:
    """
    Retorna a instância global do Agente Avaliador.
    Cria uma nova instância se necessário.
    
    Returns:
        EvaluatorAgent: A instância do agente
    """
    global _evaluator_agent_instance
    
    if _evaluator_agent_instance is None:
        _evaluator_agent_instance = EvaluatorAgent()
        
    return _evaluator_agent_instance 