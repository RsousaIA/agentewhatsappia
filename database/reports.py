from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
import pandas as pd
from firebase_admin import firestore
from .firebase_db import get_firestore_db
from .analytics import (
    get_conversation_metrics,
    get_satisfaction_metrics,
    get_performance_metrics,
    get_trending_topics,
    get_agent_performance
)

logger = logging.getLogger(__name__)

def generate_daily_report(date: datetime) -> Dict:
    """
    Gera relatório diário com todas as métricas
    
    Args:
        date: Data do relatório
        
    Returns:
        Dict com todas as métricas do dia
    """
    try:
        start_date = datetime(date.year, date.month, date.day)
        end_date = start_date + timedelta(days=1)
        
        # Coletar todas as métricas
        conversation_metrics = get_conversation_metrics(start_date, end_date)
        satisfaction_metrics = get_satisfaction_metrics(start_date, end_date)
        performance_metrics = get_performance_metrics(start_date, end_date)
        trending_topics = get_trending_topics(start_date, end_date)
        agent_metrics = get_agent_performance(start_date, end_date)
        
        # Consolidar relatório
        report = {
            'data': date.strftime('%Y-%m-%d'),
            'conversas': conversation_metrics,
            'satisfacao': satisfaction_metrics,
            'performance': performance_metrics,
            'topicos_tendencia': trending_topics,
            'atendentes': agent_metrics
        }
        
        # Salvar relatório no Firebase
        save_report(report, 'diario')
        
        return report
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório diário: {e}")
        return {}

def generate_weekly_report(start_date: datetime) -> Dict:
    """
    Gera relatório semanal com todas as métricas
    
    Args:
        start_date: Data inicial da semana
        
    Returns:
        Dict com todas as métricas da semana
    """
    try:
        end_date = start_date + timedelta(days=7)
        
        # Coletar todas as métricas
        conversation_metrics = get_conversation_metrics(start_date, end_date)
        satisfaction_metrics = get_satisfaction_metrics(start_date, end_date)
        performance_metrics = get_performance_metrics(start_date, end_date)
        trending_topics = get_trending_topics(start_date, end_date)
        agent_metrics = get_agent_performance(start_date, end_date)
        
        # Consolidar relatório
        report = {
            'periodo': {
                'inicio': start_date.strftime('%Y-%m-%d'),
                'fim': end_date.strftime('%Y-%m-%d')
            },
            'conversas': conversation_metrics,
            'satisfacao': satisfaction_metrics,
            'performance': performance_metrics,
            'topicos_tendencia': trending_topics,
            'atendentes': agent_metrics
        }
        
        # Salvar relatório no Firebase
        save_report(report, 'semanal')
        
        return report
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório semanal: {e}")
        return {}

def generate_monthly_report(date: datetime) -> Dict:
    """
    Gera relatório mensal com todas as métricas
    
    Args:
        date: Data do mês do relatório
        
    Returns:
        Dict com todas as métricas do mês
    """
    try:
        start_date = datetime(date.year, date.month, 1)
        if date.month == 12:
            end_date = datetime(date.year + 1, 1, 1)
        else:
            end_date = datetime(date.year, date.month + 1, 1)
        
        # Coletar todas as métricas
        conversation_metrics = get_conversation_metrics(start_date, end_date)
        satisfaction_metrics = get_satisfaction_metrics(start_date, end_date)
        performance_metrics = get_performance_metrics(start_date, end_date)
        trending_topics = get_trending_topics(start_date, end_date)
        agent_metrics = get_agent_performance(start_date, end_date)
        
        # Consolidar relatório
        report = {
            'mes': date.strftime('%Y-%m'),
            'conversas': conversation_metrics,
            'satisfacao': satisfaction_metrics,
            'performance': performance_metrics,
            'topicos_tendencia': trending_topics,
            'atendentes': agent_metrics
        }
        
        # Salvar relatório no Firebase
        save_report(report, 'mensal')
        
        return report
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório mensal: {e}")
        return {}

def save_report(report: Dict, report_type: str) -> str:
    """
    Salva um relatório no Firebase
    
    Args:
        report: Dados do relatório
        report_type: Tipo do relatório (diario, semanal, mensal)
        
    Returns:
        str: ID do relatório salvo
    """
    try:
        db = get_firestore_db()
        
        # Preparar dados do relatório
        report_data = {
            'tipo': report_type,
            'data_criacao': firestore.SERVER_TIMESTAMP,
            'dados': report
        }
        
        # Salvar no Firebase
        doc_ref = db.collection('relatorios').document()
        doc_ref.set(report_data)
        
        logger.info(f"Relatório {report_type} salvo com sucesso")
        return doc_ref.id
        
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")
        raise

def get_report(report_id: str) -> Optional[Dict]:
    """
    Obtém um relatório específico
    
    Args:
        report_id: ID do relatório
        
    Returns:
        Dict com dados do relatório ou None se não encontrado
    """
    try:
        db = get_firestore_db()
        doc = db.collection('relatorios').document(report_id).get()
        
        if doc.exists:
            return doc.to_dict()
        return None
        
    except Exception as e:
        logger.error(f"Erro ao obter relatório: {e}")
        return None

def export_report_to_excel(report: Dict, filename: str) -> bool:
    """
    Exporta um relatório para Excel
    
    Args:
        report: Dados do relatório
        filename: Nome do arquivo de saída
        
    Returns:
        bool: True se exportado com sucesso
    """
    try:
        # Criar DataFrames para cada seção
        dfs = {}
        
        # Conversas
        if 'conversas' in report:
            dfs['conversas'] = pd.DataFrame([report['conversas']])
        
        # Satisfação
        if 'satisfacao' in report:
            dfs['satisfacao'] = pd.DataFrame([report['satisfacao']])
        
        # Performance
        if 'performance' in report:
            dfs['performance'] = pd.DataFrame([report['performance']])
        
        # Tópicos em Tendência
        if 'topicos_tendencia' in report:
            dfs['topicos_tendencia'] = pd.DataFrame(report['topicos_tendencia'])
        
        # Atendentes
        if 'atendentes' in report:
            agent_data = []
            for agent_id, metrics in report['atendentes'].items():
                metrics['atendente_id'] = agent_id
                agent_data.append(metrics)
            dfs['atendentes'] = pd.DataFrame(agent_data)
        
        # Exportar para Excel
        with pd.ExcelWriter(filename) as writer:
            for sheet_name, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Relatório exportado para {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao exportar relatório para Excel: {e}")
        return False

def get_reports_by_type(report_type: str, limit: int = 10) -> List[Dict]:
    """
    Obtém relatórios por tipo
    
    Args:
        report_type: Tipo do relatório (diario, semanal, mensal)
        limit: Número máximo de relatórios a retornar
        
    Returns:
        Lista de relatórios
    """
    try:
        db = get_firestore_db()
        reports_ref = db.collection('relatorios').where(
            'tipo', '==', report_type
        ).order_by(
            'data_criacao', direction=firestore.Query.DESCENDING
        ).limit(limit)
        
        reports = []
        for doc in reports_ref.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            reports.append(data)
            
        return reports
        
    except Exception as e:
        logger.error(f"Erro ao obter relatórios: {e}")
        return [] 