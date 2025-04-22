import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dotenv import load_dotenv
from .conversation_processor import ConversationProcessor
from .ollama_integration import OllamaIntegration
from .prompts_library import PromptLibrary

# Carregar variáveis de ambiente
load_dotenv()

class EvaluationManager:
    """
    Gerenciador de avaliações de atendimento.
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de avaliações.
        """
        self.conversation_processor = ConversationProcessor()
        self.ollama = OllamaIntegration()
        self.prompt_library = PromptLibrary()
        
        # Pesos para cada critério de avaliação
        self.weights = {
            'communication': 0.15,      # Análise de comunicação
            'technical': 0.20,          # Conhecimento técnico
            'empathy': 0.15 * 3,        # Empatia e cordialidade (PESO TRIPLO)
            'professionalism': 0.15,    # Profissionalismo
            'results': 0.20,            # Resultados obtidos
            'emotional_intelligence': 0.10,  # Inteligência emocional
            'deadlines': 0.05           # Cumprimento de prazos
        }
        
        # Normalize os pesos para garantir que somem 1
        total_weight = sum(self.weights.values())
        self.weights = {k: v/total_weight for k, v in self.weights.items()}
        
        # Limites de tempo para diferentes tipos de solicitações (em horas)
        self.deadlines = {
            'urgent': 1,
            'high': 4,
            'medium': 8,
            'low': 24
        }
        
        logger.info("Gerenciador de avaliações inicializado")
    
    def evaluate_conversation(self, conversation: Dict, messages: List[Dict]) -> Dict:
        """
        Avalia uma conversa completa.
        
        Args:
            conversation: Dados da conversa
            messages: Lista de mensagens da conversa
            
        Returns:
            Dicionário com os resultados da avaliação
        """
        try:
            # Usar a integração com Ollama para avaliar a conversa completa
            requests = conversation.get('solicitacoes', [])
            
            # Gera o prompt de avaliação
            prompt = self.prompt_library.get_evaluation_prompt(conversation, messages, requests)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            evaluation = {
                'comunicacao_nota': float(lines[0].split(': ')[1].strip()),
                'conhecimento_nota': float(lines[1].split(': ')[1].strip()),
                'empatia_nota': float(lines[2].split(': ')[1].strip()),
                'profissionalismo_nota': float(lines[3].split(': ')[1].strip()),
                'resultados_nota': float(lines[4].split(': ')[1].strip()),
                'emocional_nota': float(lines[5].split(': ')[1].strip()),
                'cumprimento_prazos_nota': float(lines[6].split(': ')[1].strip()),
                'nota_geral': float(lines[7].split(': ')[1].strip()),
                'reclamacoes_detectadas': [r.strip() for r in lines[8].split(': ')[1].split(',')],
                'solicitacoes_nao_atendidas': [s.strip() for s in lines[9].split(': ')[1].split(',')],
                'solicitacoes_atrasadas': [s.strip() for s in lines[10].split(': ')[1].split(',')],
                'pontos_positivos': [p.strip() for p in lines[11].split(': ')[1].split(',')],
                'pontos_negativos': [p.strip() for p in lines[12].split(': ')[1].split(',')],
                'sugestoes_melhoria': [s.strip() for s in lines[13].split(': ')[1].split(',')]
            }
            
            # Se houver reclamações sobre cordialidade, zeramos a nota de empatia
            for complaint in evaluation['reclamacoes_detectadas']:
                if 'cordialidade' in complaint.lower() or 'educação' in complaint.lower():
                    evaluation['empatia_nota'] = 0
                    evaluation['nota_geral'] = 0
                    break
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Erro ao avaliar conversa: {e}")
            return {
                'comunicacao_nota': 0,
                'conhecimento_nota': 0,
                'empatia_nota': 0,
                'profissionalismo_nota': 0,
                'resultados_nota': 0,
                'emocional_nota': 0,
                'cumprimento_prazos_nota': 0,
                'nota_geral': 0,
                'reclamacoes_detectadas': [f"Erro na avaliação: {str(e)}"],
                'solicitacoes_nao_atendidas': [],
                'solicitacoes_atrasadas': [],
                'pontos_positivos': [],
                'pontos_negativos': [],
                'sugestoes_melhoria': [],
                'data_avaliacao': datetime.now()
            }
    
    def _analyze_communication(self, messages: List[Dict]) -> float:
        """
        Analisa a qualidade da comunicação.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Filtra apenas mensagens do atendente
            atendente_msgs = [msg for msg in messages if msg.get('remetente') == 'atendente']
            
            if not atendente_msgs:
                return 0
            
            # Extrai textos das mensagens do atendente
            texts = [msg.get('conteudo', '') for msg in atendente_msgs]
            
            # Usa análise de sentimento e clareza como proxy para comunicação
            # Em uma implementação real, usaríamos um modelo treinado específico
            score = 0.7  # Valor padrão moderado
            
            return score
            
        except Exception as e:
            logger.error(f"Erro ao analisar comunicação: {e}")
            return 0
    
    def _analyze_technical_knowledge(self, messages: List[Dict]) -> float:
        """
        Analisa o conhecimento técnico demonstrado.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Esta é uma implementação simplificada
            # Em uma implementação real, treinaria um modelo para isso
            return 0.8
            
        except Exception as e:
            logger.error(f"Erro ao analisar conhecimento técnico: {e}")
            return 0
    
    def _analyze_empathy(self, messages: List[Dict]) -> float:
        """
        Analisa o nível de empatia e cordialidade.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Detectar reclamações sobre falta de cordialidade
            complaints = self._detect_complaints(messages)
            
            # Se houver reclamações sobre cordialidade, zeramos o score
            for complaint in complaints:
                if 'cordialidade' in complaint.get('text', '').lower() or 'educação' in complaint.get('text', '').lower():
                    return 0
            
            # Esta é uma implementação simplificada
            # Em uma implementação real, treinaria um modelo para isso
            return 0.75
            
        except Exception as e:
            logger.error(f"Erro ao analisar empatia: {e}")
            return 0
    
    def _analyze_professionalism(self, messages: List[Dict]) -> float:
        """
        Analisa o nível de profissionalismo.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Esta é uma implementação simplificada
            # Em uma implementação real, treinaria um modelo para isso
            return 0.8
            
        except Exception as e:
            logger.error(f"Erro ao analisar profissionalismo: {e}")
            return 0
    
    def _analyze_results(self, messages: List[Dict]) -> float:
        """
        Analisa os resultados obtidos no atendimento.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Esta é uma implementação simplificada
            # Em uma implementação real, treinaria um modelo para isso
            return 0.7
            
        except Exception as e:
            logger.error(f"Erro ao analisar resultados: {e}")
            return 0
    
    def _analyze_emotional_intelligence(self, messages: List[Dict]) -> float:
        """
        Analisa a inteligência emocional demonstrada.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Esta é uma implementação simplificada
            # Em uma implementação real, treinaria um modelo para isso
            return 0.75
            
        except Exception as e:
            logger.error(f"Erro ao analisar inteligência emocional: {e}")
            return 0
    
    def _analyze_deadlines(self, conversation: Dict, messages: List[Dict]) -> float:
        """
        Verifica o cumprimento de prazos nas solicitações.
        
        Args:
            conversation: Dados da conversa
            messages: Lista de mensagens
            
        Returns:
            Score entre 0 e 1
        """
        try:
            # Obter solicitações da conversa
            requests = conversation.get('solicitacoes', [])
            
            if not requests:
                return 0.8  # Nota padrão se não houver solicitações
            
            # Conta solicitações cumpridas, não cumpridas e atrasadas
            fulfilled = 0
            unfulfilled = 0
            delayed = 0
            
            for request in requests:
                status = request.get('status', '').upper()
                
                if status == 'FULFILLED' or status == 'COMPLETED':
                    if self._is_request_delayed(request):
                        delayed += 1
                    else:
                        fulfilled += 1
                elif status == 'UNFULFILLED' or status == 'PENDING':
                    unfulfilled += 1
            
            total = fulfilled + unfulfilled + delayed
            
            if total == 0:
                return 0.8  # Nota padrão se não houver solicitações válidas
            
            # Penaliza pela proporção de solicitações não atendidas ou atrasadas
            penalty_unfulfilled = unfulfilled / total
            penalty_delayed = 0.5 * (delayed / total)  # Metade da penalidade para atrasos
            
            score = 1.0 - (penalty_unfulfilled + penalty_delayed)
            
            return max(0, min(1, score))  # Garante que fica entre 0 e 1
            
        except Exception as e:
            logger.error(f"Erro ao analisar cumprimento de prazos: {e}")
            return 0
    
    def _is_request_delayed(self, request: Dict) -> bool:
        """
        Verifica se uma solicitação foi atendida com atraso.
        
        Args:
            request: Dados da solicitação
            
        Returns:
            True se atrasada, False caso contrário
        """
        try:
            # Obter datas
            promised_date = request.get('prazo_prometido')
            fulfilled_date = request.get('data_atendimento')
            
            if not promised_date or not fulfilled_date:
                return False
            
            # Converter para datetime se necessário
            if isinstance(promised_date, str):
                promised_date = datetime.fromisoformat(promised_date)
            if isinstance(fulfilled_date, str):
                fulfilled_date = datetime.fromisoformat(fulfilled_date)
            
            return fulfilled_date > promised_date
            
        except Exception as e:
            logger.error(f"Erro ao verificar atraso: {e}")
            return False
    
    def _detect_complaints(self, messages: List[Dict]) -> List[Dict]:
        """
        Detecta reclamações nas mensagens.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Lista de reclamações detectadas
        """
        try:
            # Gera o prompt de detecção de reclamações
            prompt = self.prompt_library.get_complaint_detection_prompt(messages)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            complaints = []
            
            for line in lines:
                if line.strip():
                    parts = line.split(': ')
                    if len(parts) == 2:
                        complaints.append({
                            'text': parts[1].strip(),
                            'severity': 'high' if 'grave' in parts[0].lower() else 'medium'
                        })
            
            return complaints
            
        except Exception as e:
            logger.error(f"Erro ao detectar reclamações: {e}")
            return []
    
    def _check_unaddressed_requests(self, messages: List[Dict]) -> List[str]:
        """
        Verifica solicitações não atendidas.
        
        Args:
            messages: Lista de mensagens
            
        Returns:
            Lista de solicitações não atendidas
        """
        try:
            # Gera o prompt de verificação de solicitações
            prompt = self.prompt_library.get_request_detection_prompt(messages)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            unaddressed = []
            
            for line in lines:
                if line.strip():
                    parts = line.split(': ')
                    if len(parts) == 2 and 'não atendida' in parts[0].lower():
                        unaddressed.append(parts[1].strip())
            
            return unaddressed
            
        except Exception as e:
            logger.error(f"Erro ao verificar solicitações não atendidas: {e}")
            return []
    
    def _check_delays(self, conversation: Dict, messages: List[Dict]) -> List[str]:
        """
        Verifica atrasos nas solicitações.
        
        Args:
            conversation: Dados da conversa
            messages: Lista de mensagens
            
        Returns:
            Lista de solicitações atrasadas
        """
        try:
            # Gera o prompt de verificação de atrasos
            prompt = self.prompt_library.get_request_detection_prompt(messages)
            response = self.ollama.generate(prompt)
            
            # Processa a resposta numerada
            lines = response.strip().split('\n')
            delays = []
            
            for line in lines:
                if line.strip():
                    parts = line.split(': ')
                    if len(parts) == 2 and 'atrasada' in parts[0].lower():
                        delays.append(parts[1].strip())
            
            return delays
            
        except Exception as e:
            logger.error(f"Erro ao verificar atrasos: {e}")
            return [] 