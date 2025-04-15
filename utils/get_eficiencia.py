#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import func, distinct, desc
from contextlib import contextmanager

# Importar modelos do banco de dados
from database.db import get_db
from database.models import (
    Conversa, Avaliacao, ConversaStatus
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

def get_eficiencia_atendentes():
    """
    Retorna os dados de eficiência dos atendentes para o dashboard.
    """
    try:
        with safe_db_session() as session:
            # Obter lista de atendentes únicos
            atendentes = session.query(distinct(Conversa.atendente_nome))\
                .filter(Conversa.atendente_nome != None)\
                .filter(Conversa.atendente_nome != "")\
                .all()
                
            atendentes_lista = []
            
            for (atendente_nome,) in atendentes:
                # Total de atendimentos por atendente
                total_atendimentos = session.query(func.count(Conversa.id))\
                    .filter(Conversa.atendente_nome == atendente_nome)\
                    .scalar() or 0
                
                # Tempo médio de resolução
                tempo_medio_resolucao = session.query(func.avg(Conversa.tempo_total))\
                    .filter(Conversa.atendente_nome == atendente_nome)\
                    .scalar() or 0
                
                # Pontuação média
                pontuacao_media = session.query(func.avg(Avaliacao.nota_final))\
                    .join(Conversa, Conversa.id == Avaliacao.conversa_id)\
                    .filter(Conversa.atendente_nome == atendente_nome)\
                    .scalar() or 0
                
                # Taxa de resolução (conversas finalizadas / total)
                conversas_finalizadas = session.query(func.count(Conversa.id))\
                    .filter(
                        Conversa.atendente_nome == atendente_nome,
                        Conversa.status == ConversaStatus.FINALIZADO
                    )\
                    .scalar() or 0
                
                taxa_resolucao = conversas_finalizadas / total_atendimentos if total_atendimentos > 0 else 0
                
                # Dados do atendente formatados
                atendente_data = {
                    "nome": atendente_nome,
                    "total_atendimentos": total_atendimentos,
                    "tempo_medio_resolucao": float(tempo_medio_resolucao),
                    "pontuacao_media": float(pontuacao_media),
                    "taxa_resolucao": float(taxa_resolucao)
                }
                
                atendentes_lista.append(atendente_data)
            
            # Ordenar por pontuação média (decrescente)
            atendentes_lista = sorted(
                atendentes_lista, 
                key=lambda x: x["pontuacao_media"], 
                reverse=True
            )
            
            return atendentes_lista
            
    except Exception as e:
        print(f"Erro ao obter eficiência dos atendentes: {e}", file=sys.stderr)
        return {
            "erro": True,
            "mensagem": str(e)
        }

if __name__ == "__main__":
    # Retornar dados em formato JSON
    try:
        dados = get_eficiencia_atendentes()
        print(json.dumps(dados, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"erro": True, "mensagem": str(e)}, ensure_ascii=False))
        sys.exit(1) 