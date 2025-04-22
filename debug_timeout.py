import os
import sys
from datetime import datetime
import pytz
from database.firebase_db import init_firebase, get_conversation_messages, get_conversation
from loguru import logger
from agent.collector_agent import CollectorAgent, INACTIVITY_TIMEOUT
from queue import Queue

# Inicializando o Firebase
logger.info("Inicializando Firebase...")
init_firebase()

# ID da conversa em questão
conversation_id = "xRNEmYYPBz0YGwhX23kv"

# Obtendo conversa
logger.info(f"Buscando conversa {conversation_id}...")
conversa = get_conversation(conversation_id)
if not conversa:
    logger.error(f"Conversa {conversation_id} não encontrada!")
    sys.exit(1)

logger.info(f"Status atual da conversa: {conversa.get('status')}")
logger.info(f"Última mensagem: {conversa.get('ultimaMensagem')}")
logger.info(f"Iniciada em: {conversa.get('dataHoraInicio')}")

# Calcular tempo de inatividade
ultima_mensagem = conversa.get('ultimaMensagem')
current_time = datetime.now(pytz.UTC)  # Usar UTC para compatibilidade

if isinstance(ultima_mensagem, datetime):
    # Garantir que ambos os datetimes tenham o mesmo timezone
    if ultima_mensagem.tzinfo is not None:
        # Se ultima_mensagem tem timezone, usamos ele como está
        pass
    else:
        # Se ultima_mensagem não tem timezone, assumimos que é UTC
        ultima_mensagem = pytz.UTC.localize(ultima_mensagem)
    
    segundos_inativo = (current_time - ultima_mensagem).total_seconds()
    horas_inativo = segundos_inativo / 3600
    logger.info(f"Tempo de inatividade: {horas_inativo:.2f} horas (limite: {INACTIVITY_TIMEOUT/3600:.2f} horas)")
    
    # Verificar se excede o limite de inatividade
    if segundos_inativo > INACTIVITY_TIMEOUT:
        logger.info(f"ALERTA: Esta conversa excede o tempo limite de inatividade!")
    else:
        logger.info(f"Esta conversa ainda está dentro do tempo permitido de inatividade.")
else:
    logger.error(f"Última mensagem não é um objeto datetime: {type(ultima_mensagem)}")
    sys.exit(1)

# Criar instância do agente coletor
logger.info("Criando instância do CollectorAgent...")
collector = CollectorAgent(Queue())

# Testar o método de análise de encerramento
logger.info("Testando o método de análise de encerramento...")
analysis = collector.analyze_conversation_closure(conversation_id)
logger.info(f"Análise de encerramento: {analysis}")

# Simular verificação de inatividade com timestamp modificado
logger.info("Simulando verificação com timestamp modificado (mais de 6 horas)...")

# Criar cópia da conversa com timestamp antigo
old_conversation = conversa.copy()
old_timestamp = current_time - datetime.timedelta(hours=7)  # 7 horas atrás
old_conversation['ultimaMensagem'] = old_timestamp

# Verificar se o método de limpeza encerraria a conversa
logger.info("Verificando se o método de limpeza encerraria a conversa...")
result = (current_time.timestamp() - old_timestamp.timestamp()) > INACTIVITY_TIMEOUT
logger.info(f"A conversa seria encerrada? {result}")
logger.info(f"Tempo simulado de inatividade: {(current_time - old_timestamp).total_seconds() / 3600:.2f} horas")

logger.info("Teste concluído!") 