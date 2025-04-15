import os
import json
import time
import datetime
import threading
import pytz
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
from dotenv import load_dotenv
from queue import Queue
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import object_session

# Carrega variáveis de ambiente
load_dotenv()

# Importa os modelos do banco de dados
from database.models import Conversa, Mensagem, Solicitacao, ConversaStatus, SolicitacaoStatus
from database.db import init_db, get_db
from whatsapp import whatsapp_client
from ai.conversation_processor import ConversationProcessor
from utils.date_utils import get_current_time, is_business_day, add_business_days, calculate_business_days_between

# Configurações
INACTIVITY_TIMEOUT = int(os.getenv("INACTIVITY_TIMEOUT", "21600"))  # 6 horas em segundos
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

@contextmanager
def safe_db_session():
    """Context manager para gerenciar sessões do banco de dados com tratamento de erros."""
    session = None
    try:
        session = get_db()
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

class CollectorAgent:
    """
    Agente 1 (Coletor): responsável por monitorar e coletar mensagens do WhatsApp,
    processar o conteúdo e armazenar no banco de dados.
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Inicializa o agente coletor.
        
        Args:
            db_url: URL de conexão com o banco de dados (opcional, usa variável de ambiente se não informado)
        """
        logger.info("Inicializando Agente Coletor...")
        
        # Inicializar banco de dados
        try:
            init_db()
            logger.info("Banco de dados inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise
        
        # Configuração da zona de tempo
        self.timezone = os.getenv("TIMEZONE", "America/Sao_Paulo")
        self.tz = pytz.timezone(self.timezone)
        
        # Usar cliente global do WhatsApp Node.js
        self.whatsapp_client = whatsapp_client
        logger.info("Cliente WhatsApp Node.js inicializado")
        
        # Inicializar processador de conversas
        self.conversation_processor = ConversationProcessor()
        logger.info("Processador de conversas inicializado")
        
        # Configurações do monitoramento
        self.check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
        self.inactive_threshold_hours = int(os.getenv("INACTIVE_THRESHOLD_HOURS", "6"))
        self.update_metrics_interval = int(os.getenv("UPDATE_METRICS_INTERVAL_MINUTES", "30"))
        
        # Estado do agente
        self.is_running = False
        self.monitor_thread = None
        self.metrics_thread = None
        self.last_check_time = datetime.datetime.now()
        
        # Fila para processamento assíncrono de mensagens
        self._message_queue = Queue()
        
        # Registra threads
        self._processing_thread = None
        self._monitoring_thread = None
        
        # Dicionário para armazenar locks por conversa
        self._conversation_locks = {}
        self._lock = threading.Lock()
        
        # Cache de conversas ativas
        self._active_conversations = set()
        
        logger.info("Agente Coletor inicializado com sucesso")
        
    def start(self):
        """
        Inicia o agente de monitoramento de mensagens.
        """
        if self.is_running:
            logger.warning("Agente Coletor já está em execução")
            return
            
        self.is_running = True
        
        # Iniciar cliente do WhatsApp
        try:
            self.whatsapp_client.start(message_callback=self._handle_whatsapp_message)
            logger.info("Cliente WhatsApp iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar cliente WhatsApp: {e}")
            self.is_running = False
            raise
        
        # Iniciar thread de processamento
        self._processing_thread = threading.Thread(
            target=self._process_message_queue,
            daemon=True
        )
        self._processing_thread.start()
        
        # Iniciar thread de monitoramento
        self._monitoring_thread = threading.Thread(
            target=self._monitor_conversations,
            daemon=True
        )
        self._monitoring_thread.start()
        
        # Iniciar thread de atualização de métricas
        self.metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self.metrics_thread.start()
        logger.info("Thread de métricas iniciada")
        
        logger.info("Agente Coletor iniciado com sucesso")
    
    def stop(self):
        """
        Para o agente de monitoramento.
        """
        if not self.is_running:
            logger.warning("Agente Coletor não está em execução")
            return
            
        self.is_running = False
        
        # Parar cliente do WhatsApp
        try:
            self.whatsapp_client.stop()
            logger.info("Cliente WhatsApp parado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao parar cliente WhatsApp: {e}")
        
        # Aguardar término das threads
        if self._processing_thread:
            self._processing_thread.join(timeout=10)
        
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=10)
        
        if self.metrics_thread:
            self.metrics_thread.join(timeout=10)
            self.metrics_thread = None
            
        logger.info("Agente Coletor parado com sucesso")
    
    def _handle_whatsapp_message(self, message_data: Dict[str, Any]):
        """
        Callback para processar mensagens recebidas do WhatsApp.
        
        Args:
            message_data: Dados da mensagem recebida
        """
        # Log da mensagem recebida
        logger.info(f"Mensagem recebida: {message_data.get('id')} de {message_data.get('from')}")
        
        # Adicionar mensagem à fila de processamento
        self._message_queue.put(message_data)
        logger.debug(f"Mensagem adicionada à fila: {message_data.get('id')}")
    
    def _process_message_queue(self):
        """
        Processa a fila de mensagens.
        """
        while self.is_running:
            try:
                # Tentar obter mensagem da fila
                try:
                    message_data = self._message_queue.get(timeout=1)
                except Queue.Empty:
                    continue
                
                if message_data is None:
                    continue
                
                # Processar mensagem
                logger.info(f"Processando mensagem {message_data.get('id')} da fila")
                self._process_message(message_data)
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem da fila: {e}")
                time.sleep(1)
    
    def _process_message(self, message_data: Dict[str, Any]):
        """
        Processa uma mensagem individual.
        
        Args:
            message_data: Dados da mensagem
        """
        try:
            with safe_db_session() as session:
                # Extrair dados da mensagem
                message_id = message_data.get('id')
                from_number = message_data.get('from').split('@')[0]
                to_number = message_data.get('to', '').split('@')[0] if message_data.get('to') else ''
                body = message_data.get('body', '')
                timestamp = datetime.datetime.fromtimestamp(message_data.get('timestamp', time.time()))
                msg_type = message_data.get('type', 'text')
                
                # Determinar remetente (cliente ou atendente)
                is_from_client = message_data.get('from') != message_data.get('to')
                remetente = "cliente" if is_from_client else "atendente"
                
                # Identificar ou criar conversa
                conversa = self._get_or_create_conversation(session, message_data)
                
                # Verificar se mensagem já existe (evitar duplicatas)
                existing_msg = session.query(Mensagem).filter_by(
                    message_id=message_id
                ).first()
                
                if existing_msg:
                    logger.warning(f"Mensagem {message_id} já existe no banco de dados. Ignorando.")
                    return
                
                # Criar mensagem
                mensagem = Mensagem(
                    conversa_id=conversa.id,
                    message_id=message_id,
                    remetente_tipo=remetente,
                    remetente_nome=conversa.cliente_nome if remetente == "cliente" else conversa.atendente_nome,
                    data_hora=timestamp,
                    conteudo=body,
                    tipo_mensagem=msg_type
                )
                session.add(mensagem)
                session.flush()  # Obter ID
                
                # Atualizar metadados da conversa
                self._update_conversation_metadata(conversa, mensagem)
                
                # Detectar solicitações do cliente
                if remetente == "cliente":
                    self._detect_and_create_request(session, conversa, mensagem)
                else:
                    # Verificar se é resposta a alguma solicitação
                    self._check_request_fulfillment(session, conversa, mensagem)
                
                # Verificar se conversa deve ser encerrada
                if self._should_close_conversation(conversa):
                    conversa.status = ConversaStatus.FINALIZADO
                    logger.info(f"Conversa {conversa.id} encerrada por inatividade")
                
                # Marcar como lida (se for mensagem do cliente)
                if remetente == "cliente":
                    try:
                        self.whatsapp_client.mark_messages_as_read([message_id])
                    except Exception as e:
                        logger.error(f"Erro ao marcar mensagem como lida: {e}")
                
                session.commit()
                logger.info(f"Mensagem {message_id} processada e armazenada com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {message_data.get('id')}: {e}", exc_info=True)
    
    def _get_or_create_conversation(self, session, message_data):
        """
        Busca ou cria uma conversa para a mensagem recebida.
        
        Args:
            session: Sessão do banco de dados
            message_data: Dados da mensagem recebida
            
        Returns:
            Conversa: Conversa existente ou nova conversa
        """
        # Determinar o número do telefone do cliente
        if message_data.get('fromMe', False):
            # Mensagem enviada pelo agente, o destinatário é o cliente
            cliente_telefone = message_data.get('to', '')
        else:
            # Mensagem recebida pelo cliente, o remetente é o cliente
            cliente_telefone = message_data.get('from', '')
        
        # Normalizar número de telefone (remover prefixo 'whatsapp:' se presente)
        if 'whatsapp:' in cliente_telefone:
            cliente_telefone = cliente_telefone.replace('whatsapp:', '')
        
        # Buscar conversa ativa existente com este cliente
        conversa = session.query(Conversa).filter(
            Conversa.cliente_telefone == cliente_telefone,
            Conversa.status == 'ativo'
        ).order_by(Conversa.ultima_atualizacao.desc()).first()
        
        # Se não encontrar conversa ativa, verificar se há uma finalizada recentemente
        # que pode ser reaberta (últimas 24h)
        if not conversa:
            limite_tempo = datetime.datetime.now() - datetime.timedelta(hours=24)
            conversa = session.query(Conversa).filter(
                Conversa.cliente_telefone == cliente_telefone,
                Conversa.status == 'finalizado',
                Conversa.ultima_atualizacao >= limite_tempo
            ).order_by(Conversa.ultima_atualizacao.desc()).first()
            
            if conversa:
                # Reabrir conversa recente
                conversa.status = 'ativo'
                conversa.possivel_finalizacao = False
                self.logger.info(f"Reabrindo conversa recente: ID {conversa.id}")
        
        # Se ainda não encontrou, criar nova conversa
        if not conversa:
            conversa = Conversa(
                cliente_telefone=cliente_telefone,
                status='ativo',
                data_inicio=datetime.datetime.now(),
                ultima_atualizacao=datetime.datetime.now()
            )
            session.add(conversa)
            session.flush()  # Para obter o ID gerado
            self.logger.info(f"Nova conversa criada: ID {conversa.id}")
        
        return conversa
    
    def _update_conversation_metadata(self, conversa, message_data):
        """
        Atualiza os metadados da conversa com base na nova mensagem.
        
        Args:
            conversa: Objeto da conversa a ser atualizada
            message_data: Dados da nova mensagem
        """
        from sqlalchemy.orm import object_session
        
        # Atualizar timestamp da última atualização
        conversa.ultima_atualizacao = datetime.datetime.now()
        
        # Identificar nomes do atendente e cliente se ainda não definidos
        if message_data.get('fromMe', False) and not conversa.atendente_nome:
            # Mensagem do atendente
            atendente_nome = message_data.get('senderName', '')
            if atendente_nome:
                conversa.atendente_nome = atendente_nome
                self.logger.info(f"Atendente identificado: {atendente_nome}")
        
        if not message_data.get('fromMe', False) and not conversa.cliente_nome:
            # Mensagem do cliente
            cliente_nome = message_data.get('senderName', '')
            if cliente_nome:
                conversa.cliente_nome = cliente_nome
                self.logger.info(f"Cliente identificado: {cliente_nome}")
        
        # Calcular tempo total da conversa em minutos
        if conversa.data_inicio:
            delta = datetime.datetime.now() - conversa.data_inicio
            conversa.tempo_total = round(delta.total_seconds() / 60, 2)
        
        # Atualizar tempos de resposta apenas para mensagens do atendente
        if message_data.get('fromMe', False):
            # Buscar última mensagem do cliente na conversa
            session = object_session(conversa)
            if session is None:
                self.logger.error("Erro ao obter sessão do objeto conversa")
                return
                
            ultima_msg_cliente = session.query(Mensagem).filter(
                Mensagem.conversa_id == conversa.id,
                Mensagem.de_atendente == False
            ).order_by(Mensagem.data_hora.desc()).first()
            
            if ultima_msg_cliente:
                # Calcular tempo de resposta em minutos
                tempo_resposta = datetime.datetime.now() - ultima_msg_cliente.data_hora
                tempo_resposta_min = round(tempo_resposta.total_seconds() / 60, 2)
                
                # Atualizar tempo máximo de resposta
                if not conversa.tempo_resposta_max or tempo_resposta_min > conversa.tempo_resposta_max:
                    conversa.tempo_resposta_max = tempo_resposta_min
                
                # Atualizar tempo médio de resposta
                if conversa.tempo_resposta_media is None:
                    conversa.tempo_resposta_media = tempo_resposta_min
                    conversa.contagem_respostas = 1
                else:
                    # Calcular nova média ponderada
                    nova_media = (conversa.tempo_resposta_media * conversa.contagem_respostas + tempo_resposta_min) / (conversa.contagem_respostas + 1)
                    conversa.tempo_resposta_media = round(nova_media, 2)
                    conversa.contagem_respostas += 1
        
        # Verificar se a conversa pode estar sendo finalizada (mensagem do atendente)
        if message_data.get('fromMe', False):
            texto = message_data.get('body', '').lower()
            frases_finalizacao = [
                'obrigado por entrar em contato',
                'espero ter ajudado',
                'tenha um bom dia',
                'posso ajudar em algo mais',
                'precisar de mais alguma coisa',
                'foi um prazer atendê-lo',
                'encerramos seu atendimento',
                'finalizamos seu atendimento',
                'atendimento finalizado',
                'atendimento encerrado'
            ]
            
            # Verificar se a mensagem contém alguma das frases de finalização
            if any(frase in texto for frase in frases_finalizacao):
                conversa.possivel_finalizacao = True
                self.logger.info(f"Conversa ID {conversa.id} marcada para possível finalização")
    
    def _detect_and_create_request(self, session, conversa: Conversa, mensagem: Mensagem):
        """
        Detecta e cria solicitações do cliente.
        
        Args:
            session: Sessão do banco de dados
            conversa: Objeto da conversa
            mensagem: Mensagem do cliente
        """
        # Obter mensagens anteriores para contexto
        mensagens_anteriores = [
            {
                "remetente": m.remetente,
                "conteudo": m.conteudo,
                "timestamp": m.timestamp
            }
            for m in conversa.mensagens[-5:]  # Últimas 5 mensagens
        ]
        
        # Detectar solicitação
        solicitacao_data = self.conversation_processor.detect_request_and_deadline(
            {
                "remetente": mensagem.remetente,
                "conteudo": mensagem.conteudo,
                "timestamp": mensagem.timestamp
            },
            mensagens_anteriores
        )
        
        if solicitacao_data and solicitacao_data.get("contém_solicitação"):
            # Criar solicitação
            solicitacao = Solicitacao(
                conversa_id=conversa.conversa_id,
                mensagem_id=mensagem.mensagem_id,
                descricao=solicitacao_data.get("descrição_solicitação"),
                data_solicitacao=mensagem.timestamp,
                status=SolicitacaoStatus.PENDENTE
            )
            session.add(solicitacao)
            
            logger.info(f"Nova solicitação criada para conversa {conversa.conversa_id}")
    
    def _check_request_fulfillment(self, session, conversa: Conversa, mensagem: Mensagem):
        """
        Verifica se uma mensagem do atendente atende a alguma solicitação pendente.
        
        Args:
            session: Sessão do banco de dados
            conversa: Objeto da conversa
            mensagem: Mensagem do atendente
        """
        # Obter solicitações pendentes
        solicitacoes_pendentes = [
            s for s in conversa.solicitacoes
            if s.status == SolicitacaoStatus.PENDENTE
        ]
        
        if not solicitacoes_pendentes:
            return
        
        # Verificar se mensagem contém prazo
        prazo_data = self.conversation_processor._extract_deadline_from_responses(
            None,  # Não precisamos da mensagem original aqui
            [{
                "remetente": mensagem.remetente,
                "conteudo": mensagem.conteudo,
                "timestamp": mensagem.timestamp
            }]
        )
        
        if prazo_data:
            # Atualizar prazo da solicitação mais recente
            solicitacao = solicitacoes_pendentes[-1]
            solicitacao.prazo_prometido = prazo_data.get("prazo")
            solicitacao.dias_uteis_prometidos = prazo_data.get("dias_uteis", 1)
            solicitacao.atendente_nome = conversa.atendente_nome
    
    def _should_close_conversation(self, conversa: Conversa) -> bool:
        """
        Verifica se uma conversa deve ser encerrada por inatividade.
        
        Args:
            conversa: Objeto da conversa
            
        Returns:
            bool: True se a conversa deve ser encerrada
        """
        if not conversa.ultima_mensagem:
            return False
        
        tempo_inativo = (
            datetime.datetime.now() - conversa.ultima_mensagem
        ).total_seconds()
        
        return tempo_inativo >= INACTIVITY_TIMEOUT
    
    def _monitor_conversations(self):
        """
        Monitora conversas ativas para identificar inatividade e outros estados.
        """
        while self.is_running:
            try:
                with safe_db_session() as session:
                    # Verificar conversas ativas
                    conversas = session.query(Conversa).filter(
                        Conversa.status.in_([
                            ConversaStatus.EM_ANDAMENTO,
                            ConversaStatus.REABERTO
                        ])
                    ).all()
                    
                    for conversa in conversas:
                        if self._should_close_conversation(conversa):
                            conversa.status = ConversaStatus.FECHADA
                            conversa.hora_termino = datetime.datetime.now()
                            logger.info(f"Conversa {conversa.conversa_id} encerrada por inatividade")
                    
                    session.commit()
                
                # Aguardar próxima verificação
                time.sleep(60)  # Verificar a cada minuto
                
            except Exception as e:
                logger.error(f"Erro no monitoramento de conversas: {e}")
                time.sleep(5)
    
    def _metrics_loop(self):
        """
        Loop para atualização periódica de métricas de conversas.
        Este método é executado em uma thread separada.
        """
        logger.info("Iniciando loop de atualização de métricas...")
        
        while self.is_running:
            try:
                # Atualizar métricas de todas as conversas ativas
                self.update_conversation_metrics()
                
                # Aguardar intervalo configurado (em segundos)
                time.sleep(self.update_metrics_interval * 60)
                
            except Exception as e:
                logger.error(f"Erro no loop de métricas: {e}")
                # Aguardar um tempo antes de tentar novamente em caso de erro
                time.sleep(60)
        
    def update_conversation_metrics(self):
        """
        Atualiza métricas de todas as conversas ativas.
        """
        try:
            logger.info("Atualizando métricas de conversas...")
            
            db = get_db()
            try:
                # Buscar todas as conversas ativas
                conversas_ativas = db.query(Conversa).filter(
                    Conversa.status.in_([ConversaStatus.ATIVO, ConversaStatus.REABERTO])
                ).all()
                
                for conversa in conversas_ativas:
                    try:
                        # Verificar solicitações com prazo vencido
                        self._verificar_solicitacoes_vencidas(db, conversa.id, datetime.datetime.now())
                        
                        # Atualizar conteúdo JSON
                        conversa.conteudo_json = self.convert_conversation_to_json(conversa.id)
                        
                        db.commit()
                        
                    except Exception as e:
                        db.rollback()
                        logger.error(f"Erro ao atualizar métricas da conversa {conversa.id}: {e}")
                
                logger.info(f"Métricas atualizadas para {len(conversas_ativas)} conversas")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas de conversas: {e}")
    
    def _verificar_solicitacoes_vencidas(self, db: Session, conversa_id: int, data_atual: datetime.datetime):
        """
        Verifica solicitações pendentes e marca como atrasadas se o prazo foi ultrapassado.
        
        Args:
            db: Sessão do banco de dados
            conversa_id: ID da conversa
            data_atual: Data atual para comparação
        """
        try:
            # Buscar solicitações pendentes desta conversa
            solicitacoes_pendentes = db.query(Solicitacao).filter(
                Solicitacao.conversa_id == conversa_id,
                Solicitacao.status == SolicitacaoStatus.PENDENTE
            ).all()
            
            for solicitacao in solicitacoes_pendentes:
                if solicitacao.prazo_prometido and solicitacao.prazo_prometido < data_atual:
                    # Prazo ultrapassado, marcar como atrasada
                    solicitacao.status = SolicitacaoStatus.ATRASADA
                    logger.info(f"Solicitação {solicitacao.id} marcada como atrasada")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao verificar solicitações vencidas: {e}")
    
    def convert_conversation_to_json(self, conversa_id: int) -> str:
        """
        Converte uma conversa completa para formato JSON para análise.
        
        Args:
            conversa_id: ID da conversa
            
        Returns:
            str: Conversa em formato JSON
        """
        try:
            db = get_db()
            try:
                # Buscar conversa
                conversa = db.query(Conversa).filter_by(id=conversa_id).first()
                if not conversa:
                    logger.error(f"Conversa {conversa_id} não encontrada")
                    return "{}"
                
                # Buscar mensagens
                mensagens = db.query(Mensagem).filter_by(
                    conversa_id=conversa_id
                ).order_by(Mensagem.data_hora).all()
                
                # Buscar solicitações
                solicitacoes = db.query(Solicitacao).filter_by(
                    conversa_id=conversa_id
                ).all()
                
                # Criar dicionário da conversa
                conversa_dict = {
                    "id": conversa.id,
                    "cliente": {
                        "nome": conversa.cliente_nome or "Cliente",
                        "telefone": conversa.cliente_telefone
                    },
                    "atendente": {
                        "nome": conversa.atendente_nome or "Atendente"
                    },
                    "status": conversa.status.value if conversa.status else None,
                    "inicio": conversa.data_inicio.isoformat() if conversa.data_inicio else None,
                    "fim": conversa.data_fim.isoformat() if conversa.data_fim else None,
                    "tempo_total_segundos": conversa.tempo_total,
                    "tempo_resposta_maximo": conversa.tempo_resposta_max,
                    "tempo_resposta_medio": conversa.tempo_resposta_media,
                    "mensagens": [],
                    "solicitacoes": []
                }
                
                # Adicionar mensagens
                for msg in mensagens:
                    msg_dict = {
                        "id": msg.id,
                        "timestamp": msg.data_hora.isoformat(),
                        "remetente": {
                            "tipo": msg.remetente_tipo,
                            "nome": msg.remetente_nome
                        },
                        "conteudo": msg.conteudo,
                        "tipo": msg.tipo_mensagem
                    }
                    conversa_dict["mensagens"].append(msg_dict)
                
                # Adicionar solicitações
                for solicitacao in solicitacoes:
                    sol_dict = {
                        "id": solicitacao.id,
                        "descricao": solicitacao.descricao,
                        "data_solicitacao": solicitacao.data_solicitacao.isoformat() if solicitacao.data_solicitacao else None,
                        "prazo_prometido": solicitacao.prazo_prometido.isoformat() if solicitacao.prazo_prometido else None,
                        "status": solicitacao.status.value if solicitacao.status else None,
                        "dias_uteis_prometidos": solicitacao.dias_uteis_prometidos,
                        "atendente": solicitacao.atendente_nome,
                        "data_atendimento": solicitacao.data_atendimento.isoformat() if solicitacao.data_atendimento else None
                    }
                    conversa_dict["solicitacoes"].append(sol_dict)
                
                # Converter para JSON
                return json.dumps(conversa_dict, ensure_ascii=False)
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Erro ao converter conversa para JSON: {e}")
            return "{}"

    def _create_new_message(self, session, conversa, message_data):
        """
        Cria uma nova mensagem no banco de dados a partir dos dados recebidos.
        
        Args:
            session: Sessão do SQLAlchemy
            conversa: Objeto da conversa à qual a mensagem pertence
            message_data: Dados da mensagem recebida
            
        Returns:
            Objeto Mensagem criado
        """
        # Extrair dados da mensagem
        message_id = message_data.get('id', '')
        
        # Verificar se a mensagem já existe no banco
        mensagem_existente = session.query(Mensagem).filter(
            Mensagem.message_id == message_id
        ).first()
        
        if mensagem_existente:
            self.logger.info(f"Mensagem {message_id} já existe no banco. Ignorando.")
            return mensagem_existente
            
        # Determinar se é mensagem do atendente ou cliente
        de_atendente = message_data.get('fromMe', False)
        
        # Criar a nova mensagem
        nova_mensagem = Mensagem(
            conversa_id=conversa.id,
            message_id=message_id,
            data_hora=datetime.datetime.fromtimestamp(message_data.get('timestamp', time.time())),
            de_atendente=de_atendente,
            remetente_nome=message_data.get('senderName', ''),
            conteudo=message_data.get('body', ''),
            tipo=message_data.get('type', 'text'),
            midias=json.dumps(message_data.get('media', [])) if message_data.get('media') else None
        )
        
        # Processar anexos ou mídia se houver
        if message_data.get('hasMedia', False):
            # Aqui seria processada a mídia, por exemplo, salvando URLs ou referências
            nova_mensagem.tem_midia = True
        
        try:
            session.add(nova_mensagem)
            session.flush()  # Obter ID sem commit
            self.logger.info(f"Nova mensagem criada. ID: {nova_mensagem.id}, De: {'Atendente' if de_atendente else 'Cliente'}")
            return nova_mensagem
        except Exception as e:
            self.logger.error(f"Erro ao criar mensagem: {str(e)}")
            session.rollback()
            return None

# Singleton para acesso global
collector_agent = None

def get_collector_agent():
    """
    Obtém a instância global do agente coletor.
    
    Returns:
        CollectorAgent: Instância do agente coletor
    """
    global collector_agent
    if collector_agent is None:
        collector_agent = CollectorAgent()
    
    return collector_agent 
    return collector_agent 