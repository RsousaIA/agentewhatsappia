from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from firebase_admin import firestore
from .firebase_db import get_firestore_db

logger = logging.getLogger(__name__)

def get_conversation_metrics(start_date: datetime, end_date: datetime) -> Dict:
    """
    Obtém métricas gerais das conversas em um período
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
        
    Returns:
        Dict com métricas das conversas
    """
    try:
        db = get_firestore_db()
        
        # Consulta conversas no período
        conversations_ref = db.collection('conversas').where(
            filter=firestore.FieldFilter('data_inicio', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('data_inicio', '<=', end_date)
        )
        
        total_conversas = 0
        conversas_ativas = 0
        conversas_finalizadas = 0
        tempo_medio_resposta = 0
        total_tempo_resposta = 0
        contador_tempo_resposta = 0
        
        for doc in conversations_ref.stream():
            data = doc.to_dict()
            total_conversas += 1
            
            if data.get('status') == 'ativo':
                conversas_ativas += 1
            elif data.get('status') == 'finalizado':
                conversas_finalizadas += 1
                
            # Calcular tempo médio de resposta
            if 'tempo_resposta' in data:
                total_tempo_resposta += data['tempo_resposta']
                contador_tempo_resposta += 1
        
        if contador_tempo_resposta > 0:
            tempo_medio_resposta = total_tempo_resposta / contador_tempo_resposta
        
        return {
            'total_conversas': total_conversas,
            'conversas_ativas': conversas_ativas,
            'conversas_finalizadas': conversas_finalizadas,
            'tempo_medio_resposta': tempo_medio_resposta,
            'periodo': {
                'inicio': start_date,
                'fim': end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de conversas: {e}")
        return {}

def get_satisfaction_metrics(start_date: datetime, end_date: datetime) -> Dict:
    """
    Obtém métricas de satisfação dos clientes em um período
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
        
    Returns:
        Dict com métricas de satisfação
    """
    try:
        db = get_firestore_db()
        
        # Consulta avaliações no período
        avaliacoes_ref = db.collection('avaliacoes').where(
            filter=firestore.FieldFilter('data_criacao', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('data_criacao', '<=', end_date)
        )
        
        total_avaliacoes = 0
        soma_notas = 0
        notas_por_categoria = {}
        
        for doc in avaliacoes_ref.stream():
            data = doc.to_dict()
            total_avaliacoes += 1
            
            nota = data.get('nota', 0)
            categoria = data.get('categoria', 'geral')
            
            soma_notas += nota
            
            if categoria not in notas_por_categoria:
                notas_por_categoria[categoria] = {'total': 0, 'soma': 0}
            
            notas_por_categoria[categoria]['total'] += 1
            notas_por_categoria[categoria]['soma'] += nota
        
        # Calcular médias
        media_geral = soma_notas / total_avaliacoes if total_avaliacoes > 0 else 0
        
        medias_por_categoria = {}
        for categoria, dados in notas_por_categoria.items():
            medias_por_categoria[categoria] = dados['soma'] / dados['total']
        
        return {
            'total_avaliacoes': total_avaliacoes,
            'media_geral': media_geral,
            'medias_por_categoria': medias_por_categoria,
            'periodo': {
                'inicio': start_date,
                'fim': end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de satisfação: {e}")
        return {}

def get_performance_metrics(start_date: datetime, end_date: datetime) -> Dict:
    """
    Obtém métricas de performance do atendimento em um período
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
        
    Returns:
        Dict com métricas de performance
    """
    try:
        db = get_firestore_db()
        
        # Consulta solicitações no período
        solicitacoes_ref = db.collection('solicitacoes').where(
            filter=firestore.FieldFilter('data_criacao', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('data_criacao', '<=', end_date)
        )
        
        total_solicitacoes = 0
        solicitacoes_resolvidas = 0
        tempo_medio_resolucao = 0
        total_tempo_resolucao = 0
        contador_tempo_resolucao = 0
        
        for doc in solicitacoes_ref.stream():
            data = doc.to_dict()
            total_solicitacoes += 1
            
            if data.get('status') == 'resolvido':
                solicitacoes_resolvidas += 1
                
                # Calcular tempo de resolução
                if 'data_resolucao' in data and 'data_criacao' in data:
                    tempo_resolucao = (data['data_resolucao'] - data['data_criacao']).total_seconds()
                    total_tempo_resolucao += tempo_resolucao
                    contador_tempo_resolucao += 1
        
        if contador_tempo_resolucao > 0:
            tempo_medio_resolucao = total_tempo_resolucao / contador_tempo_resolucao
        
        taxa_resolucao = (solicitacoes_resolvidas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0
        
        return {
            'total_solicitacoes': total_solicitacoes,
            'solicitacoes_resolvidas': solicitacoes_resolvidas,
            'taxa_resolucao': taxa_resolucao,
            'tempo_medio_resolucao': tempo_medio_resolucao,
            'periodo': {
                'inicio': start_date,
                'fim': end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de performance: {e}")
        return {}

def get_trending_topics(start_date: datetime, end_date: datetime, limit: int = 10) -> List[Dict]:
    """
    Identifica os tópicos mais frequentes nas conversas em um período
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
        limit: Número máximo de tópicos a retornar
        
    Returns:
        Lista de tópicos mais frequentes
    """
    try:
        db = get_firestore_db()
        
        # Consulta mensagens no período
        messages_ref = db.collection('mensagens').where(
            filter=firestore.FieldFilter('data_hora', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('data_hora', '<=', end_date)
        )
        
        # Contagem de palavras-chave
        keywords_count = {}
        
        for doc in messages_ref.stream():
            data = doc.to_dict()
            content = data.get('conteudo', '').lower()
            
            # TODO: Implementar análise de sentimento e extração de tópicos
            # Por enquanto, apenas conta palavras simples
            words = content.split()
            for word in words:
                if len(word) > 3:  # Ignora palavras muito curtas
                    keywords_count[word] = keywords_count.get(word, 0) + 1
        
        # Ordenar e retornar os tópicos mais frequentes
        sorted_topics = sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)
        return [{'topico': topic, 'frequencia': count} for topic, count in sorted_topics[:limit]]
        
    except Exception as e:
        logger.error(f"Erro ao identificar tópicos em tendência: {e}")
        return []

def get_agent_performance(start_date: datetime, end_date: datetime) -> Dict:
    """
    Obtém métricas de performance por atendente em um período
    
    Args:
        start_date: Data inicial do período
        end_date: Data final do período
        
    Returns:
        Dict com métricas por atendente
    """
    try:
        db = get_firestore_db()
        
        # Consulta mensagens de atendentes no período
        messages_ref = db.collection('mensagens').where(
            filter=firestore.FieldFilter('data_hora', '>=', start_date)
        ).where(
            filter=firestore.FieldFilter('data_hora', '<=', end_date)
        ).where(
            filter=firestore.FieldFilter('remetente_tipo', '==', 'atendente')
        )
        
        agent_metrics = {}
        
        for doc in messages_ref.stream():
            data = doc.to_dict()
            agent_id = data.get('atendente_id')
            
            if agent_id not in agent_metrics:
                agent_metrics[agent_id] = {
                    'total_mensagens': 0,
                    'tempo_medio_resposta': 0,
                    'total_tempo_resposta': 0,
                    'contador_tempo_resposta': 0
                }
            
            agent_metrics[agent_id]['total_mensagens'] += 1
            
            # Calcular tempo de resposta
            if 'tempo_resposta' in data:
                agent_metrics[agent_id]['total_tempo_resposta'] += data['tempo_resposta']
                agent_metrics[agent_id]['contador_tempo_resposta'] += 1
        
        # Calcular médias
        for agent_id, metrics in agent_metrics.items():
            if metrics['contador_tempo_resposta'] > 0:
                metrics['tempo_medio_resposta'] = metrics['total_tempo_resposta'] / metrics['contador_tempo_resposta']
            del metrics['total_tempo_resposta']
            del metrics['contador_tempo_resposta']
        
        return {
            'periodo': {
                'inicio': start_date,
                'fim': end_date
            },
            'atendentes': agent_metrics
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de atendentes: {e}")
        return {} 