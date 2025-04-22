import unittest
from datetime import datetime, timedelta
from database.firebase_db import (
    init_firebase,
    get_firestore_db,
    # Funções de conversas
    get_conversation,
    create_conversation,
    update_conversation,
    # Funções de mensagens
    get_messages_by_conversation,
    save_message,
    # Funções de solicitações
    get_solicitacoes_by_status,
    create_solicitacao,
    update_solicitacao,
    get_solicitacao,
    # Funções de avaliações
    get_avaliacoes_by_conversation,
    create_avaliacao,
    get_avaliacao,
    # Funções de consolidado
    get_consolidado_by_period,
    create_consolidado,
    get_consolidado,
    get_conversations_with_pagination,
    get_messages_with_pagination
)
from tests.test_config import FIREBASE_TEST_CONFIG, COLLECTIONS
import os
from dotenv import load_dotenv
import pytest
from unittest.mock import patch, MagicMock

class TestFirebaseCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuração inicial para todos os testes"""
        load_dotenv()
        
        # Verifica se as configurações necessárias estão presentes
        for key, value in FIREBASE_TEST_CONFIG.items():
            if not value:
                raise ValueError(f"Configuração {key} não encontrada no arquivo .env")
                
        init_firebase()
        cls.db = get_firestore_db()
        
    def setUp(self):
        """Configuração antes de cada teste"""
        # Limpa os dados de teste anteriores
        self._cleanup_test_data()
        
    def tearDown(self):
        """Limpeza após cada teste"""
        self._cleanup_test_data()
        
    def _cleanup_test_data(self):
        """Remove todos os documentos de teste"""
        for collection in COLLECTIONS.values():
            docs = self.db.collection(collection).stream()
            for doc in docs:
                doc.reference.delete()
                
    def test_conversation_crud(self):
        """Testa operações CRUD para conversas"""
        # Teste de criação
        conversation_data = {
            'cliente_id': 'test_cliente',
            'status': 'aberta',
            'ultima_mensagem': 'Teste inicial'
        }
        conversation_id = create_conversation(conversation_data)
        self.assertIsNotNone(conversation_id)
        
        # Teste de leitura
        conversation = get_conversation(conversation_id)
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation['cliente_id'], 'test_cliente')
        
        # Teste de atualização
        update_data = {
            'status': 'fechada',
            'ultima_mensagem': 'Teste atualizado'
        }
        success = update_conversation(conversation_id, update_data)
        self.assertTrue(success)
        
        # Verifica atualização
        updated_conversation = get_conversation(conversation_id)
        self.assertEqual(updated_conversation['status'], 'fechada')
        
    def test_messages_crud(self):
        """Testa operações CRUD para mensagens"""
        # Cria uma conversa para teste
        conversation_id = create_conversation({
            'cliente_id': 'test_cliente',
            'status': 'aberta'
        })
        
        # Teste de criação de mensagem
        message_data = {
            'conversation_id': conversation_id,
            'sender': 'test_cliente',
            'content': 'Teste de mensagem',
            'type': 'text'
        }
        message_id = save_message(message_data)
        self.assertIsNotNone(message_id)
        
        # Teste de leitura de mensagens
        messages = get_messages_by_conversation(conversation_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['content'], 'Teste de mensagem')
        
    def test_solicitacoes_crud(self):
        """Testa operações CRUD para solicitações"""
        # Teste de criação
        solicitacao_data = {
            'cliente_id': 'test_cliente',
            'tipo': 'suporte',
            'descricao': 'Teste de solicitação',
            'status': 'aberta'
        }
        solicitacao_id = create_solicitacao(solicitacao_data)
        self.assertIsNotNone(solicitacao_id)
        
        # Teste de leitura por status
        solicitacoes = get_solicitacoes_by_status('aberta')
        self.assertEqual(len(solicitacoes), 1)
        
        # Teste de leitura específica
        solicitacao = get_solicitacao(solicitacao_id)
        self.assertIsNotNone(solicitacao)
        self.assertEqual(solicitacao['tipo'], 'suporte')
        
        # Teste de atualização
        update_data = {
            'status': 'fechada',
            'resposta': 'Teste de resposta'
        }
        success = update_solicitacao(solicitacao_id, update_data)
        self.assertTrue(success)
        
        # Verifica atualização
        updated_solicitacao = get_solicitacao(solicitacao_id)
        self.assertEqual(updated_solicitacao['status'], 'fechada')
        
    def test_avaliacoes_crud(self):
        """Testa operações CRUD para avaliações"""
        # Cria uma conversa para teste
        conversation_id = create_conversation({
            'cliente_id': 'test_cliente',
            'status': 'fechada'
        })
        
        # Teste de criação
        avaliacao_data = {
            'conversation_id': conversation_id,
            'nota': 5,
            'comentario': 'Excelente atendimento',
            'cliente_id': 'test_cliente'
        }
        avaliacao_id = create_avaliacao(avaliacao_data)
        self.assertIsNotNone(avaliacao_id)
        
        # Teste de leitura por conversa
        avaliacoes = get_avaliacoes_by_conversation(conversation_id)
        self.assertEqual(len(avaliacoes), 1)
        self.assertEqual(avaliacoes[0]['nota'], 5)
        
        # Teste de leitura específica
        avaliacao = get_avaliacao(avaliacao_id)
        self.assertIsNotNone(avaliacao)
        self.assertEqual(avaliacao['comentario'], 'Excelente atendimento')
        
    def test_consolidado_crud(self):
        """Testa operações CRUD para dados consolidados"""
        # Define período de teste
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # Teste de criação
        consolidado_data = {
            'data_inicio': start_date,
            'data_fim': end_date,
            'total_atendimentos': 10,
            'media_avaliacao': 4.5,
            'tempo_medio_resposta': 120
        }
        consolidado_id = create_consolidado(consolidado_data)
        self.assertIsNotNone(consolidado_id)
        
        # Teste de leitura por período
        consolidado = get_consolidado_by_period(start_date, end_date)
        self.assertIsNotNone(consolidado)
        self.assertEqual(consolidado['total_atendimentos'], 10)
        
        # Teste de leitura específica
        consolidado = get_consolidado(consolidado_id)
        self.assertIsNotNone(consolidado)
        self.assertEqual(consolidado['media_avaliacao'], 4.5)

def test_get_conversation():
    """Testa a obtenção de uma conversa específica."""
    conversation_id = 'test_conversation'
    expected_data = {'status': 'em_andamento', 'cliente': {'nome': 'Test User'}}
    
    with patch('database.firebase_db.get_firestore_db') as mock_db:
        # Configura o mock para retornar os dados esperados
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = expected_data
        mock_db.return_value.collection().document().get.return_value = mock_doc
        
        # Executa a função
        result = get_conversation(conversation_id)
        
        # Verifica o resultado
        assert result == expected_data
        mock_db.return_value.collection.assert_called_once_with('conversas')
        mock_db.return_value.collection().document.assert_called_once_with(conversation_id)

def test_get_conversations_with_pagination_no_status():
    """Testa a paginação de conversas sem filtro de status."""
    # Mock para documentos retornados pelo Firestore
    mock_docs = []
    for i in range(3):
        mock_doc = MagicMock()
        mock_doc.id = f'conversation_{i}'
        mock_doc.to_dict.return_value = {
            'ultimaMensagem': datetime.now(),
            'status': 'em_andamento',
            'cliente': {'nome': f'Cliente {i}'}
        }
        mock_docs.append(mock_doc)
    
    with patch('database.firebase_db.get_firestore_db') as mock_db:
        # Configura o mock para retornar a lista de documentos
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.return_value.collection().order_by().limit.return_value = mock_query
        
        # Executa a função
        conversations, last_doc_id = get_conversations_with_pagination(limit=3)
        
        # Verifica o resultado
        assert len(conversations) == 3
        assert all('id' in conv for conv in conversations)
        assert last_doc_id == 'conversation_2'  # Último documento
        
        # Verifica que o método order_by foi chamado corretamente
        mock_db.return_value.collection().order_by.assert_called_once()

def test_get_conversations_with_pagination_with_status():
    """Testa a paginação de conversas com filtro de status."""
    # Mock para documentos retornados pelo Firestore
    mock_docs = []
    for i in range(2):
        mock_doc = MagicMock()
        mock_doc.id = f'conversation_{i}'
        mock_doc.to_dict.return_value = {
            'ultimaMensagem': datetime.now(),
            'status': 'encerrada',
            'cliente': {'nome': f'Cliente {i}'}
        }
        mock_docs.append(mock_doc)
    
    with patch('database.firebase_db.get_firestore_db') as mock_db, \
         patch('database.firebase_db.firestore') as mock_firestore:
        # Configura o mock para retornar a lista de documentos
        mock_filter = MagicMock()
        mock_db.return_value.collection().where.return_value = mock_filter
        mock_filter.order_by().limit.return_value.stream.return_value = mock_docs
        
        # Executa a função
        conversations, last_doc_id = get_conversations_with_pagination(status='encerrada', limit=2)
        
        # Verifica o resultado
        assert len(conversations) == 2
        assert all(conv['status'] == 'encerrada' for conv in conversations)
        assert last_doc_id == 'conversation_1'  # Último documento
        
        # Verifica que o método where foi chamado corretamente
        mock_db.return_value.collection().where.assert_called_once()

def test_get_conversations_with_pagination_with_start_after():
    """Testa a paginação de conversas com ponto de início."""
    # Mock para o documento de início
    start_doc = MagicMock()
    start_doc.exists = True
    
    # Mock para documentos retornados pelo Firestore
    mock_docs = []
    for i in range(3):
        mock_doc = MagicMock()
        mock_doc.id = f'conversation_next_{i}'
        mock_doc.to_dict.return_value = {
            'ultimaMensagem': datetime.now(),
            'status': 'em_andamento',
            'cliente': {'nome': f'Cliente Next {i}'}
        }
        mock_docs.append(mock_doc)
    
    with patch('database.firebase_db.get_firestore_db') as mock_db:
        # Configura o mock para retornar o documento de início
        mock_db.return_value.collection().document().get.return_value = start_doc
        
        # Configura o mock para retornar a lista de documentos após o ponto de início
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_docs
        mock_db.return_value.collection().order_by().start_after().limit.return_value = mock_query
        
        # Executa a função
        conversations, last_doc_id = get_conversations_with_pagination(
            limit=3,
            start_after='last_conversation_id'
        )
        
        # Verifica o resultado
        assert len(conversations) == 3
        assert all('id' in conv for conv in conversations)
        assert last_doc_id == 'conversation_next_2'  # Último documento
        
        # Verifica que o método start_after foi chamado corretamente
        mock_db.return_value.collection().order_by().start_after.assert_called_once()

def test_get_messages_with_pagination():
    """Testa a paginação de mensagens de uma conversa."""
    conversation_id = 'test_conversation'
    
    # Mock para documentos retornados pelo Firestore
    mock_docs = []
    for i in range(5):
        mock_doc = MagicMock()
        mock_doc.id = f'message_{i}'
        mock_doc.to_dict.return_value = {
            'timestamp': datetime.now(),
            'remetente': 'cliente' if i % 2 == 0 else 'atendente',
            'conteudo': f'Mensagem de teste {i}'
        }
        mock_docs.append(mock_doc)
    
    with patch('database.firebase_db.get_firestore_db') as mock_db, \
         patch('database.firebase_db.firestore') as mock_firestore:
        # Configura o mock para retornar a lista de documentos
        mock_filter = MagicMock()
        mock_db.return_value.collection().where.return_value = mock_filter
        mock_filter.order_by().limit.return_value.stream.return_value = mock_docs
        
        # Executa a função
        messages, last_doc_id = get_messages_with_pagination(conversation_id, limit=5)
        
        # Verifica o resultado
        assert len(messages) == 5
        assert all('id' in msg for msg in messages)
        assert last_doc_id == 'message_4'  # Último documento
        
        # Verifica que os métodos foram chamados corretamente
        mock_db.return_value.collection.assert_called_once_with('mensagens')
        mock_db.return_value.collection().where.assert_called_once()

if __name__ == '__main__':
    unittest.main() 