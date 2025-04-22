import pytest
import time
import queue
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
from agent import init_agents
from agent.collector_agent import CollectorAgent
from agent.evaluator_agent import EvaluatorAgent

@pytest.fixture
def notification_queue():
    """Fixture que retorna uma fila de notificações compartilhada."""
    return queue.Queue()

@pytest.fixture
def agents(notification_queue):
    """Fixture que retorna instâncias dos agentes para testes de integração."""
    with patch('database.firebase_db.init_firebase'), \
         patch('database.firebase_db.get_firestore_db'), \
         patch('agent.collector_agent.CollectorAgent._process_message_thread', return_value=None), \
         patch('agent.evaluator_agent.EvaluatorAgent._process_evaluation_queue', return_value=None):
        collector = CollectorAgent(evaluation_notification_queue=notification_queue)
        evaluator = EvaluatorAgent(notification_queue=notification_queue)
        
        collector._running = True  # Simular que o agente está em execução
        evaluator._running = True  # Simular que o agente está em execução
        
        return collector, evaluator

def test_end_to_end_conversation_flow(agents):
    """
    Testa o fluxo completo desde a criação de uma conversa, 
    passando pelo encerramento até a avaliação.
    """
    collector, evaluator = agents
    
    # 1. Configurar mocks para as operações do banco de dados
    with patch('database.firebase_db.get_conversation', return_value=None), \
         patch('database.firebase_db.create_conversation') as mock_create, \
         patch('database.firebase_db.update_conversation') as mock_update, \
         patch('database.firebase_db.save_message') as mock_save_message, \
         patch('database.firebase_db.get_messages_by_conversation') as mock_get_messages, \
         patch('database.firebase_db.save_evaluation') as mock_save_evaluation, \
         patch('database.firebase_db.save_consolidated_attendance') as mock_save_consolidated, \
         patch.object(evaluator.evaluation_manager, 'evaluate_conversation') as mock_evaluate:
        
        # Configurar a criação da conversa
        conversation_id = "test_conversation_123"
        mock_create.return_value = {"id": conversation_id, "status": "em_andamento"}
        
        # Configurar mensagens da conversa
        messages = [
            {
                'id': 'msg1',
                'remetente': 'cliente',
                'conteudo': 'Olá, preciso de ajuda',
                'timestamp': datetime.now() - timedelta(minutes=30)
            },
            {
                'id': 'msg2',
                'remetente': 'atendente',
                'conteudo': 'Como posso ajudar?',
                'timestamp': datetime.now() - timedelta(minutes=25)
            },
            {
                'id': 'msg3',
                'remetente': 'cliente',
                'conteudo': 'Obrigado pela ajuda',
                'timestamp': datetime.now() - timedelta(minutes=5)
            },
            {
                'id': 'msg4',
                'remetente': 'atendente',
                'conteudo': 'Por nada, tenha um bom dia!',
                'timestamp': datetime.now() - timedelta(minutes=2)
            }
        ]
        mock_get_messages.return_value = messages
        
        # Configurar resultado da avaliação
        mock_evaluate.return_value = {
            'comunicacao_nota': 0.9,
            'conhecimento_nota': 0.85,
            'empatia_nota': 0.8,
            'nota_geral': 0.85,
            'pontos_positivos': ['Atendimento cordial'],
            'pontos_negativos': [],
            'sugestoes_melhoria': []
        }
        
        # 2. Enviar mensagens para o agente coletor
        for i, msg in enumerate(messages):
            # Simular a recepção de uma mensagem
            collector.process_message({
                'conversation_id': conversation_id,
                'content': msg['conteudo'],
                'timestamp': msg['timestamp'],
                'type': 'cliente' if msg['remetente'] == 'cliente' else 'atendente'
            })
            
            # Verificar que a mensagem foi salva
            mock_save_message.assert_called()
        
        # 3. Simular a detecção de encerramento de conversa
        with patch.object(collector.ollama, 'should_close_conversation') as mock_should_close:
            # Configurar para retornar que a conversa deve ser encerrada
            mock_should_close.return_value = {
                'should_close': True,
                'confidence': 95,
                'reason': 'despedida'
            }
            
            # Chamar o método de detecção de encerramento
            result = collector._should_close_conversation(messages)
            assert result['should_close'] is True
            
            # Simular o encerramento da conversa
            collector._close_conversation(conversation_id, "Despedida detectada")
            
            # Verificar que a notificação foi enviada para a fila compartilhada
            assert not collector.evaluation_notification_queue.empty()
            
            # Obter a notificação da fila
            notification = collector.evaluation_notification_queue.get()
            assert notification['event'] == 'conversation_closed'
            assert notification['conversation_id'] == conversation_id
        
        # 4. Simular o processamento da notificação pelo avaliador
        with patch.object(evaluator, 'evaluate_conversation') as mock_eval_conversation, \
             patch('database.firebase_db.get_conversation') as mock_get_conversation:
            
            # Configurar para retornar os dados da conversa
            mock_get_conversation.return_value = {
                'id': conversation_id,
                'status': 'encerrada',
                'cliente': {'nome': 'Test User'},
                'dataHoraInicio': datetime.now() - timedelta(minutes=30),
                'dataHoraEncerramento': datetime.now() - timedelta(minutes=1)
            }
            
            # Processar a notificação
            evaluator._handle_notification(notification)
            
            # Verificar que a avaliação foi agendada com prioridade
            mock_eval_conversation.assert_called_once()
            assert mock_eval_conversation.call_args[0][0] == conversation_id
            
            # Simular a avaliação propriamente dita
            evaluator._evaluate_conversation(conversation_id)
            
            # Verificar que a avaliação foi salva
            mock_save_evaluation.assert_called_once()
            
            # Verificar que os dados consolidados foram salvos
            mock_save_consolidated.assert_called_once()
            
            # Verificar que a conversa foi marcada como avaliada
            mock_update.assert_called_with(conversation_id, {'avaliada': True})

def test_reopened_conversation_flow(agents):
    """
    Testa o fluxo de uma conversa que é reaberta após o encerramento.
    """
    collector, evaluator = agents
    
    # Configurar mocks para as operações do banco de dados
    with patch('database.firebase_db.get_conversation') as mock_get_conversation, \
         patch('database.firebase_db.update_conversation') as mock_update, \
         patch('database.firebase_db.save_message') as mock_save_message, \
         patch('database.firebase_db.get_messages_by_conversation'), \
         patch('database.firebase_db.update_conversation_status') as mock_update_status, \
         patch.object(evaluator, 'evaluate_conversation') as mock_evaluate:
        
        # Configurar a conversa já existente e encerrada
        conversation_id = "test_conversation_reopened"
        mock_get_conversation.return_value = {
            'id': conversation_id,
            'status': 'encerrada',
            'avaliada': True,
            'cliente': {'nome': 'Test User'},
            'dataHoraInicio': datetime.now() - timedelta(days=1),
            'dataHoraEncerramento': datetime.now() - timedelta(hours=2)
        }
        
        # Simular a recepção de uma nova mensagem após encerramento
        new_message = {
            'conversation_id': conversation_id,
            'content': 'Desculpe, tenho mais uma dúvida',
            'timestamp': datetime.now(),
            'type': 'cliente'
        }
        
        # Processar a mensagem
        collector.process_message(new_message)
        
        # Verificar que a conversa foi reaberta
        mock_update_status.assert_called_with(conversation_id, 'reaberta')
        
        # Verificar que a mensagem foi salva
        mock_save_message.assert_called()
        
        # Simular o encerramento novamente
        collector._close_conversation(conversation_id, "Conversa encerrada novamente")
        
        # Verificar que uma nova notificação foi enviada
        assert not collector.evaluation_notification_queue.empty()
        
        # Obter a notificação
        notification = collector.evaluation_notification_queue.get()
        
        # Processar a notificação pelo avaliador
        evaluator._handle_notification(notification)
        
        # Verificar que a avaliação foi agendada com prioridade máxima (1)
        # por ser uma conversa reaberta
        mock_evaluate.assert_called_once()
        assert mock_evaluate.call_args[0][1] <= 2  # Prioridade alta (1 ou 2) 