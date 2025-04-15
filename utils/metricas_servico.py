import sys
import os
import datetime
from contextlib import contextmanager
import statistics

# Adicionando o diretório raiz ao path para importar módulos
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from database.models import Avaliacao, Conversa, Atendente, Solicitacao, SolicitacaoStatus
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

def calcular_tempo_medio_resposta():
    """Calcula o tempo médio de resposta em minutos"""
    try:
        with safe_db_session() as session:
            # Seleciona todas as solicitações com data_criacao e data_primeiro_atendimento
            solicitacoes = session.query(
                Solicitacao
            ).filter(
                Solicitacao.data_criacao.isnot(None),
                Solicitacao.data_primeiro_atendimento.isnot(None)
            ).all()
            
            if not solicitacoes:
                return None
                
            # Calcula a diferença em minutos para cada solicitação
            tempos = []
            for s in solicitacoes:
                delta = s.data_primeiro_atendimento - s.data_criacao
                tempos.append(delta.total_seconds() / 60)  # Convertendo para minutos
                
            return {
                'media': statistics.mean(tempos) if tempos else 0,
                'mediana': statistics.median(tempos) if tempos else 0,
                'minimo': min(tempos) if tempos else 0,
                'maximo': max(tempos) if tempos else 0
            }
    except Exception as e:
        print(f"Erro ao calcular tempo médio de resposta: {str(e)}")
        return None

def calcular_tempo_medio_resolucao():
    """Calcula o tempo médio de resolução em minutos para solicitações concluídas"""
    try:
        with safe_db_session() as session:
            # Busca status "Concluído" ou similar
            status_concluido = session.query(SolicitacaoStatus).filter(
                SolicitacaoStatus.nome.ilike('%conclu%')
            ).first()
            
            if not status_concluido:
                return None
                
            # Seleciona solicitações concluídas
            solicitacoes = session.query(
                Solicitacao
            ).filter(
                Solicitacao.data_criacao.isnot(None),
                Solicitacao.data_conclusao.isnot(None),
                Solicitacao.status_id == status_concluido.id
            ).all()
            
            if not solicitacoes:
                return None
                
            # Calcula a diferença em minutos
            tempos = []
            for s in solicitacoes:
                delta = s.data_conclusao - s.data_criacao
                tempos.append(delta.total_seconds() / 60)
                
            return {
                'media': statistics.mean(tempos) if tempos else 0,
                'mediana': statistics.median(tempos) if tempos else 0,
                'minimo': min(tempos) if tempos else 0,
                'maximo': max(tempos) if tempos else 0
            }
    except Exception as e:
        print(f"Erro ao calcular tempo médio de resolução: {str(e)}")
        return None

def calcular_pontuacao_media_avaliacoes():
    """Calcula a pontuação média das avaliações"""
    try:
        with safe_db_session() as session:
            avaliacoes = session.query(Avaliacao).all()
            
            if not avaliacoes:
                return None
            
            pontuacoes = {
                'tempo_resposta': [],
                'qualidade': [],
                'resolucao': [],
                'satisfacao': [],
                'final': []
            }
            
            for a in avaliacoes:
                if a.pontuacao_tempo_resposta is not None:
                    pontuacoes['tempo_resposta'].append(a.pontuacao_tempo_resposta)
                if a.pontuacao_qualidade is not None:
                    pontuacoes['qualidade'].append(a.pontuacao_qualidade)
                if a.pontuacao_resolucao is not None:
                    pontuacoes['resolucao'].append(a.pontuacao_resolucao)
                if a.pontuacao_satisfacao is not None:
                    pontuacoes['satisfacao'].append(a.pontuacao_satisfacao)
                if a.pontuacao_final is not None:
                    pontuacoes['final'].append(a.pontuacao_final)
            
            resultado = {}
            for categoria, valores in pontuacoes.items():
                if valores:
                    resultado[categoria] = {
                        'media': statistics.mean(valores),
                        'mediana': statistics.median(valores),
                        'minimo': min(valores),
                        'maximo': max(valores)
                    }
                else:
                    resultado[categoria] = {
                        'media': 0,
                        'mediana': 0,
                        'minimo': 0,
                        'maximo': 0
                    }
            
            return resultado
    except Exception as e:
        print(f"Erro ao calcular pontuação média das avaliações: {str(e)}")
        return None

def calcular_eficiencia_atendentes():
    """Calcula a eficiência dos atendentes baseada em tempo de resolução e pontuação"""
    try:
        with safe_db_session() as session:
            # Query para calcular métricas por atendente
            atendentes = session.query(Atendente).all()
            resultado = []
            
            for atendente in atendentes:
                # Contagem total de solicitações
                total_solicitacoes = session.query(Solicitacao).join(
                    Conversa, Conversa.id == Solicitacao.conversa_id
                ).filter(
                    Conversa.atendente_id == atendente.id
                ).count()
                
                # Solicitações concluídas
                status_concluido = session.query(SolicitacaoStatus).filter(
                    SolicitacaoStatus.nome.ilike('%conclu%')
                ).first()
                
                total_concluidas = 0
                if status_concluido:
                    total_concluidas = session.query(Solicitacao).join(
                        Conversa, Conversa.id == Solicitacao.conversa_id
                    ).filter(
                        Conversa.atendente_id == atendente.id,
                        Solicitacao.status_id == status_concluido.id
                    ).count()
                
                # Média de pontuação final
                avaliacoes = session.query(Avaliacao).join(
                    Conversa, Conversa.id == Avaliacao.conversa_id
                ).filter(
                    Conversa.atendente_id == atendente.id
                ).all()
                
                pontuacao_media = 0
                if avaliacoes:
                    pontuacoes = [a.pontuacao_final for a in avaliacoes if a.pontuacao_final is not None]
                    pontuacao_media = statistics.mean(pontuacoes) if pontuacoes else 0
                
                # Adiciona ao resultado
                resultado.append({
                    'id': atendente.id,
                    'nome': atendente.nome,
                    'email': atendente.email,
                    'total_solicitacoes': total_solicitacoes,
                    'total_concluidas': total_concluidas,
                    'taxa_conclusao': (total_concluidas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0,
                    'pontuacao_media': pontuacao_media
                })
            
            return resultado
    except Exception as e:
        print(f"Erro ao calcular eficiência dos atendentes: {str(e)}")
        return None

def obter_metricas_servico():
    """Função principal que retorna todas as métricas do serviço"""
    try:
        # Obtém todas as métricas
        tempo_resposta = calcular_tempo_medio_resposta()
        tempo_resolucao = calcular_tempo_medio_resolucao()
        pontuacoes = calcular_pontuacao_media_avaliacoes()
        eficiencia_atendentes = calcular_eficiencia_atendentes()
        
        # Total de solicitações por status
        with safe_db_session() as session:
            status_list = session.query(SolicitacaoStatus).all()
            solicitacoes_por_status = {}
            
            for status in status_list:
                count = session.query(Solicitacao).filter(
                    Solicitacao.status_id == status.id
                ).count()
                solicitacoes_por_status[status.nome] = count
        
        return {
            'tempo_medio_resposta': tempo_resposta,
            'tempo_medio_resolucao': tempo_resolucao,
            'pontuacoes_medias': pontuacoes,
            'eficiencia_atendentes': eficiencia_atendentes,
            'solicitacoes_por_status': solicitacoes_por_status
        }
    except Exception as e:
        print(f"Erro ao obter métricas de serviço: {str(e)}")
        return {
            'erro': True,
            'mensagem': f"Erro ao obter métricas de serviço: {str(e)}"
        }

if __name__ == "__main__":
    # Teste da função
    metricas = obter_metricas_servico()
    import json
    print(json.dumps(metricas, indent=4, ensure_ascii=False)) 