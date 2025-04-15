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
    Conversa, Avaliacao, AvaliacaoStatus
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

def get_avaliacoes():
    """
    Retorna as últimas avaliações para exibir no dashboard.
    """
    try:
        with safe_db_session() as session:
            # Obter todas as avaliações ordenadas por data
            avaliacoes_query = session.query(Avaliacao)\
                .join(Conversa, Conversa.id == Avaliacao.conversa_id)\
                .order_by(Avaliacao.data_avaliacao.desc())\
                .limit(50)  # Limitar a 50 avaliações mais recentes
            
            avaliacoes_lista = []
            
            for avaliacao in avaliacoes_query:
                conversa = session.query(Conversa).filter(Conversa.id == avaliacao.conversa_id).first()
                
                if not conversa:
                    continue
                    
                # Calcular tempo de primeira resposta e tempo total de resolução
                tempo_primeira_resposta = conversa.tempo_resposta_medio or 0
                tempo_resolucao = conversa.tempo_total or 0
                
                # Dados da avaliação formatados
                avaliacao_data = {
                    "id": avaliacao.id,
                    "conversa_id": avaliacao.conversa_id,
                    "data": avaliacao.data_avaliacao.strftime("%d/%m/%Y"),
                    "cliente": conversa.cliente_nome or "Cliente não identificado",
                    "atendente": conversa.atendente_nome or "Atendente não identificado",
                    "tempo_primeira_resposta": float(tempo_primeira_resposta) * 60,  # Converter para segundos
                    "tempo_resolucao": float(tempo_resolucao),  # Em minutos
                    "pontuacao_final": float(avaliacao.nota_final) if avaliacao.nota_final else 0,
                    "pontuacao_tempo": float(avaliacao.tempo_resposta) if avaliacao.tempo_resposta else 0,
                    "pontuacao_qualidade": float(avaliacao.qualidade_resposta) if avaliacao.qualidade_resposta else 0,
                    "pontuacao_satisfacao": float(avaliacao.satisfacao_cliente) if avaliacao.satisfacao_cliente else 0,
                    "comentario": avaliacao.reclamacoes_cliente or "-"
                }
                
                avaliacoes_lista.append(avaliacao_data)
            
            return avaliacoes_lista
            
    except Exception as e:
        print(f"Erro ao obter avaliações: {e}", file=sys.stderr)
        return {
            "erro": True,
            "mensagem": str(e)
        }

if __name__ == "__main__":
    # Retornar dados em formato JSON
    try:
        avaliacoes = get_avaliacoes()
        print(json.dumps(avaliacoes, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"erro": True, "mensagem": str(e)}, ensure_ascii=False))
        sys.exit(1) 