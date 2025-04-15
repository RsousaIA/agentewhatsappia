from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class ConversaStatus(enum.Enum):
    ATIVO = "ativo"
    FINALIZADO = "finalizado"
    REABERTO = "reaberto"

class SolicitacaoStatus(enum.Enum):
    PENDENTE = "pendente"
    ATENDIDA = "atendida"
    ATRASADA = "atrasada"
    NAO_ATENDIDA = "nao_atendida"

class AvaliacaoStatus(enum.Enum):
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    ATUALIZADA = "atualizada"

class Conversa(Base):
    __tablename__ = 'conversas'
    
    id = Column(Integer, primary_key=True)
    cliente_nome = Column(String(100))
    cliente_telefone = Column(String(20), index=True)
    atendente_nome = Column(String(100))
    data_inicio = Column(DateTime, default=datetime.utcnow)
    data_fim = Column(DateTime, nullable=True)
    tempo_total = Column(Float, nullable=True)  # em segundos
    tempo_resposta_maximo = Column(Float, nullable=True)  # em segundos
    tempo_resposta_medio = Column(Float, nullable=True)  # em segundos
    status = Column(Enum(ConversaStatus), default=ConversaStatus.ATIVO)
    conteudo_json = Column(Text, nullable=True)  # JSON da conversa completa
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    mensagens = relationship("Mensagem", back_populates="conversa", cascade="all, delete-orphan")
    solicitacoes = relationship("Solicitacao", back_populates="conversa", cascade="all, delete-orphan")
    avaliacao = relationship("Avaliacao", back_populates="conversa", uselist=False, cascade="all, delete-orphan")
    consolidado = relationship("ConsolidadaAtendimento", back_populates="conversa", uselist=False, cascade="all, delete-orphan")

class Mensagem(Base):
    __tablename__ = 'mensagens'
    
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id'), index=True)
    remetente_tipo = Column(String(20))  # 'cliente' ou 'atendente'
    remetente_nome = Column(String(100))
    data_hora = Column(DateTime, default=datetime.utcnow)
    conteudo = Column(Text)
    tipo_mensagem = Column(String(20), default='texto')  # texto, imagem, áudio, etc.
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="mensagens")
    solicitacoes = relationship("Solicitacao", back_populates="mensagem", cascade="all, delete-orphan")

class Solicitacao(Base):
    __tablename__ = 'solicitacoes'
    
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id'), index=True)
    mensagem_id = Column(Integer, ForeignKey('mensagens.id'), index=True)
    descricao = Column(Text)
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    prazo_prometido = Column(DateTime, nullable=True)
    status = Column(Enum(SolicitacaoStatus), default=SolicitacaoStatus.PENDENTE)
    dias_uteis_prometidos = Column(Integer, nullable=True)
    atendente_nome = Column(String(100))
    data_atendimento = Column(DateTime, nullable=True)
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="solicitacoes")
    mensagem = relationship("Mensagem", back_populates="solicitacoes")

class Avaliacao(Base):
    __tablename__ = 'avaliacoes'
    
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id'), unique=True)
    clareza_comunicacao = Column(Integer)  # 0-10
    conhecimento_tecnico = Column(Integer)  # 0-10
    paciencia = Column(Integer)  # 0-10
    profissionalismo = Column(Integer)  # 0-10
    inteligencia_emocional = Column(Integer)  # 0-10
    nota_final = Column(Float)  # Média ponderada
    reclamacao_cliente = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    solicitacoes_nao_atendidas = Column(Integer, default=0)
    solicitacoes_atrasadas = Column(Integer, default=0)
    cumprimento_prazos = Column(Integer, default=10)  # 0-10
    status = Column(Enum(AvaliacaoStatus), default=AvaliacaoStatus.PENDENTE)
    data_avaliacao = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="avaliacao")

class ConsolidadaAtendimento(Base):
    __tablename__ = 'consolidada_atendimentos'
    
    id = Column(Integer, primary_key=True)
    conversa_id = Column(Integer, ForeignKey('conversas.id'), unique=True)
    cliente_nome = Column(String(100))
    cliente_telefone = Column(String(20))
    atendente_nome = Column(String(100))
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime, nullable=True)
    tempo_total = Column(Float, nullable=True)  # em segundos
    tempo_resposta_maximo = Column(Float, nullable=True)  # em segundos
    tempo_resposta_medio = Column(Float, nullable=True)  # em segundos
    quantidade_mensagens = Column(Integer, default=0)
    quantidade_solicitacoes = Column(Integer, default=0)
    solicitacoes_atendidas = Column(Integer, default=0)
    solicitacoes_nao_atendidas = Column(Integer, default=0)
    solicitacoes_atrasadas = Column(Integer, default=0)
    nota_final = Column(Float, nullable=True)
    status_conversa = Column(String(20))
    status_avaliacao = Column(String(20), default=AvaliacaoStatus.PENDENTE.value)
    
    # Relacionamentos
    conversa = relationship("Conversa", back_populates="consolidado") 