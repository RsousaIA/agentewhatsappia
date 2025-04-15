#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from db.session import SessionLocal
from db.models import Atendimento, Avaliacao, Solicitacao

def get_avaliacoes():
    """
    Retorna todas as avaliações formatadas para o dashboard
    
    Returns:
        list: Lista de avaliações formatadas
    """
    with SessionLocal() as session:
        try:
            # Busca todas as avaliações com seus atendimentos e solicitações relacionados
            avaliacoes = (
                session.query(
                    Avaliacao, 
                    Atendimento, 
                    Solicitacao
                )
                .join(Atendimento, Avaliacao.atendimento_id == Atendimento.id)
                .join(Solicitacao, Atendimento.solicitacao_id == Solicitacao.id)
                .all()
            )
            
            resultado = []
            
            for avaliacao, atendimento, solicitacao in avaliacoes:
                # Calcula o tempo de resolução em minutos
                tempo_resolucao = None
                if solicitacao.data_criacao and solicitacao.data_resolucao:
                    tempo_resolucao = int((solicitacao.data_resolucao - solicitacao.data_criacao).total_seconds() / 60)
                
                # Calcula o tempo da primeira resposta em minutos
                tempo_primeira_resposta = None
                if solicitacao.data_criacao and solicitacao.data_primeira_resposta:
                    tempo_primeira_resposta = int((solicitacao.data_primeira_resposta - solicitacao.data_criacao).total_seconds() / 60)
                
                # Formata a data para o padrão brasileiro
                data_formatada = solicitacao.data_criacao.strftime("%d/%m/%Y") if solicitacao.data_criacao else "Sem data"
                
                # Cria o objeto de avaliação formatado
                avaliacao_formatada = {
                    "id": avaliacao.id,
                    "data": data_formatada,
                    "atendente": atendimento.atendente or "Não identificado",
                    "cliente": solicitacao.cliente or "Não identificado",
                    "tempo_resolucao": tempo_resolucao,
                    "tempo_primeira_resposta": tempo_primeira_resposta,
                    "pontuacao_tempo_resposta": avaliacao.pontuacao_tempo_resposta,
                    "pontuacao_qualidade": avaliacao.pontuacao_qualidade,
                    "pontuacao_resolucao": avaliacao.pontuacao_resolucao,
                    "pontuacao_satisfacao": avaliacao.pontuacao_satisfacao,
                    "pontuacao_final": avaliacao.pontuacao_final,
                    "comentario": avaliacao.comentario or ""
                }
                
                resultado.append(avaliacao_formatada)
            
            return resultado
            
        except SQLAlchemyError as e:
            print(f"Erro ao buscar avaliações: {e}")
            return []

if __name__ == "__main__":
    # Teste da função
    avaliacoes = get_avaliacoes()
    print(f"Total de avaliações: {len(avaliacoes)}")
    if avaliacoes:
        print("Exemplo de avaliação:")
        print(avaliacoes[0]) 