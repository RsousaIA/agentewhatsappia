import re
import datetime
import logging
from typing import Dict, Any, List, Optional
from .ollama_integration import OllamaIntegration

logger = logging.getLogger(__name__)

class ConversationProcessor:
    """
    Processa mensagens de conversas e extrai informações relevantes usando IA.
    """
    def __init__(self):
        """
        Inicializa o processador de conversas.
        """
        self.ollama = OllamaIntegration()
        self.request_patterns = self._load_request_patterns()
        self.deadline_patterns = self._load_deadline_patterns()

    def process(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa uma mensagem e extrai informações relevantes usando IA.
        
        Args:
            message_data: Dados da mensagem
            
        Returns:
            Dict com dados processados para atualizar a conversa
        """
        try:
            updates = {}
            
            # Processa o texto da mensagem
            text = message_data.get('content', '')
            
            # Usa o Ollama para análise avançada
            entities = self.ollama.extract_entities(text)
            sentiment = self.ollama.analyze_sentiment(text)
            
            # Processa solicitações
            if message_data.get('sender_type') == 'client':
                if entities.get('requests'):
                    updates['has_request'] = True
                    updates['request_description'] = entities['requests'][0]
                    updates['request_priority'] = entities.get('priorities', ['medium'])[0]
            
            # Processa prazos
            if message_data.get('sender_type') == 'agent':
                if entities.get('deadlines'):
                    deadline = entities['deadlines'][0]
                    updates['has_deadline'] = True
                    updates['deadline_date'] = deadline.get('date')
                    updates['deadline_business_days'] = deadline.get('business_days')
            
            # Adiciona análise de sentimento
            if sentiment:
                updates['sentiment'] = sentiment.get('sentiment', 'neutral')
                updates['sentiment_confidence'] = sentiment.get('confidence', 0.0)
                updates['sentiment_key_phrases'] = sentiment.get('key_phrases', [])
            
            return updates
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return {}

    def _calculate_business_days(self, days: int) -> int:
        """
        Calcula o número de dias úteis a partir de um número de dias corridos.
        """
        current_date = datetime.datetime.now()
        end_date = current_date + datetime.timedelta(days=days)
        
        business_days = 0
        current = current_date
        while current <= end_date:
            if current.weekday() < 5:  # 0-4 são dias úteis (seg-sex)
                business_days += 1
            current += datetime.timedelta(days=1)
        
        return business_days

    def _load_request_patterns(self) -> List[Dict[str, Any]]:
        """
        Carrega padrões para detecção de solicitações.
        """
        return [
            {
                'regex': re.compile(r'preciso\s+de\s+ajuda'),
                'description': 'Solicitação de ajuda geral',
                'priority': 'medium'
            },
            {
                'regex': re.compile(r'urgente|emergência'),
                'description': 'Solicitação urgente',
                'priority': 'high'
            },
            {
                'regex': re.compile(r'quando\s+(?:vocês?|podem|pode)\s+(?:resolver|consertar)'),
                'description': 'Solicitação de prazo',
                'priority': 'medium'
            }
        ]

    def _load_deadline_patterns(self) -> List[Dict[str, Any]]:
        """
        Carrega padrões para detecção de prazos.
        """
        return [
            {
                'regex': re.compile(r'(?:em|até)\s+(\d+)\s+dias?'),
                'type': 'days'
            },
            {
                'regex': re.compile(r'(?:em|até)\s+(\d+)\s+semanas?'),
                'type': 'weeks',
                'multiplier': 7
            }
        ] 