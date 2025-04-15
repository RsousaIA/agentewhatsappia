#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime
from contextlib import contextmanager

from database import get_session, Conversa, ConversaStatus

@contextmanager
def safe_db_session():
    """Context manager para gerenciar sessões do banco de dados com tratamento de erros."""
    session = None
    try:
        session = get_session()
        yield session
        session.commit()
    except Exception as e:
        if session:
            session.rollback()
        print(f"Erro na sessão do banco de dados: {e}", file=sys.stderr)
        raise
    finally:
        if session:
            session.close()

def format_datetime(dt):
    """Formata datetime para string."""
    if dt is None:
        return None
    return dt.strftime("%d/%m/%Y %H:%M")

def get_conversas():
    """
    Retorna a lista de conversas ativas e recentemente encerradas.
    """
    try:
        with safe_db_session() as session:
            # Obter conversas ativas e as 20 conversas finalizadas mais recentes
            ativas = session.query(Conversa).filter(
                Conversa.status == ConversaStatus.ATIVO
            ).order_by(Conversa.ultima_atualizacao.desc()).all()
            
            finalizadas = session.query(Conversa).filter(
                Conversa.status != ConversaStatus.ATIVO
            ).order_by(Conversa.data_fim.desc()).limit(20).all()
            
            # Combinar e formatar
            conversas = []
            
            for c in ativas + finalizadas:
                # Calcular duração se possível
                duracao = None
                if c.tempo_total:
                    duracao = f"{int(c.tempo_total / 60)} min"
                
                # Formatar tempos de resposta
                tempo_resposta = None
                if c.tempo_resposta_medio:
                    tempo_resposta = f"{int(c.tempo_resposta_medio)} s"
                
                conversas.append({
                    "id": c.id,
                    "cliente": c.cliente_nome,
                    "atendente": c.atendente_nome,
                    "status": c.status.value,
                    "inicio": format_datetime(c.data_inicio),
                    "fim": format_datetime(c.data_fim),
                    "duracao": duracao,
                    "tempo_resposta": tempo_resposta,
                    "ultima_atualizacao": format_datetime(c.ultima_atualizacao)
                })
            
            return conversas
            
    except Exception as e:
        print(f"Erro ao listar conversas: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    # Retornar dados em formato JSON
    try:
        conversas = get_conversas()
        print(json.dumps(conversas, ensure_ascii=False))
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        # Retornar JSON vazio em caso de erro
        print('[]')
        sys.exit(1) 