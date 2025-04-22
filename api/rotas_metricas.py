import sys
import os
from flask import Blueprint, request, jsonify
import json
import logging
from datetime import datetime

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from database.firebase_db import get_firestore_db
from src.utils.logger import setup_logger
from src.metrics.metrics_manager import MetricsManager
from src.utils.metricas_servico import (
    obter_metricas_servico,
    calcular_tempo_medio_resposta,
    calcular_tempo_medio_resolucao,
    calcular_pontuacao_media_avaliacoes,
    calcular_eficiencia_atendentes
)
from src.utils.list_avaliacoes import get_avaliacoes

# Criando o blueprint para as rotas de métricas
metricas_blueprint = Blueprint('metricas', __name__)

@metricas_blueprint.route('/todas-metricas', methods=['GET'])
def todas_metricas():
    """Retorna todas as métricas do serviço"""
    metricas = obter_metricas_servico()
    if metricas.get('erro'):
        return jsonify({"erro": metricas['mensagem']}), 500
    return jsonify(metricas)

@metricas_blueprint.route('/tempo-resposta', methods=['GET'])
def tempo_resposta():
    """Retorna as métricas de tempo de resposta"""
    dados = calcular_tempo_medio_resposta()
    if dados is None:
        return jsonify({"erro": "Dados insuficientes para calcular tempo de resposta"}), 404
    return jsonify(dados)

@metricas_blueprint.route('/tempo-resolucao', methods=['GET'])
def tempo_resolucao():
    """Retorna as métricas de tempo de resolução"""
    dados = calcular_tempo_medio_resolucao()
    if dados is None:
        return jsonify({"erro": "Dados insuficientes para calcular tempo de resolução"}), 404
    return jsonify(dados)

@metricas_blueprint.route('/pontuacoes', methods=['GET'])
def pontuacoes():
    """Retorna as pontuações médias das avaliações"""
    dados = calcular_pontuacao_media_avaliacoes()
    if dados is None:
        return jsonify({"erro": "Dados insuficientes para calcular pontuações"}), 404
    return jsonify(dados)

@metricas_blueprint.route('/eficiencia-atendentes', methods=['GET'])
def eficiencia_atendentes():
    """Retorna as métricas de eficiência dos atendentes"""
    dados = calcular_eficiencia_atendentes()
    if dados is None:
        return jsonify({"erro": "Dados insuficientes para calcular eficiência dos atendentes"}), 404
    return jsonify(dados)

@metricas_blueprint.route('/avaliacoes', methods=['GET'])
def avaliacoes():
    """Retorna todas as avaliações no formato adequado para o dashboard"""
    try:
        dados = get_avaliacoes()
        return jsonify(dados)
    except Exception as e:
        return jsonify({"erro": f"Erro ao obter avaliações: {str(e)}"}), 500

def registrar_rotas_metricas(app):
    """Registra as rotas de métricas no aplicativo Flask"""
    app.register_blueprint(metricas_blueprint, url_prefix='/api/metricas') 