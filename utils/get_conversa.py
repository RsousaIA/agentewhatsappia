#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
from datetime import datetime
from contextlib import contextmanager

from database import get_session, Conversa, Mensagem, Solicitacao, Avaliacao

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
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def get_conversa(conversa_id):
    """
    Retorna os detalhes de uma conversa específica.
    """
    try:
        with safe_db_session() as session:
            # Buscar conversa
            conversa = session.query(Conversa).filter(Conversa.id == conversa_id).first()
            
            if not conversa:
                return {"erro": True, "mensagem": f"Conversa {conversa_id} não encontrada"}
            
            # Buscar mensagens
            mensagens = session.query(Mensagem).filter(
                Mensagem.conversa_id == conversa_id
            ).order_by(Mensagem.data_hora).all()
            
            # Buscar solicitações
            solicitacoes = session.query(Solicitacao).filter(
                Solicitacao.conversa_id == conversa_id
            ).order_by(Solicitacao.data_solicitacao).all()
            
            # Buscar avaliação
            avaliacao = session.query(Avaliacao).filter(
                Avaliacao.conversa_id == conversa_id
            ).first()
            
            # Formatar dados da conversa
            conversa_data = {
                "id": conversa.id,
                "cliente": conversa.cliente_nome,
                "cliente_telefone": conversa.cliente_telefone,
                "atendente": conversa.atendente_nome,
                "data_inicio": format_datetime(conversa.data_inicio),
                "data_fim": format_datetime(conversa.data_fim),
                "status": conversa.status.value,
                "tempo_total": conversa.tempo_total,
                "tempo_resposta_medio": conversa.tempo_resposta_medio,
                "tempo_resposta_maximo": conversa.tempo_resposta_maximo,
                "ultima_atualizacao": format_datetime(conversa.ultima_atualizacao)
            }
            
            # Formatar mensagens
            mensagens_data = []
            for m in mensagens:
                mensagens_data.append({
                    "id": m.id,
                    "remetente": m.remetente_tipo,
                    "nome": m.remetente_nome,
                    "data_hora": format_datetime(m.data_hora),
                    "conteudo": m.conteudo,
                    "tipo": m.tipo_mensagem
                })
            
            # Formatar solicitações
            solicitacoes_data = []
            for s in solicitacoes:
                solicitacoes_data.append({
                    "id": s.id,
                    "descricao": s.descricao,
                    "data_solicitacao": format_datetime(s.data_solicitacao),
                    "prazo_prometido": format_datetime(s.prazo_prometido),
                    "status": s.status.value,
                    "dias_uteis_prometidos": s.dias_uteis_prometidos,
                    "atendente": s.atendente_nome,
                    "data_atendimento": format_datetime(s.data_atendimento)
                })
            
            # Formatar avaliação
            avaliacao_data = None
            if avaliacao:
                avaliacao_data = {
                    "id": avaliacao.id,
                    "clareza_comunicacao": avaliacao.clareza_comunicacao,
                    "conhecimento_tecnico": avaliacao.conhecimento_tecnico,
                    "paciencia": avaliacao.paciencia,
                    "profissionalismo": avaliacao.profissionalismo,
                    "inteligencia_emocional": avaliacao.inteligencia_emocional,
                    "nota_final": avaliacao.nota_final,
                    "reclamacao_cliente": avaliacao.reclamacao_cliente,
                    "observacoes": avaliacao.observacoes,
                    "solicitacoes_nao_atendidas": avaliacao.solicitacoes_nao_atendidas,
                    "solicitacoes_atrasadas": avaliacao.solicitacoes_atrasadas,
                    "cumprimento_prazos": avaliacao.cumprimento_prazos,
                    "status": avaliacao.status.value,
                    "data_avaliacao": format_datetime(avaliacao.data_avaliacao)
                }
            
            # Montar resultado final
            return {
                "conversa": conversa_data,
                "mensagens": mensagens_data,
                "solicitacoes": solicitacoes_data,
                "avaliacao": avaliacao_data
            }
            
    except Exception as e:
        print(f"Erro ao obter conversa {conversa_id}: {e}", file=sys.stderr)
        return {"erro": True, "mensagem": f"Erro ao obter conversa: {str(e)}"}

if __name__ == "__main__":
    # Verificar se ID foi fornecido
    if len(sys.argv) < 2:
        print('{"erro": true, "mensagem": "ID da conversa não fornecido"}')
        sys.exit(1)
    
    try:
        conversa_id = int(sys.argv[1])
        resultado = get_conversa(conversa_id)
        print(json.dumps(resultado, ensure_ascii=False))
    except ValueError:
        print('{"erro": true, "mensagem": "ID da conversa inválido"}')
        sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        print('{"erro": true, "mensagem": "Erro ao processar dados da conversa"}')
        sys.exit(1) 