from flask import Flask, jsonify, send_from_directory
import os
import sys
import random
import datetime
from datetime import timedelta
import json
from contextlib import contextmanager

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from database.models import Conversa, Mensagem, Solicitacao, Avaliacao
from database.db_engine import SessionLocal

app = Flask(__name__, static_folder="../public")

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

# Função auxiliar para formatar datetime
def format_datetime(dt):
    if dt is None:
        return None
    return dt.strftime("%d/%m/%Y %H:%M:%S")

@app.route('/')
def index():
    """Retorna a página inicial do dashboard"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve arquivos estáticos"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/dashboard')
def dashboard_data():
    """Retorna os dados para o dashboard principal"""
    try:
        with safe_db_session() as session:
            # Contagem de conversas ativas
            conversas_ativas = session.query(Conversa).filter(
                Conversa.status == 'ativo'
            ).count()
            
            # Contagem de mensagens de hoje
            hoje = datetime.datetime.now().date()
            mensagens_hoje = session.query(Mensagem).filter(
                Mensagem.data_hora >= hoje
            ).count()
            
            # Contagem de solicitações pendentes
            solicitacoes_pendentes = session.query(Solicitacao).filter(
                Solicitacao.status.in_(['pendente', 'atrasada'])
            ).count()
            
            # Nota média das avaliações
            result = session.query(
                Avaliacao.nota_final
            ).all()
            
            notas = [r[0] for r in result if r[0] is not None]
            nota_media = sum(notas) / len(notas) if notas else 0
            
            # Mensagens por dia (últimos 7 dias)
            mensagens_por_dia = []
            dias_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
            
            for i in range(7):
                data = hoje - timedelta(days=6-i)
                count = session.query(Mensagem).filter(
                    Mensagem.data_hora >= data,
                    Mensagem.data_hora < data + timedelta(days=1)
                ).count()
                
                mensagens_por_dia.append({
                    'data': dias_semana[data.weekday()],
                    'quantidade': count
                })
            
            # Status das solicitações
            status_solicitacoes = {
                'pendente': session.query(Solicitacao).filter(
                    Solicitacao.status == 'pendente'
                ).count(),
                'atendida': session.query(Solicitacao).filter(
                    Solicitacao.status == 'atendida'
                ).count(),
                'atrasada': session.query(Solicitacao).filter(
                    Solicitacao.status == 'atrasada'
                ).count(),
                'nao_atendida': session.query(Solicitacao).filter(
                    Solicitacao.status == 'nao_atendida'
                ).count()
            }
            
            # Tempo médio e máximo de resposta
            tempo_medio_resposta = 0
            tempo_maximo_resposta = 0
            
            # Buscar tempos de resposta de todas as conversas
            result = session.query(
                Conversa.tempo_resposta_medio,
                Conversa.tempo_resposta_maximo
            ).filter(
                Conversa.tempo_resposta_medio.isnot(None),
                Conversa.tempo_resposta_maximo.isnot(None)
            ).all()
            
            if result:
                tempos_medios = [r[0] for r in result]
                tempos_maximos = [r[1] for r in result]
                
                tempo_medio_resposta = sum(tempos_medios) / len(tempos_medios)
                tempo_maximo_resposta = max(tempos_maximos) if tempos_maximos else 0
            
            # Avaliações recentes (últimas 5)
            avaliacoes_recentes = []
            result = session.query(
                Avaliacao.id,
                Avaliacao.nota_final,
                Avaliacao.data_avaliacao,
                Conversa.id.label('conversa_id'),
                Conversa.nome_cliente,
                Conversa.nome_atendente
            ).join(
                Conversa, Conversa.id == Avaliacao.conversa_id
            ).order_by(
                Avaliacao.data_avaliacao.desc()
            ).limit(5).all()
            
            for r in result:
                avaliacoes_recentes.append({
                    'id': r.id,
                    'cliente': r.nome_cliente or 'Cliente não identificado',
                    'atendente': r.nome_atendente or 'Atendente não identificado',
                    'nota': r.nota_final,
                    'data': format_datetime(r.data_avaliacao),
                    'conversa_id': r.conversa_id
                })
            
            # Total de avaliações feitas
            avaliacoes_feitas = session.query(Avaliacao).count()
            
            return jsonify({
                'conversas_ativas': conversas_ativas,
                'mensagens_hoje': mensagens_hoje,
                'solicitacoes_pendentes': solicitacoes_pendentes,
                'nota_media': nota_media,
                'mensagens_por_dia': mensagens_por_dia,
                'status_solicitacoes': status_solicitacoes,
                'tempo_medio_resposta': tempo_medio_resposta,
                'tempo_maximo_resposta': tempo_maximo_resposta,
                'avaliacoes_recentes': avaliacoes_recentes,
                'avaliacoes_feitas': avaliacoes_feitas
            })
            
    except Exception as e:
        print(f"Erro ao obter dados do dashboard: {str(e)}")
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter dados do dashboard: {str(e)}"
        }), 500

@app.route('/api/conversas')
def get_conversas():
    """Retorna a lista de conversas"""
    try:
        with safe_db_session() as session:
            result = session.query(
                Conversa.id,
                Conversa.nome_cliente,
                Conversa.nome_atendente,
                Conversa.status,
                Conversa.data_inicio,
                Conversa.data_fim,
                Conversa.tempo_resposta_medio
            ).order_by(
                Conversa.data_inicio.desc()
            ).limit(100).all()
            
            conversas = []
            for r in result:
                # Calcular a duração da conversa
                duracao = None
                if r.data_inicio and r.data_fim:
                    delta = r.data_fim - r.data_inicio
                    duracao = f"{delta.days * 24 + delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
                
                conversas.append({
                    'id': r.id,
                    'cliente': r.nome_cliente or 'Cliente não identificado',
                    'atendente': r.nome_atendente or 'Atendente não identificado',
                    'status': r.status,
                    'inicio': format_datetime(r.data_inicio),
                    'fim': format_datetime(r.data_fim),
                    'duracao': duracao,
                    'tempo_resposta': f"{int(r.tempo_resposta_medio)}s" if r.tempo_resposta_medio else None
                })
            
            return jsonify(conversas)
            
    except Exception as e:
        print(f"Erro ao obter conversas: {str(e)}")
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter conversas: {str(e)}"
        }), 500

@app.route('/api/solicitacoes')
def get_solicitacoes():
    """Retorna a lista de solicitações"""
    try:
        from utils.list_solicitacoes import get_solicitacoes
        return jsonify(get_solicitacoes())
            
    except Exception as e:
        print(f"Erro ao obter solicitações: {str(e)}")
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter solicitações: {str(e)}"
        }), 500

@app.route('/api/avaliacoes')
def get_avaliacoes():
    """Retorna a lista de avaliações"""
    try:
        from utils.list_avaliacoes import get_avaliacoes
        return jsonify(get_avaliacoes())
            
    except Exception as e:
        print(f"Erro ao obter avaliações: {str(e)}")
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter avaliações: {str(e)}"
        }), 500

@app.route('/api/conversa/<int:conversa_id>')
def get_conversa_details(conversa_id):
    """Retorna os detalhes de uma conversa específica"""
    try:
        from utils.get_conversa import get_conversa
        return jsonify(get_conversa(conversa_id))
            
    except Exception as e:
        print(f"Erro ao obter detalhes da conversa: {str(e)}")
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter detalhes da conversa: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True, port=3000) 