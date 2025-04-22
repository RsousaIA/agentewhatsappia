import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from agent.collectors.collector_agent import CollectorAgent
from database.firebase_db import init_firebase, get_firestore_db

@pytest.fixture
def collector_agent():
    """Fixture que retorna uma instância do CollectorAgent para testes."""
    with patch('database.firebase_db.init_firebase'), \
         patch('database.firebase_db.get_firestore_db'):
        agent = CollectorAgent()
        return agent

def test_collector_agent_initialization(collector_agent):
    """Testa a inicialização do CollectorAgent."""
    assert collector_agent._message_queue is not None
    assert collector_agent._processing_thread is None
    assert collector_agent._cleanup_thread is None
    assert collector_agent._running is False
    assert collector_agent._inactive_timeout == 1800  # 30 minutos
    assert collector_agent._cleanup_interval == 300   # 5 minutos

def test_start_stop(collector_agent):
    """Testa o início e parada do agente."""
    collector_agent.start()
    assert collector_agent._running is True
    assert collector_agent._processing_thread is not None
    assert collector_agent._cleanup_thread is not None
    
    collector_agent.stop()
    assert collector_agent._running is False
    assert collector_agent._processing_thread is None
    assert collector_agent._cleanup_thread is None

def test_process_message(collector_agent):
    """Testa o processamento de mensagens."""
    message = {
        'id': 'test_message',
        'conversation_id': 'test_conversation',
        'content': 'Test message',
        'timestamp': datetime.now(),
        'type': 'USER'
    }
    
    with patch('database.firebase_db.save_message') as mock_save:
        collector_agent.process_message(message)
        
        # Verifica se a mensagem foi adicionada à fila
        assert not collector_agent._message_queue.empty()
        
        # Verifica se a mensagem foi salva no Firebase
        mock_save.assert_called_once()

def test_process_messages_queue(collector_agent):
    """Testa o processamento da fila de mensagens."""
    messages = [
        {
            'id': f'test_message_{i}',
            'conversation_id': 'test_conversation',
            'content': f'Test message {i}',
            'timestamp': datetime.now(),
            'type': 'USER'
        }
        for i in range(3)
    ]
    
    with patch('database.firebase_db.save_message') as mock_save:
        # Adiciona mensagens à fila
        for msg in messages:
            collector_agent._message_queue.put(msg)
        
        # Processa a fila
        collector_agent._process_messages()
        
        # Verifica se todas as mensagens foram salvas
        assert mock_save.call_count == 3

def test_should_close_conversation(collector_agent):
    """Testa o método de detecção de encerramento de conversa com Ollama."""
    # Cria mensagens de teste com despedida
    messages = [
        {
            'remetente': 'cliente',
            'content': 'Olá, preciso de ajuda',
            'timestamp': datetime.now() - timedelta(minutes=10)
        },
        {
            'remetente': 'atendente',
            'content': 'Como posso ajudar?',
            'timestamp': datetime.now() - timedelta(minutes=8)
        },
        {
            'remetente': 'cliente',
            'content': 'Obrigado pela ajuda',
            'timestamp': datetime.now() - timedelta(minutes=5)
        },
        {
            'remetente': 'atendente',
            'content': 'Por nada, tenha um bom dia!',
            'timestamp': datetime.now() - timedelta(minutes=2)
        }
    ]
    
    # Mock para o Ollama
    ollama_result = {
        'should_close': True,
        'confidence': 90,
        'reason': 'despedida'
    }
    
    # Substitui o ollama do collector_agent por um mock
    collector_agent.ollama = Mock()
    collector_agent.ollama.should_close_conversation.return_value = ollama_result
    
    # Executa o método de detecção de encerramento
    result = collector_agent._should_close_conversation(messages)
    
    # Verifica se o Ollama foi chamado corretamente
    collector_agent.ollama.should_close_conversation.assert_called_once()
    
    # Verifica o resultado
    assert result['should_close'] is True
    assert result['reason'] == 'despedida'

def test_should_close_conversation_with_error(collector_agent):
    """Testa o método de detecção quando há erro no Ollama (fallback para palavras de despedida)."""
    # Cria mensagens de teste com despedida
    messages = [
        {
            'remetente': 'cliente',
            'content': 'Olá, preciso de ajuda',
            'timestamp': datetime.now() - timedelta(minutes=10)
        },
        {
            'remetente': 'atendente',
            'content': 'Como posso ajudar?',
            'timestamp': datetime.now() - timedelta(minutes=8)
        },
        {
            'remetente': 'cliente',
            'content': 'Já resolvi, muito obrigado',
            'timestamp': datetime.now() - timedelta(minutes=5)
        }
    ]
    
    # Configura o mock para lançar exceção
    collector_agent.ollama = Mock()
    collector_agent.ollama.should_close_conversation.side_effect = Exception("Erro de conexão")
    
    # Executa o método de detecção de encerramento
    result = collector_agent._should_close_conversation(messages)
    
    # Verifica se o resultado do fallback indica encerramento devido a palavras de despedida
    assert result['should_close'] is True
    assert result['reason'] == 'despedida'

def test_should_close_conversation_active(collector_agent):
    """Testa o método de detecção para conversas ainda ativas."""
    # Cria mensagens de teste sem despedida
    messages = [
        {
            'remetente': 'cliente',
            'content': 'Olá, preciso de ajuda',
            'timestamp': datetime.now() - timedelta(minutes=10)
        },
        {
            'remetente': 'atendente',
            'content': 'Como posso ajudar?',
            'timestamp': datetime.now() - timedelta(minutes=8)
        },
        {
            'remetente': 'cliente',
            'content': 'Estou com problema no produto',
            'timestamp': datetime.now() - timedelta(minutes=5)
        }
    ]
    
    # Mock para o Ollama
    ollama_result = {
        'should_close': False,
        'confidence': 85,
        'reason': 'conversa_ativa'
    }
    
    # Substitui o ollama do collector_agent por um mock
    collector_agent.ollama = Mock()
    collector_agent.ollama.should_close_conversation.return_value = ollama_result
    
    # Executa o método de detecção de encerramento
    result = collector_agent._should_close_conversation(messages)
    
    # Verifica se o resultado indica que a conversa ainda está ativa
    assert result['should_close'] is False
    assert result['reason'] == 'conversa_ativa'

def test_cleanup_inactive_conversations(collector_agent):
    """Testa a limpeza de conversas inativas."""
    # Cria conversas de teste
    active_conversation = {
        'id': 'active_conversation',
        'last_message_time': datetime.now(),
        'status': 'ACTIVE'
    }
    
    inactive_conversation = {
        'id': 'inactive_conversation',
        'last_message_time': datetime.now() - timedelta(hours=1),
        'status': 'ACTIVE'
    }
    
    with patch('database.firebase_db.get_conversations') as mock_get, \
         patch('database.firebase_db.update_conversation_status') as mock_update:
        
        mock_get.return_value = [active_conversation, inactive_conversation]
        
        # Executa a limpeza
        collector_agent._cleanup_inactive_conversations()
        
        # Verifica se apenas a conversa inativa foi atualizada
        mock_update.assert_called_once_with(
            inactive_conversation['id'],
            'CLOSED',
            'Inatividade prolongada'
        )

def test_handle_message_error(collector_agent):
    """Testa o tratamento de erros no processamento de mensagens."""
    invalid_message = {
        'id': 'invalid_message',
        'conversation_id': None,  # Campo obrigatório faltando
        'content': 'Test message',
        'timestamp': datetime.now(),
        'type': 'USER'
    }
    
    with patch('database.firebase_db.save_message') as mock_save:
        collector_agent.process_message(invalid_message)
        
        # Verifica se a mensagem foi adicionada à fila
        assert not collector_agent._message_queue.empty()
        
        # Verifica se houve tentativa de salvar no Firebase
        mock_save.assert_not_called()

def test_conversation_creation(collector_agent):
    """Testa a criação de novas conversas."""
    message = {
        'id': 'test_message',
        'conversation_id': 'new_conversation',
        'content': 'Test message',
        'timestamp': datetime.now(),
        'type': 'USER'
    }
    
    with patch('database.firebase_db.get_conversation') as mock_get, \
         patch('database.firebase_db.create_conversation') as mock_create:
        
        mock_get.return_value = None  # Simula conversa inexistente
        
        collector_agent.process_message(message)
        
        # Verifica se a conversa foi criada
        mock_create.assert_called_once()

def test_message_processing_thread(collector_agent):
    """Testa o funcionamento da thread de processamento de mensagens."""
    collector_agent.start()
    
    message = {
        'id': 'test_message',
        'conversation_id': 'test_conversation',
        'content': 'Test message',
        'timestamp': datetime.now(),
        'type': 'USER'
    }
    
    with patch('database.firebase_db.save_message') as mock_save:
        collector_agent.process_message(message)
        
        # Aguarda um pouco para a thread processar
        import time
        time.sleep(0.1)
        
        # Verifica se a mensagem foi processada
        mock_save.assert_called_once()
    
    collector_agent.stop()

def test_cleanup_thread(collector_agent):
    """Testa o funcionamento da thread de limpeza."""
    collector_agent.start()
    
    with patch('database.firebase_db.get_conversations') as mock_get, \
         patch('database.firebase_db.update_conversation_status') as mock_update:
        
        mock_get.return_value = []
        
        # Aguarda um pouco para a thread executar
        import time
        time.sleep(0.1)
        
        # Verifica se a verificação foi feita
        mock_get.assert_called()
    
    collector_agent.stop()

def test_concurrent_message_processing(collector_agent):
    """Testa o processamento concorrente de mensagens."""
    collector_agent.start()
    
    messages = [
        {
            'id': f'test_message_{i}',
            'conversation_id': 'test_conversation',
            'content': f'Test message {i}',
            'timestamp': datetime.now(),
            'type': 'USER'
        }
        for i in range(10)
    ]
    
    with patch('database.firebase_db.save_message') as mock_save:
        # Adiciona mensagens concorrentemente
        import threading
        
        def add_messages():
            for msg in messages:
                collector_agent.process_message(msg)
        
        threads = [threading.Thread(target=add_messages) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Aguarda o processamento
        import time
        time.sleep(0.1)
        
        # Verifica se todas as mensagens foram processadas
        assert mock_save.call_count == 30  # 10 mensagens * 3 threads
    
    collector_agent.stop() 