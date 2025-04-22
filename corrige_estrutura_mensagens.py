#!/usr/bin/env python3
"""
Script para corrigir a estrutura das mensagens no Firebase, garantindo
que todas sigam o padrão: tipo, conteudo, remetente e timestamp
"""

import os
import argparse
from typing import Dict, Any, List
import datetime
import time
from loguru import logger

# Configura logging
logger.remove()
logger.add(
    "logs/correcao_estrutura.log",
    rotation="500 MB",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(
    lambda msg: print(msg),
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Tenta importar os módulos do Firebase
try:
    from database.firebase_db import (
        init_firebase,
        get_firestore_db,
        get_conversations
    )
except ImportError:
    try:
        # Tenta importar de outro caminho
        from firebase_db import (
            init_firebase,
            get_firestore_db,
            get_conversations
        )
    except ImportError:
        # Se não encontrar, define funções para teste
        logger.warning("Módulos do Firebase não encontrados. Usando modo de simulação.")
        
        def init_firebase():
            logger.info("Firebase inicializado (modo simulação)")
            return True
            
        def get_firestore_db():
            logger.info("Obtendo instância do Firestore (modo simulação)")
            return None
            
        def get_conversations():
            logger.info("Obtendo conversas (modo simulação)")
            return []

def corrigir_mensagens(conversation_id: str = None, dry_run: bool = True):
    """
    Corrige a estrutura das mensagens nas conversas
    
    Args:
        conversation_id: ID específico da conversa (None para todas)
        dry_run: Se True, apenas simula as correções sem aplicá-las
    """
    # Inicializa o Firebase
    init_firebase()
    db = get_firestore_db()
    
    if db is None:
        logger.error("Não foi possível conectar ao Firebase")
        return
        
    # Obtém as conversas a serem processadas
    if conversation_id:
        logger.info(f"Processando apenas a conversa {conversation_id}")
        conversations = [db.collection('conversas').document(conversation_id).get()]
        if not conversations[0].exists:
            logger.error(f"Conversa {conversation_id} não encontrada")
            return
    else:
        logger.info("Processando todas as conversas")
        conversations = db.collection('conversas').stream()
    
    total_conversations = 0
    total_messages = 0
    fixed_messages = 0
    
    # Processa cada conversa
    for conv_doc in conversations:
        total_conversations += 1
        conv_id = conv_doc.id
        logger.info(f"Processando conversa {conv_id}")
        
        # Obtém as mensagens da conversa
        messages_ref = db.collection('conversas').document(conv_id).collection('mensagens')
        messages = messages_ref.stream()
        
        # Processa cada mensagem
        for msg_doc in messages:
            total_messages += 1
            msg_id = msg_doc.id
            msg_data = msg_doc.to_dict()
            
            # Verifica se a mensagem precisa ser corrigida
            needs_fix = False
            new_data = {}
            
            # Campo tipo
            if 'tipo' not in msg_data:
                needs_fix = True
                if msg_data.get('mediaUrl') or msg_data.get('mediaType'):
                    if msg_data.get('mediaType') == 'image' or (msg_data.get('mediaUrl') and 'image' in msg_data.get('mediaUrl', '')):
                        new_data['tipo'] = 'imagem'
                    elif msg_data.get('mediaType') == 'audio' or (msg_data.get('mediaUrl') and 'audio' in msg_data.get('mediaUrl', '')):
                        new_data['tipo'] = 'audio'
                    elif msg_data.get('mediaType') == 'video' or (msg_data.get('mediaUrl') and 'video' in msg_data.get('mediaUrl', '')):
                        new_data['tipo'] = 'video'
                    else:
                        new_data['tipo'] = 'arquivo'
                else:
                    new_data['tipo'] = 'texto'
            else:
                new_data['tipo'] = msg_data['tipo']
            
            # Campo conteudo
            if 'conteudo' not in msg_data:
                needs_fix = True
                if msg_data.get('mediaUrl'):
                    new_data['conteudo'] = msg_data['mediaUrl']
                elif msg_data.get('body'):
                    new_data['conteudo'] = msg_data['body']
                elif msg_data.get('content'):
                    new_data['conteudo'] = msg_data['content']
                else:
                    new_data['conteudo'] = "(Conteúdo não disponível)"
            else:
                new_data['conteudo'] = msg_data['conteudo']
            
            # Campo remetente
            if 'remetente' not in msg_data:
                needs_fix = True
                if msg_data.get('isFromMe') == True or msg_data.get('fromMe') == True:
                    new_data['remetente'] = 'atendente'
                elif msg_data.get('sender'):
                    new_data['remetente'] = msg_data['sender']
                elif msg_data.get('from'):
                    phone = msg_data['from'].split('@')[0] if '@' in msg_data['from'] else msg_data['from']
                    new_data['remetente'] = phone
                else:
                    new_data['remetente'] = 'cliente'
            else:
                new_data['remetente'] = msg_data['remetente']
            
            # Campo timestamp
            if 'timestamp' not in msg_data:
                needs_fix = True
                if msg_data.get('createdAt'):
                    new_data['timestamp'] = msg_data['createdAt']
                else:
                    new_data['timestamp'] = datetime.datetime.now()
            else:
                new_data['timestamp'] = msg_data['timestamp']
            
            # Aplica a correção se necessário
            if needs_fix:
                fixed_messages += 1
                logger.info(f"Corrigindo mensagem {msg_id} na conversa {conv_id}")
                logger.debug(f"Dados originais: {msg_data}")
                logger.debug(f"Novos dados: {new_data}")
                
                if not dry_run:
                    try:
                        messages_ref.document(msg_id).set(new_data)
                        logger.info(f"Mensagem {msg_id} corrigida com sucesso")
                    except Exception as e:
                        logger.error(f"Erro ao corrigir mensagem {msg_id}: {e}")
                else:
                    logger.info(f"[DRY RUN] Mensagem {msg_id} seria corrigida")
    
    # Resumo final
    logger.info(f"Processamento concluído:")
    logger.info(f"- Conversas processadas: {total_conversations}")
    logger.info(f"- Total de mensagens: {total_messages}")
    logger.info(f"- Mensagens corrigidas: {fixed_messages}")
    
    if dry_run and fixed_messages > 0:
        logger.info("Execute novamente com --apply para aplicar as correções")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corrige a estrutura das mensagens no Firebase")
    parser.add_argument("--conversation", "-c", help="ID da conversa específica (opcional)")
    parser.add_argument("--apply", "-a", action="store_true", help="Aplica as correções (sem isso, apenas simula)")
    
    args = parser.parse_args()
    
    corrigir_mensagens(
        conversation_id=args.conversation,
        dry_run=not args.apply
    ) 