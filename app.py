from flask import Flask, render_template, jsonify, request
import os
from datetime import datetime, timedelta
import random
import json
from utils.list_avaliacoes import get_avaliacoes

app = Flask(__name__)

# Diretório para armazenar dados de métricas (simulados)
METRICS_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(METRICS_DIR, exist_ok=True)

# Rota para a página principal do dashboard
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# API para obter todas as métricas principais
@app.route('/api/metricas/todas-metricas', methods=['GET'])
def get_todas_metricas():
    try:
        # Obter dados reais do sistema de avaliação
        avaliacoes = get_avaliacoes()
        
        if not avaliacoes:
            # Dados de exemplo caso não existam avaliações
            return jsonify({
                'total_atendimentos': 0,
                'tempo_medio_resolucao': 0,
                'pontuacao_media': 0,
                'taxa_resolucao': 0,
                'media_pontuacao_tempo_resposta': 0,
                'media_pontuacao_qualidade': 0,
                'media_pontuacao_resolucao': 0,
                'media_pontuacao_satisfacao': 0
            })
        
        # Calcular métricas baseadas nas avaliações reais
        total_atendimentos = len(avaliacoes)
        
        # Tempo médio de resolução (em minutos)
        tempos_resolucao = [a.get('tempo_resolucao', 0) for a in avaliacoes if a.get('tempo_resolucao')]
        tempo_medio_resolucao = sum(tempos_resolucao) / len(tempos_resolucao) if tempos_resolucao else 0
        
        # Pontuação média
        pontuacoes = [a.get('pontuacao_final', 0) for a in avaliacoes if a.get('pontuacao_final') is not None]
        pontuacao_media = sum(pontuacoes) / len(pontuacoes) if pontuacoes else 0
        
        # Taxa de resolução (atendimentos resolvidos / total)
        resolvidos = sum(1 for a in avaliacoes if a.get('resolvido', False))
        taxa_resolucao = resolvidos / total_atendimentos if total_atendimentos > 0 else 0
        
        # Pontuações médias por categoria
        p_tempo = [a.get('pontuacao_tempo', 0) for a in avaliacoes if a.get('pontuacao_tempo') is not None]
        p_qualidade = [a.get('pontuacao_qualidade', 0) for a in avaliacoes if a.get('pontuacao_qualidade') is not None]
        p_resolucao = [a.get('pontuacao_resolucao', 0) for a in avaliacoes if a.get('pontuacao_resolucao') is not None]
        p_satisfacao = [a.get('pontuacao_satisfacao', 0) for a in avaliacoes if a.get('pontuacao_satisfacao') is not None]
        
        media_p_tempo = sum(p_tempo) / len(p_tempo) if p_tempo else 0
        media_p_qualidade = sum(p_qualidade) / len(p_qualidade) if p_qualidade else 0
        media_p_resolucao = sum(p_resolucao) / len(p_resolucao) if p_resolucao else 0
        media_p_satisfacao = sum(p_satisfacao) / len(p_satisfacao) if p_satisfacao else 0
        
        return jsonify({
            'total_atendimentos': total_atendimentos,
            'tempo_medio_resolucao': tempo_medio_resolucao,
            'pontuacao_media': pontuacao_media,
            'taxa_resolucao': taxa_resolucao,
            'media_pontuacao_tempo_resposta': media_p_tempo,
            'media_pontuacao_qualidade': media_p_qualidade,
            'media_pontuacao_resolucao': media_p_resolucao,
            'media_pontuacao_satisfacao': media_p_satisfacao
        })
    
    except Exception as e:
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter métricas: {str(e)}"
        })

# API para obter todas as avaliações
@app.route('/api/metricas/avaliacoes', methods=['GET'])
def get_api_avaliacoes():
    try:
        avaliacoes = get_avaliacoes()
        return jsonify(avaliacoes)
    except Exception as e:
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter avaliações: {str(e)}"
        })

# API para obter eficiência dos atendentes
@app.route('/api/metricas/eficiencia-atendentes', methods=['GET'])
def get_eficiencia_atendentes():
    try:
        avaliacoes = get_avaliacoes()
        
        if not avaliacoes:
            return jsonify([])
        
        # Agrupar avaliações por atendente
        atendentes = {}
        for avaliacao in avaliacoes:
            atendente = avaliacao.get('atendente', 'Não identificado')
            if atendente not in atendentes:
                atendentes[atendente] = {
                    'nome': atendente,
                    'total_atendimentos': 0,
                    'tempos_resolucao': [],
                    'pontuacoes': [],
                    'resolvidos': 0
                }
            
            atendentes[atendente]['total_atendimentos'] += 1
            
            if avaliacao.get('tempo_resolucao'):
                atendentes[atendente]['tempos_resolucao'].append(avaliacao['tempo_resolucao'])
            
            if avaliacao.get('pontuacao_final') is not None:
                atendentes[atendente]['pontuacoes'].append(avaliacao['pontuacao_final'])
            
            if avaliacao.get('resolvido', False):
                atendentes[atendente]['resolvidos'] += 1
        
        # Calcular métricas para cada atendente
        resultado = []
        for nome, dados in atendentes.items():
            tempo_medio = sum(dados['tempos_resolucao']) / len(dados['tempos_resolucao']) if dados['tempos_resolucao'] else 0
            pontuacao_media = sum(dados['pontuacoes']) / len(dados['pontuacoes']) if dados['pontuacoes'] else 0
            taxa_resolucao = dados['resolvidos'] / dados['total_atendimentos'] if dados['total_atendimentos'] > 0 else 0
            
            resultado.append({
                'nome': nome,
                'total_atendimentos': dados['total_atendimentos'],
                'tempo_medio_resolucao': tempo_medio,
                'pontuacao_media': pontuacao_media,
                'taxa_resolucao': taxa_resolucao
            })
        
        # Ordenar por pontuação média (decrescente)
        resultado.sort(key=lambda x: x['pontuacao_media'], reverse=True)
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao obter eficiência dos atendentes: {str(e)}"
        })

# Rota para gerar o relatório em PDF (simulado)
@app.route('/api/metricas/gerar-relatorio', methods=['POST'])
def gerar_relatorio():
    try:
        # Aqui implementaríamos a geração real do relatório
        # Por ora, apenas simulamos o processo
        
        data_inicio = request.json.get('data_inicio', '')
        data_fim = request.json.get('data_fim', '')
        
        return jsonify({
            'sucesso': True,
            'mensagem': f"Relatório gerado com sucesso para o período de {data_inicio} a {data_fim}",
            'url_download': "/relatorios/metricas_report.pdf"
        })
    
    except Exception as e:
        return jsonify({
            'erro': True,
            'mensagem': f"Erro ao gerar relatório: {str(e)}"
        })

# Iniciar a aplicação se executada diretamente
if __name__ == '__main__':
    app.run(debug=True, port=3000) 