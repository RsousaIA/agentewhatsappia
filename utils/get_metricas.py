#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from contextlib import contextmanager

# Importar modelos do banco de dados
from database.db import get_db
from database.models import (
    Conversa, Mensagem, Solicitacao, Avaliacao, 
    ConversaStatus, SolicitacaoStatus, AvaliacaoStatus
)

@contextmanager
def safe_db_session():
    """Context manager para gerenciar sessões do banco de dados com tratamento de erros."""
    session = None
    try:
        session = get_db()
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

def get_todas_metricas():
    """
    Retorna todas as métricas gerais para o dashboard.
    """
    try:
        with safe_db_session() as session:
            # Data de hoje no início do dia
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Total de atendimentos (todas as conversas)
            total_atendimentos = session.query(func.count(Conversa.id)).scalar() or 0
            
            # Tempo médio de resolução (em minutos)
            tempo_medio_resolucao = session.query(func.avg(Conversa.tempo_total)).scalar() or 0
            
            # Pontuação média das avaliações
            pontuacao_media = session.query(func.avg(Avaliacao.nota_final)).scalar() or 0
            
            # Taxa de resolução (conversas com status FINALIZADO / total)
            conversas_finalizadas = session.query(func.count(Conversa.id)).filter(
                Conversa.status == ConversaStatus.FINALIZADO
            ).scalar() or 0
            
            taxa_resolucao = conversas_finalizadas / total_atendimentos if total_atendimentos > 0 else 0
            
            # Médias das pontuações por categoria
            media_pontuacao_tempo_resposta = session.query(func.avg(Avaliacao.tempo_resposta)).scalar() or 0
            media_pontuacao_qualidade = session.query(func.avg(Avaliacao.qualidade_resposta)).scalar() or 0
            media_pontuacao_resolucao = session.query(func.avg(Avaliacao.cumprimento_prazos_nota)).scalar() or 0
            media_pontuacao_satisfacao = session.query(func.avg(Avaliacao.satisfacao_cliente)).scalar() or 0
            
            # Dados para distribuição de pontuações
            distribuicao_pontuacoes = {
                "excelente": session.query(func.count(Avaliacao.id)).filter(Avaliacao.nota_final >= 8).scalar() or 0,
                "bom": session.query(func.count(Avaliacao.id)).filter(Avaliacao.nota_final >= 6, Avaliacao.nota_final < 8).scalar() or 0,
                "regular": session.query(func.count(Avaliacao.id)).filter(Avaliacao.nota_final >= 4, Avaliacao.nota_final < 6).scalar() or 0,
                "ruim": session.query(func.count(Avaliacao.id)).filter(Avaliacao.nota_final < 4).scalar() or 0
            }
            
            return {
                "total_atendimentos": total_atendimentos,
                "tempo_medio_resolucao": float(tempo_medio_resolucao),
                "pontuacao_media": float(pontuacao_media),
                "taxa_resolucao": float(taxa_resolucao),
                "media_pontuacao_tempo_resposta": float(media_pontuacao_tempo_resposta),
                "media_pontuacao_qualidade": float(media_pontuacao_qualidade),
                "media_pontuacao_resolucao": float(media_pontuacao_resolucao),
                "media_pontuacao_satisfacao": float(media_pontuacao_satisfacao),
                "distribuicao_pontuacoes": distribuicao_pontuacoes
            }
            
    except Exception as e:
        print(f"Erro ao obter métricas: {e}", file=sys.stderr)
        return {
            "erro": True,
            "mensagem": str(e)
        }

if __name__ == "__main__":
    # Retornar dados em formato JSON
    try:
        dados = get_todas_metricas()
        print(json.dumps(dados, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"erro": True, "mensagem": str(e)}, ensure_ascii=False))
        sys.exit(1) 