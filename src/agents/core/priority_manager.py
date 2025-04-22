import time
from typing import List, Dict, Any
from datetime import datetime
import pytz
from loguru import logger

class PriorityManager:
    """
    Gerenciador de prioridades para avaliação de conversas.
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de prioridades.
        """
        # Configurações de priorização
        self._prioridade_por_tempo = {
            'alta': 3600,  # 1 hora
            'media': 7200,  # 2 horas
            'baixa': 14400  # 4 horas
        }
        
        self._prioridade_por_urgencia = {
            'critica': 1.5,
            'alta': 1.2,
            'normal': 1.0
        }
        
        self._prioridade_por_tipo = {
            'reclamacao': 1.3,
            'solicitacao': 1.2,
            'informacao': 1.0
        }
        
        self._prioridade_por_reabertura = {
            0: 1.0,  # Primeira avaliação
            1: 1.2,  # Primeira reabertura
            2: 1.4,  # Segunda reabertura
            3: 1.6   # Terceira reabertura ou mais
        }
        
        logger.info("Gerenciador de Prioridades inicializado")
    
    def sort_conversations_by_priority(self, conversas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ordena as conversas por prioridade de avaliação.
        
        Args:
            conversas: Lista de conversas a serem ordenadas
            
        Returns:
            Lista de conversas ordenadas por prioridade
        """
        try:
            # Calcular prioridade para cada conversa
            for conversa in conversas:
                conversa['prioridade'] = self._calcular_prioridade_conversa(conversa)
            
            # Ordenar por prioridade (maior primeiro)
            conversas_ordenadas = sorted(
                conversas,
                key=lambda c: c['prioridade'],
                reverse=True
            )
            
            return conversas_ordenadas
            
        except Exception as e:
            logger.error(f"Erro ao ordenar conversas por prioridade: {e}")
            return conversas
    
    def _calcular_prioridade_conversa(self, conversa: Dict[str, Any]) -> float:
        """
        Calcula a prioridade de avaliação de uma conversa.
        
        Args:
            conversa: Dados da conversa
            
        Returns:
            Prioridade calculada
        """
        try:
            # Prioridade baseada no tempo de espera
            tempo_espera = (datetime.now(pytz.UTC) - conversa['start_time']).total_seconds()
            prioridade_tempo = 1.0
            
            for nivel, limite in self._prioridade_por_tempo.items():
                if tempo_espera <= limite:
                    prioridade_tempo = 1.0 / (tempo_espera / limite)
                    break
            
            # Prioridade baseada no tipo de solicitação
            prioridade_tipo = self._prioridade_por_tipo.get(conversa['request_type'], 1.0)
            
            # Prioridade baseada em reclamações
            prioridade_reclamacao = 1.0
            for msg in conversa['messages']:
                if msg['role'] == 'client':
                    content = msg['content'].lower()
                    if any(term in content for term in ['reclama', 'queixa', 'insatisf', 'problema']):
                        prioridade_reclamacao = self._prioridade_por_urgencia['critica']
                        break
            
            # Prioridade baseada em urgência
            prioridade_urgencia = self._prioridade_por_urgencia['normal']
            for msg in conversa['messages']:
                if msg['role'] == 'client':
                    content = msg['content'].lower()
                    if any(term in content for term in ['urgente', 'urgência', 'emergência', 'emergencia']):
                        prioridade_urgencia = self._prioridade_por_urgencia['alta']
                        break
            
            # Prioridade baseada em reaberturas
            prioridade_reabertura = self._prioridade_por_reabertura.get(
                conversa['reopen_count'],
                self._prioridade_por_reabertura[3]  # Usar valor máximo para mais de 3 reaberturas
            )
            
            # Cálculo da prioridade final
            prioridade_final = (
                prioridade_tempo *
                prioridade_tipo *
                prioridade_reclamacao *
                prioridade_urgencia *
                prioridade_reabertura
            )
            
            return prioridade_final
            
        except Exception as e:
            logger.error(f"Erro ao calcular prioridade da conversa: {e}")
            return 1.0 