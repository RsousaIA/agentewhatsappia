from typing import Dict, List, Optional, Union, Tuple
import firebase_admin
from firebase_admin import firestore
from loguru import logger
from datetime import datetime

class ConsolidatedMetrics:
    """
    Classe responsável por gerenciar métricas consolidadas das avaliações.
    Centraliza operações de acesso, atualização e cálculo de métricas.
    """
    
    def __init__(self, firestore_client=None):
        """
        Inicializa a classe de métricas consolidadas.
        
        Args:
            firestore_client: Cliente opcional do Firestore. Se não for fornecido,
                              o cliente padrão será utilizado.
        """
        self.db = firestore_client if firestore_client else firestore.client()
        self.metrics_ref = self.db.collection('metricas_consolidadas')
        
    def update_metrics_after_evaluation(self, 
                                        evaluation_data: Dict,
                                        conversation_data: Dict) -> bool:
        """
        Atualiza as métricas consolidadas após uma avaliação.
        
        Args:
            evaluation_data: Dados da avaliação realizada
            conversation_data: Dados da conversa avaliada
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        try:
            # Extrair métricas relevantes da avaliação
            metrics = self._extract_metrics_from_evaluation(evaluation_data, conversation_data)
            
            # Obter o documento de métricas atual ou criar um novo
            metrics_doc = self._get_or_create_metrics_document()
            
            # Atualizar métricas
            self._update_metrics_document(metrics_doc.id, metrics)
            
            logger.info(f"Métricas consolidadas atualizadas com sucesso após avaliação")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas consolidadas: {str(e)}")
            return False
            
    def _extract_metrics_from_evaluation(self, 
                                         evaluation_data: Dict,
                                         conversation_data: Dict) -> Dict:
        """
        Extrai métricas relevantes dos dados de avaliação.
        
        Args:
            evaluation_data: Dados da avaliação
            conversation_data: Dados da conversa
            
        Returns:
            Dict: Dicionário com as métricas extraídas
        """
        # Extrair informações básicas
        tempo_resposta = evaluation_data.get('tempo_resposta', 0)
        satisfacao = evaluation_data.get('satisfacao', 0)
        eficiencia = evaluation_data.get('eficiencia', 0)
        assertividade = evaluation_data.get('assertividade', 0)
        
        # Calcular NPS (-100 a 100)
        nps = evaluation_data.get('nps', 0)
        
        # Extrair categoria da conversa (se disponível)
        categoria = conversation_data.get('categoria', 'não_categorizado')
        
        # Extrair outros metadados úteis
        timestamp = datetime.now()
        
        return {
            'tempo_resposta': tempo_resposta,
            'satisfacao': satisfacao,
            'eficiencia': eficiencia,
            'assertividade': assertividade,
            'nps': nps,
            'categoria': categoria,
            'timestamp': timestamp
        }
        
    def _get_or_create_metrics_document(self):
        """
        Obtém o documento de métricas atual ou cria um novo se não existir.
        
        Returns:
            DocumentReference: Referência para o documento de métricas
        """
        # Verificar se existe um documento de métricas
        metrics_query = self.metrics_ref.limit(1).get()
        
        if len(metrics_query) > 0:
            return metrics_query[0].reference
        
        # Criar novo documento de métricas se não existir
        return self.metrics_ref.document()
        
    def _update_metrics_document(self, doc_id: str, metrics: Dict) -> bool:
        """
        Atualiza o documento de métricas com novas informações.
        
        Args:
            doc_id: ID do documento de métricas
            metrics: Novas métricas a serem consolidadas
            
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        try:
            doc_ref = self.metrics_ref.document(doc_id)
            doc_data = doc_ref.get().to_dict() or {}
            
            # Inicializar arrays se não existirem
            if 'avaliacoes' not in doc_data:
                doc_data['avaliacoes'] = []
                
            if 'historico_nps' not in doc_data:
                doc_data['historico_nps'] = []
                
            # Adicionar nova avaliação ao histórico
            doc_data['avaliacoes'].append({
                'tempo_resposta': metrics['tempo_resposta'],
                'satisfacao': metrics['satisfacao'],
                'eficiencia': metrics['eficiencia'],
                'assertividade': metrics['assertividade'],
                'categoria': metrics['categoria'],
                'timestamp': metrics['timestamp']
            })
            
            # Adicionar NPS ao histórico
            doc_data['historico_nps'].append({
                'valor': metrics['nps'],
                'timestamp': metrics['timestamp']
            })
            
            # Calcular médias atualizadas
            doc_data['media_tempo_resposta'] = self._calculate_average(
                [a['tempo_resposta'] for a in doc_data['avaliacoes']]
            )
            
            doc_data['media_satisfacao'] = self._calculate_average(
                [a['satisfacao'] for a in doc_data['avaliacoes']]
            )
            
            doc_data['media_eficiencia'] = self._calculate_average(
                [a['eficiencia'] for a in doc_data['avaliacoes']]
            )
            
            doc_data['media_assertividade'] = self._calculate_average(
                [a['assertividade'] for a in doc_data['avaliacoes']]
            )
            
            # Calcular NPS global
            doc_data['nps_global'] = self._calculate_global_nps(
                [n['valor'] for n in doc_data['historico_nps']]
            )
            
            # Atualizar contagens
            doc_data['total_avaliacoes'] = len(doc_data['avaliacoes'])
            doc_data['ultima_atualizacao'] = metrics['timestamp']
            
            # Salvar documento atualizado
            doc_ref.set(doc_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar documento de métricas: {str(e)}")
            return False
            
    def _calculate_average(self, values: List[float]) -> float:
        """
        Calcula a média de uma lista de valores.
        
        Args:
            values: Lista de valores
            
        Returns:
            float: Média calculada
        """
        if not values:
            return 0
        return sum(values) / len(values)
        
    def _calculate_global_nps(self, nps_values: List[int]) -> int:
        """
        Calcula o NPS global com base em todas as avaliações.
        Utiliza a fórmula padrão do NPS: % Promotores - % Detratores
        
        Args:
            nps_values: Lista de valores de NPS individuais
            
        Returns:
            int: NPS global calculado
        """
        if not nps_values:
            return 0
            
        # Contagem de promotores e detratores
        promoters = sum(1 for nps in nps_values if nps == 100)
        detractors = sum(1 for nps in nps_values if nps == -100)
        
        # Calcular porcentagens
        total = len(nps_values)
        promoters_pct = (promoters / total) * 100 if total > 0 else 0
        detractors_pct = (detractors / total) * 100 if total > 0 else 0
        
        # Fórmula do NPS
        return int(promoters_pct - detractors_pct)
        
    def get_current_metrics(self) -> Dict:
        """
        Obtém as métricas consolidadas atuais.
        
        Returns:
            Dict: Métricas consolidadas
        """
        try:
            metrics_query = self.metrics_ref.limit(1).get()
            
            if len(metrics_query) > 0:
                return metrics_query[0].to_dict() or {}
            
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas consolidadas: {str(e)}")
            return {} 