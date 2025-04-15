#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
import datetime
from contextlib import contextmanager

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from database.models import Solicitacao, SolicitacaoStatus, SolicitacaoPrioridade, Conversa, Atendente
from database.db_engine import SessionLocal

@contextmanager
def safe_db_session():
    """Gerencia a sessão do banco de dados com tratamento de exceções"""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        print(f"Erro no banco de dados: {str(e)}")
        raise
    finally:
        session.close()

def format_datetime(dt):
    """Formata um objeto datetime para string"""
    if dt is None:
        return None
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def calcular_tempo_atendimento(data_criacao, data_conclusao):
    """Calcula o tempo de atendimento em horas e minutos"""
    if data_criacao is None or data_conclusao is None:
        return None
    
    diff = data_conclusao - data_criacao
    segundos_totais = diff.total_seconds()
    horas = int(segundos_totais // 3600)
    minutos = int((segundos_totais % 3600) // 60)
    
    if horas > 0:
        return f"{horas}h {minutos}min"
    else:
        return f"{minutos}min"

def calcular_tempo_restante(data_prazo):
    """Calcula o tempo restante até o prazo"""
    if data_prazo is None:
        return None
    
    agora = datetime.datetime.now()
    if data_prazo < agora:
        return "Atrasado"
    
    diff = data_prazo - agora
    dias = diff.days
    horas = diff.seconds // 3600
    
    if dias > 0:
        return f"{dias} dias"
    else:
        return f"{horas}h"

def get_solicitacoes():
    """Retorna a lista de solicitações formatadas para a API"""
    try:
        with safe_db_session() as session:
            result = session.query(
                Solicitacao.id,
                Solicitacao.tipo,
                Solicitacao.descricao,
                Solicitacao.status,
                Solicitacao.prioridade,
                Solicitacao.data_criacao,
                Solicitacao.data_prazo,
                Solicitacao.data_conclusao,
                Conversa.id.label('conversa_id'),
                Conversa.nome_cliente,
                Atendente.nome.label('nome_atendente')
            ).join(
                Conversa, Conversa.id == Solicitacao.conversa_id
            ).join(
                Atendente, Atendente.id == Conversa.atendente_id, isouter=True
            ).order_by(
                Solicitacao.data_criacao.desc()
            ).limit(100).all()
            
            solicitacoes = []
            for r in result:
                tempo_atendimento = calcular_tempo_atendimento(r.data_criacao, r.data_conclusao)
                tempo_restante = None
                
                if r.status != SolicitacaoStatus.CONCLUIDA and r.status != SolicitacaoStatus.CANCELADA:
                    tempo_restante = calcular_tempo_restante(r.data_prazo)
                
                solicitacoes.append({
                    'id': r.id,
                    'conversa_id': r.conversa_id,
                    'tipo': r.tipo,
                    'descricao': r.descricao,
                    'status': r.status.value if isinstance(r.status, SolicitacaoStatus) else r.status,
                    'prioridade': r.prioridade.value if isinstance(r.prioridade, SolicitacaoPrioridade) else r.prioridade,
                    'cliente': r.nome_cliente or 'Cliente não identificado',
                    'atendente': r.nome_atendente or 'Atendente não identificado',
                    'data_criacao': format_datetime(r.data_criacao),
                    'data_prazo': format_datetime(r.data_prazo),
                    'data_conclusao': format_datetime(r.data_conclusao),
                    'tempo_atendimento': tempo_atendimento,
                    'tempo_restante': tempo_restante
                })
            
            return solicitacoes
            
    except Exception as e:
        print(f"Erro ao obter solicitações: {str(e)}")
        return {
            'erro': True,
            'mensagem': f"Erro ao obter solicitações: {str(e)}"
        }

if __name__ == "__main__":
    # Teste da função
    solicitacoes = get_solicitacoes()
    print(json.dumps(solicitacoes, indent=4, ensure_ascii=False)) 