#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from contextlib import contextmanager

from database import get_session, Conversa, Mensagem, Solicitacao, Avaliacao, ConsolidadaAtendimento, ConversaStatus, SolicitacaoStatus

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

def get_dashboard_data():
    """
    Retorna os dados principais para o dashboard.
    """
    try:
        with safe_db_session() as session:
            # Data de hoje no início do dia
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Conversas ativas
            conversas_ativas = session.query(func.count(Conversa.id)).filter(
                Conversa.status == ConversaStatus.ATIVO
            ).scalar() or 0
            
            # Mensagens recebidas hoje
            mensagens_hoje = session.query(func.count(Mensagem.id)).filter(
                Mensagem.data_hora >= hoje
            ).scalar() or 0
            
            # Solicitações pendentes
            solicitacoes_pendentes = session.query(func.count(Solicitacao.id)).filter(
                Solicitacao.status == SolicitacaoStatus.PENDENTE
            ).scalar() or 0
            
            # Avaliações feitas
            avaliacoes_feitas = session.query(func.count(Avaliacao.id)).scalar() or 0
            
            # Nota média das avaliações
            nota_media = session.query(func.avg(Avaliacao.nota_final)).scalar() or 0
            
            # Dados adicionais para gráficos
            
            # Últimos 7 dias
            inicio_semana = hoje - timedelta(days=6)
            
            # Mensagens por dia (últimos 7 dias)
            mensagens_por_dia = []
            for i in range(7):
                data = inicio_semana + timedelta(days=i)
                data_seguinte = data + timedelta(days=1)
                
                count = session.query(func.count(Mensagem.id)).filter(
                    Mensagem.data_hora >= data,
                    Mensagem.data_hora < data_seguinte
                ).scalar() or 0
                
                mensagens_por_dia.append({
                    "data": data.strftime("%d/%m"),
                    "quantidade": count
                })
            
            # Distribuição de status das solicitações
            status_solicitacoes = {
                "pendente": session.query(func.count(Solicitacao.id)).filter(
                    Solicitacao.status == SolicitacaoStatus.PENDENTE
                ).scalar() or 0,
                "atendida": session.query(func.count(Solicitacao.id)).filter(
                    Solicitacao.status == SolicitacaoStatus.ATENDIDA
                ).scalar() or 0,
                "atrasada": session.query(func.count(Solicitacao.id)).filter(
                    Solicitacao.status == SolicitacaoStatus.ATRASADA
                ).scalar() or 0,
                "nao_atendida": session.query(func.count(Solicitacao.id)).filter(
                    Solicitacao.status == SolicitacaoStatus.NAO_ATENDIDA
                ).scalar() or 0
            }
            
            # Tempos médios de resposta
            tempos_resposta = session.query(
                func.avg(Conversa.tempo_resposta_medio),
                func.max(Conversa.tempo_resposta_maximo)
            ).first()
            
            tempo_medio = tempos_resposta[0] or 0
            tempo_maximo = tempos_resposta[1] or 0
            
            # Últimas avaliações (top 5)
            avaliacoes_recentes = []
            avaliacoes = session.query(Avaliacao).order_by(Avaliacao.data_avaliacao.desc()).limit(5).all()
            
            for avaliacao in avaliacoes:
                conversa = session.query(Conversa).filter(Conversa.id == avaliacao.conversa_id).first()
                
                if conversa:
                    avaliacoes_recentes.append({
                        "id": avaliacao.id,
                        "conversa_id": avaliacao.conversa_id,
                        "cliente": conversa.cliente_nome,
                        "atendente": conversa.atendente_nome,
                        "nota": avaliacao.nota_final,
                        "data": avaliacao.data_avaliacao.strftime("%d/%m/%Y %H:%M")
                    })
            
            return {
                "conversas_ativas": conversas_ativas,
                "mensagens_hoje": mensagens_hoje,
                "solicitacoes_pendentes": solicitacoes_pendentes,
                "avaliacoes_feitas": avaliacoes_feitas,
                "nota_media": float(nota_media),
                "mensagens_por_dia": mensagens_por_dia,
                "status_solicitacoes": status_solicitacoes,
                "tempo_medio_resposta": float(tempo_medio),
                "tempo_maximo_resposta": float(tempo_maximo),
                "avaliacoes_recentes": avaliacoes_recentes
            }
            
    except Exception as e:
        # Em caso de erro, retornar dados padrão
        print(f"Erro ao obter dados: {e}", file=sys.stderr)
        return {
            "conversas_ativas": 0,
            "mensagens_hoje": 0,
            "solicitacoes_pendentes": 0,
            "avaliacoes_feitas": 0,
            "nota_media": 0,
            "mensagens_por_dia": [],
            "status_solicitacoes": {"pendente": 0, "atendida": 0, "atrasada": 0, "nao_atendida": 0},
            "tempo_medio_resposta": 0,
            "tempo_maximo_resposta": 0,
            "avaliacoes_recentes": []
        }

if __name__ == "__main__":
    # Retornar dados em formato JSON
    try:
        data = get_dashboard_data()
        print(json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        # Retornar JSON mínimo em caso de erro
        print('{"erro": true, "mensagem": "Erro ao processar dados do dashboard"}')
        sys.exit(1) 