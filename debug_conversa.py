import os
import sys
import datetime
from database.firebase_db import init_firebase, get_conversation_messages, get_conversation
from loguru import logger
from agent.collector_agent import CollectorAgent
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

# Obtendo mensagens
logger.info(f"Buscando mensagens da conversa {conversation_id}...")
mensagens = get_conversation_messages(conversation_id)
logger.info(f"Total de mensagens: {len(mensagens)}")

# Exibindo as mensagens
logger.info("Mensagens:")
for i, msg in enumerate(mensagens):
    # Verificando o formato da mensagem
    if isinstance(msg, list):
        for sub_msg in msg:
            if isinstance(sub_msg, dict):
                logger.info(f"[{sub_msg.get('remetente', 'desconhecido')}] {sub_msg.get('conteudo', 'sem conteúdo')} ({sub_msg.get('timestamp', 'sem data')})")
            else:
                logger.info(f"Sub-mensagem com formato inesperado: {type(sub_msg)}")
    elif isinstance(msg, dict):
        logger.info(f"[{msg.get('remetente', 'desconhecido')}] {msg.get('conteudo', 'sem conteúdo')} ({msg.get('timestamp', 'sem data')})")
    else:
        logger.info(f"Mensagem {i+1} com formato inesperado: {type(msg)}")
        logger.info(f"Conteúdo: {msg}")

# Testando o método de verificação de encerramento
logger.info("Testando método de verificação de encerramento...")
collector = CollectorAgent(Queue())

# Estruturando mensagens para o teste
mensagens_formatadas = []
for msg in mensagens:
    if isinstance(msg, list):
        mensagens_formatadas.extend(msg)
    else:
        mensagens_formatadas.append(msg)

# Testa o check_conversation_closure
for idx, msg in enumerate(mensagens_formatadas):
    if isinstance(msg, dict):
        conteudo = msg.get('conteudo', '')
        remetente = msg.get('remetente', 'desconhecido')
        actor = 'cliente' if remetente == 'cliente' else 'atendente'
        logger.info(f"Testando mensagem: [{remetente}] {conteudo}")
        should_close = collector._check_conversation_closure(conversation_id, conteudo, actor)
        logger.info(f"Mensagem {idx+1}: Deveria encerrar? {should_close}")

# Testa o método de análise completa do encerramento
logger.info("Testando método completo de análise de encerramento...")
analysis = collector.analyze_conversation_closure(conversation_id)
logger.info(f"Análise completa: {analysis}")

logger.info("Verificação concluída!") 