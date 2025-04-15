import pytest
from datetime import datetime, timedelta
import sqlite3
import os

# Mock das classes de modelo para testes
class ConversaStatus:
    ATIVA = "ativa"
    ENCERRADA = "encerrada"
    AGUARDANDO = "aguardando"

class SolicitacaoStatus:
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    ATRASADA = "atrasada"

class AvaliacaoStatus:
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"

class TestDatabase:
    """Testes para o módulo de banco de dados"""
    
    @pytest.fixture
    def db_conn(self):
        """Configuração do banco de dados para testes"""
        # Criar banco de dados em memória
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Criar tabelas
        cursor.execute('''
        CREATE TABLE conversa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            attendant_name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            status TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE mensagem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (conversa_id) REFERENCES conversa (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE solicitacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline TIMESTAMP,
            FOREIGN KEY (conversa_id) REFERENCES conversa (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE avaliacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            client_complaint TEXT,
            FOREIGN KEY (conversa_id) REFERENCES conversa (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE consolidada_atendimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversa_id INTEGER NOT NULL,
            total_messages INTEGER NOT NULL,
            avg_response_time INTEGER,
            has_complaint BOOLEAN NOT NULL,
            FOREIGN KEY (conversa_id) REFERENCES conversa (id)
        )
        ''')
        
        conn.commit()
        
        yield conn
        
        conn.close()
    
    def test_conversa_creation(self, db_conn):
        """Testa a criação de uma conversa"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        db_conn.commit()
        
        # Verificar se a conversa foi criada
        cursor.execute('SELECT * FROM conversa WHERE client_name = ?', ("João Silva",))
        conversa = cursor.fetchone()
        
        assert conversa is not None
        assert conversa[1] == "João Silva"
        assert conversa[5] == ConversaStatus.ATIVA
    
    def test_mensagem_creation(self, db_conn):
        """Testa a criação de uma mensagem"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        conversa_id = cursor.lastrowid
        
        # Inserir mensagem
        cursor.execute('''
        INSERT INTO mensagem (conversa_id, sender, content, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (conversa_id, "client", "Bom dia, preciso de ajuda", datetime.now()))
        
        db_conn.commit()
        
        # Verificar se a mensagem foi criada
        cursor.execute('SELECT * FROM mensagem WHERE conversa_id = ?', (conversa_id,))
        mensagem = cursor.fetchone()
        
        assert mensagem is not None
        assert mensagem[1] == conversa_id
        assert mensagem[2] == "client"
    
    def test_solicitacao_creation(self, db_conn):
        """Testa a criação de uma solicitação"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        conversa_id = cursor.lastrowid
        
        # Inserir solicitação
        cursor.execute('''
        INSERT INTO solicitacao (conversa_id, description, status, deadline)
        VALUES (?, ?, ?, ?)
        ''', (conversa_id, "Preciso de um orçamento", SolicitacaoStatus.PENDENTE, 
              datetime.now() + timedelta(days=2)))
        
        db_conn.commit()
        
        # Verificar se a solicitação foi criada
        cursor.execute('SELECT * FROM solicitacao WHERE conversa_id = ?', (conversa_id,))
        solicitacao = cursor.fetchone()
        
        assert solicitacao is not None
        assert solicitacao[1] == conversa_id
        assert solicitacao[3] == SolicitacaoStatus.PENDENTE
    
    def test_avaliacao_creation(self, db_conn):
        """Testa a criação de uma avaliação"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        conversa_id = cursor.lastrowid
        
        # Inserir avaliação
        cursor.execute('''
        INSERT INTO avaliacao (conversa_id, status, client_complaint)
        VALUES (?, ?, ?)
        ''', (conversa_id, AvaliacaoStatus.PENDENTE, "Demorou muito para responder"))
        
        db_conn.commit()
        
        # Verificar se a avaliação foi criada
        cursor.execute('SELECT * FROM avaliacao WHERE conversa_id = ?', (conversa_id,))
        avaliacao = cursor.fetchone()
        
        assert avaliacao is not None
        assert avaliacao[1] == conversa_id
        assert avaliacao[2] == AvaliacaoStatus.PENDENTE
    
    def test_consolidada_creation(self, db_conn):
        """Testa a criação de um registro consolidado"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        conversa_id = cursor.lastrowid
        
        # Inserir consolidada
        cursor.execute('''
        INSERT INTO consolidada_atendimento (conversa_id, total_messages, avg_response_time, has_complaint)
        VALUES (?, ?, ?, ?)
        ''', (conversa_id, 10, 120, True))
        
        db_conn.commit()
        
        # Verificar se a consolidada foi criada
        cursor.execute('SELECT * FROM consolidada_atendimento WHERE conversa_id = ?', (conversa_id,))
        consolidada = cursor.fetchone()
        
        assert consolidada is not None
        assert consolidada[1] == conversa_id
        assert consolidada[2] == 10
    
    def test_relationships(self, db_conn):
        """Testa os relacionamentos entre as tabelas"""
        cursor = db_conn.cursor()
        
        # Inserir conversa
        cursor.execute('''
        INSERT INTO conversa (client_name, attendant_name, start_time, status)
        VALUES (?, ?, ?, ?)
        ''', ("João Silva", "Maria Santos", datetime.now(), ConversaStatus.ATIVA))
        
        conversa_id = cursor.lastrowid
        
        # Inserir mensagem
        cursor.execute('''
        INSERT INTO mensagem (conversa_id, sender, content, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (conversa_id, "client", "Bom dia", datetime.now()))
        
        # Inserir solicitação
        cursor.execute('''
        INSERT INTO solicitacao (conversa_id, description, status)
        VALUES (?, ?, ?)
        ''', (conversa_id, "Orçamento", SolicitacaoStatus.PENDENTE))
        
        # Inserir avaliação
        cursor.execute('''
        INSERT INTO avaliacao (conversa_id, status)
        VALUES (?, ?)
        ''', (conversa_id, AvaliacaoStatus.PENDENTE))
        
        # Inserir consolidada
        cursor.execute('''
        INSERT INTO consolidada_atendimento (conversa_id, total_messages, has_complaint)
        VALUES (?, ?, ?)
        ''', (conversa_id, 1, False))
        
        db_conn.commit()
        
        # Verificar relacionamentos
        cursor.execute('SELECT COUNT(*) FROM mensagem WHERE conversa_id = ?', (conversa_id,))
        count_mensagens = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM solicitacao WHERE conversa_id = ?', (conversa_id,))
        count_solicitacoes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM avaliacao WHERE conversa_id = ?', (conversa_id,))
        count_avaliacoes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM consolidada_atendimento WHERE conversa_id = ?', (conversa_id,))
        count_consolidadas = cursor.fetchone()[0]
        
        assert count_mensagens == 1
        assert count_solicitacoes == 1
        assert count_avaliacoes == 1
        assert count_consolidadas == 1 