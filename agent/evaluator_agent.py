import os
import json
import time
import datetime
import re
from typing import Dict, Any, List, Optional, Tuple
import threading
from queue import Queue
from loguru import logger
from dotenv import load_dotenv
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
import sqlalchemy.orm
import pytz

from database import (
    get_session, 
    Conversa, 
    Mensagem, 
    Solicitacao, 
    Avaliacao,
    ConsolidadaAtendimento,
    ConversaStatus,
    SolicitacaoStatus,
    AvaliacaoStatus
)
from ai import ConversationProcessor
from agent.priority_manager import PriorityManager

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
VERIFICATION_INTERVAL_MINUTES = int(os.getenv("VERIFICATION_INTERVAL_MINUTES", "10"))
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

@contextmanager
def safe_db_session():
    """Context manager para gerenciar sessões do banco de dados com tratamento de erros."""
    session = None
    try:
        session = get_session()
        yield session
        session.commit()
    except SQLAlchemyError as e:
        if session:
            session.rollback()
        logger.error(f"Erro na sessão do banco de dados: {e}")
        raise
    finally:
        if session:
            session.close()

class EvaluatorAgent:
    """
    Agente 2 (Avaliador): responsável por avaliar a qualidade do atendimento
    com base nas conversas coletadas pelo Agente 1.
    """
    
    def __init__(self):
        """
        Inicializa o agente avaliador.
        """
        self.conversation_processor = ConversationProcessor()
        self.priority_manager = PriorityManager()
        
        # Fila para processamento assíncrono de avaliações
        self._evaluation_queue = Queue()
        
        # Registra thread de processamento
        self._processing_thread = None
        self._running = False
        
        # Thread para verificação periódica de conversas a serem avaliadas
        self._verification_thread = None
        
        self._evaluation_locks = {}  # Dicionário para armazenar locks por conversa
        self._lock = threading.Lock()  # Lock para operações no dicionário de locks
        self._evaluation_timeout = 300  # 5 minutos em segundos
        self._evaluation_start_times = {}  # Dicionário para armazenar tempos de início
        self._failed_evaluations = {}  # Dicionário para armazenar tentativas falhas
        self._max_retries = 3  # Número máximo de tentativas
        self._retry_delay = 60  # Delay entre tentativas em segundos
        
        logger.info("Agente Avaliador inicializado")
    
    def start(self):
        """
        Inicia o agente avaliador.
        """
        if self._running:
            logger.warning("Agente Avaliador já está em execução")
            return
        
        self._running = True
        
        # Iniciar thread de processamento de avaliações
        self._processing_thread = threading.Thread(
            target=self._process_evaluation_queue, 
            daemon=True
        )
        self._processing_thread.start()
        
        # Iniciar thread de verificação periódica
        self._verification_thread = threading.Thread(
            target=self._periodic_verification,
            daemon=True
        )
        self._verification_thread.start()
        
        logger.info("Agente Avaliador iniciado")
    
    def stop(self):
        """
        Para o agente avaliador.
        """
        if not self._running:
            logger.warning("Agente Avaliador não está em execução")
            return
        
        self._running = False
        
        if self._processing_thread:
            self._processing_thread.join(timeout=10)
        
        if self._verification_thread:
            self._verification_thread.join(timeout=10)
        
        logger.info("Agente Avaliador parado")
    
    def evaluate_conversation(self, conversa_id: int):
        """
        Adiciona uma conversa à fila para avaliação.
        
        Args:
            conversa_id: ID da conversa a ser avaliada
        """
        self._evaluation_queue.put(conversa_id)
        logger.info(f"Conversa {conversa_id} adicionada à fila de avaliação")
    
    def _periodic_verification(self):
        """
        Executa verificações periódicas de conversas e solicitações.
        """
        while self._running:
            try:
                # Verificar timeouts
                self._check_evaluation_timeouts()
                
                # Verificar conversas encerradas não avaliadas
                self._check_for_pending_evaluations()
                
                # Verificar solicitações pendentes e prazos
                self._check_pending_requests()
                
                # Verificar conversas reabertas
                self._check_reopened_conversations()
                
                # Aguardar até o próximo intervalo
                for _ in range(VERIFICATION_INTERVAL_MINUTES * 60):
                    if not self._running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro na verificação periódica: {e}")
                time.sleep(60)  # Esperar 1 minuto em caso de erro
    
    def _check_for_pending_evaluations(self):
        """
        Verifica se há conversas encerradas que ainda não foram avaliadas.
        """
        with safe_db_session() as session:
            try:
                # Buscar conversas encerradas sem avaliação
                conversas = session.query(Conversa).filter(
                    Conversa.status == ConversaStatus.FECHADA,
                    ~Conversa.avaliacoes.any()
                ).options(
                    sqlalchemy.orm.joinedload(Conversa.mensagens),
                    sqlalchemy.orm.joinedload(Conversa.solicitacoes)
                ).all()
                
                # Converter conversas para formato de dicionário
                conversas_data = []
                for conversa in conversas:
                    conversa_data = {
                        'id': conversa.conversa_id,
                        'start_time': conversa.data_inicio,
                        'messages': [
                            {
                                'role': 'client' if msg.remetente == 'cliente' else 'atendente',
                                'content': msg.conteudo,
                                'timestamp': msg.data_hora
                            }
                            for msg in conversa.mensagens
                        ],
                        'request_type': conversa.solicitacoes[0].tipo if conversa.solicitacoes else 'informação',
                        'reopen_count': conversa.quantidade_reaberturas
                    }
                    conversas_data.append(conversa_data)
                
                # Ordenar conversas por prioridade
                conversas_ordenadas = self.priority_manager.sort_conversations_by_priority(conversas_data)
                
                # Adicionar à fila na ordem de prioridade
                for conversa in conversas_ordenadas:
                    lock = self._get_conversation_lock(conversa['id'])
                    if not lock.locked():
                        self._evaluation_queue.put(conversa['id'])
                        logger.info(f"Conversa {conversa['id']} adicionada à fila de avaliação")
                        
            except SQLAlchemyError as e:
                logger.error(f"Erro ao verificar avaliações pendentes: {e}")
    
    def _check_pending_requests(self):
        """
        Verifica solicitações pendentes e atualiza status com base nos prazos.
        """
        with safe_db_session() as session:
            try:
                # Buscar solicitações pendentes
                solicitacoes = session.query(Solicitacao).filter(
                    Solicitacao.status == SolicitacaoStatus.PENDENTE
                ).all()
                
                now = datetime.datetime.now()
                
                for solicitacao in solicitacoes:
                    if solicitacao.prazo_prometido and solicitacao.prazo_prometido < now:
                        # Prazo expirado, marcar como atrasada
                        solicitacao.status = SolicitacaoStatus.ATRASADA
                        
                        # Verificar se a conversa relacionada tem avaliação
                        avaliacao = session.query(Avaliacao).filter(
                            Avaliacao.conversa_id == solicitacao.conversa_id
                        ).first()
                        
                        if avaliacao and avaliacao.status_avaliacao != AvaliacaoStatus.NAO_AVALIADA:
                            # Marcar para reavaliação
                            avaliacao.status_avaliacao = AvaliacaoStatus.PENDENTE_REVISAO
                            self.evaluate_conversation(solicitacao.conversa_id)
                
                session.commit()
                
            except SQLAlchemyError as e:
                logger.error(f"Erro ao verificar solicitações pendentes: {e}")
                session.rollback()
    
    def _check_reopened_conversations(self):
        """
        Verifica conversas que foram reabertas e atualiza suas avaliações.
        """
        with safe_db_session() as session:
            try:
                # Buscar conversas reabertas
                conversas = session.query(Conversa).filter(
                    Conversa.status == ConversaStatus.ABERTA,
                    Conversa.quantidade_reaberturas > 0
                ).options(
                    sqlalchemy.orm.joinedload(Conversa.avaliacoes)
                ).all()
                
                for conversa in conversas:
                    # Verificar se já existe avaliação
                    avaliacao = conversa.avaliacoes[0] if conversa.avaliacoes else None
                    
                    if avaliacao and avaliacao.status_avaliacao != AvaliacaoStatus.NAO_AVALIADA:
                        # Marcar para reavaliação
                        avaliacao.status_avaliacao = AvaliacaoStatus.REAVALIACAO_PENDENTE
                        self.evaluate_conversation(conversa.conversa_id)
                        
            except SQLAlchemyError as e:
                logger.error(f"Erro ao verificar conversas reabertas: {e}")
    
    def _process_evaluation_queue(self):
        """
        Processa a fila de avaliações de forma assíncrona.
        """
        while self._running:
            try:
                # Obter próxima conversa da fila
                conversa_id = self._evaluation_queue.get(timeout=1)
                
                # Verificar se a conversa já está sendo avaliada
                lock = self._get_conversation_lock(conversa_id)
                if lock.locked():
                    logger.warning(f"Conversa {conversa_id} já está sendo avaliada")
                    self._evaluation_queue.put(conversa_id)  # Recolocar na fila
                    continue
                
                # Adquirir lock e registrar tempo de início
                with lock:
                    self._evaluation_start_times[conversa_id] = time.time()
                    
                    try:
                        # Avaliar a conversa
                        self._evaluate_conversation(conversa_id)
                        
                        # Limpar registros de falhas se houver sucesso
                        if conversa_id in self._failed_evaluations:
                            del self._failed_evaluations[conversa_id]
                            
                    except Exception as e:
                        logger.error(f"Erro ao avaliar conversa {conversa_id}: {e}")
                        
                        # Registrar falha
                        if conversa_id not in self._failed_evaluations:
                            self._failed_evaluations[conversa_id] = 0
                        self._failed_evaluations[conversa_id] += 1
                        
                        # Recolocar na fila se ainda houver tentativas
                        if self._failed_evaluations[conversa_id] < self._max_retries:
                            time.sleep(self._retry_delay)
                            self._evaluation_queue.put(conversa_id)
                        else:
                            logger.error(f"Conversa {conversa_id} falhou após {self._max_retries} tentativas")
                            
                    finally:
                        # Limpar registros
                        if conversa_id in self._evaluation_start_times:
                            del self._evaluation_start_times[conversa_id]
                            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no processamento da fila: {e}")
                time.sleep(1)
    
    def _evaluate_conversation(self, conversa_id: int):
        """
        Avalia uma conversa específica e atualiza suas métricas.
        
        Args:
            conversa_id: ID da conversa a ser avaliada
        """
        with safe_db_session() as session:
            try:
                # Buscar conversa e suas mensagens
                conversa = session.query(Conversa).filter(
                    Conversa.conversa_id == conversa_id
                ).options(
                    sqlalchemy.orm.joinedload(Conversa.mensagens),
                    sqlalchemy.orm.joinedload(Conversa.solicitacoes)
                ).first()
                
                if not conversa:
                    logger.error(f"Conversa {conversa_id} não encontrada")
                    return
                
                # Buscar ou criar avaliação
                avaliacao = session.query(Avaliacao).filter(
                    Avaliacao.conversa_id == conversa_id
                ).first()
                
                if not avaliacao:
                    avaliacao = Avaliacao(conversa_id=conversa_id)
                    session.add(avaliacao)
                
                # Processar mensagens
                mensagens = conversa.mensagens
                if not mensagens:
                    logger.warning(f"Conversa {conversa_id} não possui mensagens")
                    return
                
                # Calcular métricas
                tempo_resposta = self._calculate_response_time(mensagens)
                qualidade_resposta = self._analyze_response_quality(mensagens)
                satisfacao_cliente = self._analyze_customer_satisfaction(mensagens)
                
                # Atualizar avaliação
                avaliacao.tempo_resposta = tempo_resposta
                avaliacao.qualidade_resposta = qualidade_resposta
                avaliacao.satisfacao_cliente = satisfacao_cliente
                avaliacao.status_avaliacao = AvaliacaoStatus.AVALIADA
                
                # Atualizar métricas consolidadas
                self._update_consolidated_metrics(conversa, avaliacao)
                
                logger.info(f"Conversa {conversa_id} avaliada com sucesso")
                
            except SQLAlchemyError as e:
                logger.error(f"Erro ao avaliar conversa {conversa_id}: {e}")
                raise
    
    def _calculate_response_time(self, mensagens: List[Mensagem]) -> float:
        """
        Calcula o tempo médio de resposta do atendente.
        
        Args:
            mensagens: Lista de mensagens da conversa
            
        Returns:
            Tempo médio de resposta em segundos
        """
        tempos_resposta = []
        ultima_mensagem_cliente = None
        
        for msg in sorted(mensagens, key=lambda x: x.data_hora):
            if msg.remetente == 'cliente':
                ultima_mensagem_cliente = msg
            elif msg.remetente == 'atendente' and ultima_mensagem_cliente:
                tempo = (msg.data_hora - ultima_mensagem_cliente.data_hora).total_seconds()
                tempos_resposta.append(tempo)
                ultima_mensagem_cliente = None
        
        return sum(tempos_resposta) / len(tempos_resposta) if tempos_resposta else 0
    
    def _analyze_response_quality(self, mensagens: List[Mensagem]) -> float:
        """
        Analisa a qualidade das respostas do atendente.
        
        Args:
            mensagens: Lista de mensagens da conversa
            
        Returns:
            Score de qualidade entre 0 e 1
        """
        scores = []
        
        for msg in mensagens:
            if msg.remetente == 'atendente':
                score = self.conversation_processor.analyze_response_quality({
                    'content': msg.conteudo,
                    'role': 'attendant'
                })
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def _analyze_customer_satisfaction(self, mensagens: List[Mensagem]) -> float:
        """
        Analisa o nível de satisfação do cliente.
        
        Args:
            mensagens: Lista de mensagens da conversa
            
        Returns:
            Score de satisfação entre 0 e 1
        """
        scores = []
        
        for msg in mensagens:
            if msg.remetente == 'cliente':
                score = self.conversation_processor.detect_sentiment(msg.conteudo)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _update_consolidated_metrics(self, conversa: Conversa, avaliacao: Avaliacao):
        """
        Atualiza as métricas consolidadas do atendimento.
        
        Args:
            conversa: Objeto da conversa
            avaliacao: Objeto da avaliação
        """
        with safe_db_session() as session:
            try:
                # Buscar ou criar métricas consolidadas
                consolidada = session.query(ConsolidadaAtendimento).filter(
                    ConsolidadaAtendimento.conversa_id == conversa.conversa_id
                ).first()
                
                if not consolidada:
                    consolidada = ConsolidadaAtendimento(conversa_id=conversa.conversa_id)
                    session.add(consolidada)
                
                # Atualizar métricas
                consolidada.tempo_medio_resposta = avaliacao.tempo_resposta
                consolidada.qualidade_atendimento = avaliacao.qualidade_resposta
                consolidada.satisfacao_cliente = avaliacao.satisfacao_cliente
                consolidada.quantidade_reaberturas = conversa.quantidade_reaberturas
                
                # Calcular NPS
                consolidada.nps = self._calculate_nps(avaliacao.satisfacao_cliente)
                
            except SQLAlchemyError as e:
                logger.error(f"Erro ao atualizar métricas consolidadas: {e}")
                raise
    
    def _calculate_nps(self, satisfacao: float) -> int:
        """
        Calcula o NPS (Net Promoter Score) baseado na satisfação do cliente.
        
        Args:
            satisfacao: Score de satisfação entre 0 e 1
            
        Returns:
            NPS entre 0 e 10
        """
        # Converter satisfação (0-1) para NPS (0-10)
        return int(satisfacao * 10)
    
    def _get_conversation_lock(self, conversa_id: int) -> threading.Lock:
        """
        Obtém ou cria um lock para uma conversa específica.
        
        Args:
            conversa_id: ID da conversa
            
        Returns:
            Lock da conversa
        """
        with self._lock:
            if conversa_id not in self._evaluation_locks:
                self._evaluation_locks[conversa_id] = threading.Lock()
            return self._evaluation_locks[conversa_id]
    
    def _check_evaluation_timeouts(self):
        """
        Verifica e limpa avaliações que excederam o tempo limite.
        """
        now = time.time()
        with self._lock:
            for conversa_id, start_time in list(self._evaluation_start_times.items()):
                if now - start_time > self._evaluation_timeout:
                    logger.warning(f"Timeout na avaliação da conversa {conversa_id}")
                    if conversa_id in self._evaluation_locks:
                        del self._evaluation_locks[conversa_id]
                    if conversa_id in self._evaluation_start_times:
                        del self._evaluation_start_times[conversa_id]

def get_evaluator_agent():
    """
    Retorna a instância global do agente avaliador.
    
    Returns:
        Instância do agente avaliador
    """
    global _evaluator_agent
    if not hasattr(get_evaluator_agent, '_evaluator_agent'):
        get_evaluator_agent._evaluator_agent = EvaluatorAgent()
    return get_evaluator_agent._evaluator_agent 