"""
Biblioteca central de prompts para os agentes de IA.
Esta biblioteca contém todos os prompts utilizados pelos agentes para análise
de mensagens, detecção de solicitações, avaliação de atendimento, etc.
"""

import os
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Versão da biblioteca de prompts
PROMPTS_VERSION = "2.0.0"

class PromptLibrary:
    """
    Biblioteca central de prompts para os agentes de IA.
    """
    
    @staticmethod
    def get_prompt_version() -> str:
        """Retorna a versão atual da biblioteca de prompts."""
        return PROMPTS_VERSION
    
    @staticmethod
    def get_message_analysis_prompt(message: str) -> str:
        """
        Gera o prompt para análise de uma mensagem individual.
        
        Args:
            message: Texto da mensagem a ser analisada
            
        Returns:
            Prompt formatado para análise da mensagem
        """
        return f"""
        Analise a seguinte mensagem e responda com as informações solicitadas:

        MENSAGEM: "{message}"

        Responda com:
        1. Intenção principal (pergunta, solicitação, reclamação, elogio, informação, despedida, saudação)
        2. Sentimento (positivo, negativo, neutro)
        3. Nível de urgência (baixa, média, alta)
        4. É uma reclamação? (sim/não)
        5. Contém uma solicitação que requer ação? (sim/não)
        6. Menciona algum prazo? (sim/não)
        7. Indica encerramento da conversa? (sim/não)
        8. Tópicos principais mencionados (lista separada por vírgulas)
        """
    
    @staticmethod
    def get_request_detection_prompt(conversation_context: str, message: str) -> str:
        """
        Gera o prompt para detectar solicitações e prazos em uma mensagem.
        
        Args:
            conversation_context: Contexto recente da conversa
            message: Texto da mensagem atual
            
        Returns:
            Prompt formatado para detecção de solicitações
        """
        return f"""
        Analise a mensagem e identifique solicitações e prazos:

        CONTEXTO RECENTE:
        {conversation_context}

        MENSAGEM ATUAL: "{message}"

        Responda com:
        1. Contém solicitação? (sim/não)
        2. Se sim, descreva a solicitação
        3. Menciona prazo? (sim/não)
        4. Se sim, qual o prazo mencionado?
        5. Prioridade da solicitação (baixa, média, alta)
        """
    
    @staticmethod
    def get_conversation_closure_prompt(messages: List[Dict[str, Any]]) -> str:
        """
        Gera um prompt para verificação de encerramento de uma conversa.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            Prompt para verificação de encerramento
        """
        conversation_text = "\n".join([
            f"[{msg.get('remetente', 'desconhecido')}]: {msg.get('conteudo', '')}"
            for msg in messages
        ])
        
        prompt = f"""
        Analise a seguinte conversa entre um atendente e um cliente e determine se a conversa deve ser considerada encerrada.

        Conversa:
        {conversation_text}

        ===

        Uma conversa deve ser considerada encerrada quando:
        1. O cliente expressa gratidão e encerra a interação ("obrigado", "valeu", "agradeço", etc.)
        2. O cliente diz de forma explícita que não precisa de mais ajuda
        3. O cliente utiliza despedidas como "até logo", "tchau", etc.
        4. O cliente confirma que o problema foi resolvido ("resolvido", "solucionado", etc.)
        5. O atendente pergunta se o cliente precisa de mais alguma coisa/ajuda e o cliente responde negativamente (com "não", "não preciso", "não, obrigado", "só isso", etc.)
        6. Houve a resolução do problema e uma despedida clara

        ===
        
        Responda APENAS com as seguintes informações:
        SHOULD_CLOSE: [sim/nao]
        CONFIDENCE: [0-100]
        REASON: [motivo]
        """
        
        return prompt
    
    @staticmethod
    def get_evaluation_prompt(conversation_data: Dict[str, Any], messages: List[Dict[str, Any]], requests: List[Dict[str, Any]]) -> str:
        """
        Gera o prompt para avaliação completa de um atendimento.
        
        Args:
            conversation_data: Dados da conversa
            messages: Lista completa de mensagens da conversa
            requests: Lista de solicitações identificadas
            
        Returns:
            Prompt formatado para avaliação da conversa
        """
        messages_text = "\n".join([
            f"[{msg.get('timestamp', '')}] [{msg.get('remetente', 'desconhecido')}]: {msg.get('conteudo', '')}"
            for msg in messages
        ])
        
        requests_text = "\n".join([
            f"- {req.get('descricao', '')}, Prazo: {req.get('prazo_prometido', 'Não especificado')}, Status: {req.get('status', 'Não informado')}"
            for req in requests
        ]) if requests else "Nenhuma solicitação registrada."
        
        return f"""
        Avalie o atendimento com base nas mensagens e solicitações:

        CONVERSA COMPLETA:
        {messages_text}

        SOLICITAÇÕES:
        {requests_text}

        Responda com:
        1. Nota de comunicação (0-10)
        2. Nota de conhecimento técnico (0-10)
        3. Nota de empatia/cordialidade (0-10) - PESO TRIPLO
        4. Nota de profissionalismo (0-10)
        5. Nota de resultados (0-10)
        6. Nota de inteligência emocional (0-10)
        7. Nota de cumprimento de prazos (0-10)
        8. Nota geral (considere peso triplo para empatia)
        9. Reclamações detectadas (lista)
        10. Solicitações não atendidas (lista)
        11. Solicitações atrasadas (lista)
        12. Pontos positivos (lista)
        13. Pontos negativos (lista)
        14. Sugestões de melhoria (lista)

        REGRA IMPORTANTE: Se houver reclamação sobre falta de cordialidade, a nota final deve ser 0.
        """
    
    @staticmethod
    def get_complaint_detection_prompt(messages: List[Dict[str, Any]]) -> str:
        """
        Gera o prompt para detectar reclamações em uma conversa.
        
        Args:
            messages: Lista de mensagens da conversa
            
        Returns:
            Prompt formatado para detecção de reclamações
        """
        cliente_messages = [msg for msg in messages if msg.get('remetente', '') == 'cliente']
        messages_text = "\n".join([
            f"[{msg.get('timestamp', '')}]: {msg.get('conteudo', '')}"
            for msg in cliente_messages
        ])
        
        return f"""
        Analise as mensagens do cliente e identifique reclamações:

        MENSAGENS DO CLIENTE:
        {messages_text}

        Responda com:
        1. Há reclamações? (sim/não)
        2. Se sim, liste as reclamações identificadas
        3. Gravidade de cada reclamação (baixa, média, alta)
        4. Tópico de cada reclamação
        5. Sentimento geral do cliente (muito negativo, negativo, neutro, positivo)
        6. Nível de satisfação (0-10)
        """
    
    @staticmethod
    def get_summary_prompt(conversation_data: Dict[str, Any], messages: List[Dict[str, Any]], evaluation_data: Dict[str, Any]) -> str:
        """
        Gera o prompt para criar um resumo consolidado do atendimento.
        
        Args:
            conversation_data: Dados da conversa
            messages: Lista de mensagens da conversa
            evaluation_data: Dados da avaliação
            
        Returns:
            Prompt formatado para geração de resumo
        """
        cliente_nome = conversation_data.get('cliente', {}).get('nome', 'Cliente')
        data_inicio = conversation_data.get('dataHoraInicio', 'Data não disponível')
        
        messages_sample = [msg for msg in messages[:5]] + [msg for msg in messages[-5:]]
        messages_text = "\n".join([
            f"[{msg.get('timestamp', '')}] [{msg.get('remetente', 'desconhecido')}]: {msg.get('conteudo', '')}"
            for msg in messages_sample
        ])
        
        return f"""
        Crie um resumo do atendimento:

        DADOS DO ATENDIMENTO:
        Cliente: {cliente_nome}
        Data de início: {data_inicio}
        Total de mensagens: {len(messages)}

        AMOSTRA DE MENSAGENS:
        {messages_text}

        AVALIAÇÃO:
        Nota geral: {evaluation_data.get('nota_geral', 'Não avaliado')}
        Pontos positivos: {', '.join(evaluation_data.get('pontos_positivos', ['Não disponível']))}
        Pontos negativos: {', '.join(evaluation_data.get('pontos_negativos', ['Não disponível']))}

        Responda com:
        1. Resumo do atendimento (máx. 200 palavras)
        2. Problema principal
        3. Solução aplicada
        4. Status final (resolvido/não resolvido)
        5. Próximos passos (se houver)
        6. Tags para categorização (3-5 tags)
        """

# Funções de conveniência para versões específicas dos prompts
def get_default_message_analysis_prompt(message: str) -> str:
    """Retorna o prompt padrão para análise de mensagem."""
    return PromptLibrary.get_message_analysis_prompt(message)

def get_default_request_detection_prompt(context: str, message: str) -> str:
    """Retorna o prompt padrão para detecção de solicitações."""
    return PromptLibrary.get_request_detection_prompt(context, message)

def get_default_conversation_closure_prompt(messages: List[Dict[str, Any]]) -> str:
    """Retorna o prompt padrão para verificação de encerramento de conversa."""
    return PromptLibrary.get_conversation_closure_prompt(messages)

def get_default_evaluation_prompt(conversation: Dict[str, Any], messages: List[Dict[str, Any]], requests: List[Dict[str, Any]]) -> str:
    """Retorna o prompt padrão para avaliação de atendimento."""
    return PromptLibrary.get_evaluation_prompt(conversation, messages, requests)

def get_default_complaint_detection_prompt(messages: List[Dict[str, Any]]) -> str:
    """Retorna o prompt padrão para detecção de reclamações."""
    return PromptLibrary.get_complaint_detection_prompt(messages)

def get_default_summary_prompt(conversation: Dict[str, Any], messages: List[Dict[str, Any]], evaluation: Dict[str, Any]) -> str:
    """Retorna o prompt padrão para geração de resumo."""
    return PromptLibrary.get_summary_prompt(conversation, messages, evaluation)

def get_farewell_detection_prompt(self, message: str) -> str:
    """
    Gera prompt para detecção de despedida em uma mensagem.
    
    Args:
        message: Conteúdo da mensagem
        
    Returns:
        str: Prompt para o modelo
    """
    return f"""
Analise a seguinte mensagem e determine se ela indica uma despedida ou encerramento da conversa.
Considere tanto despedidas formais quanto informais, e também confirmações de entendimento que podem indicar o fim da conversa.

Mensagem: {message}

Responda apenas com 'sim' ou 'não'.
"""

def get_request_detection_prompt(self, conversation_context: str, message: str) -> str:
    """
    Gera prompt para detecção de solicitações e prazos em uma mensagem.
    
    Args:
        conversation_context: Contexto da conversa
        message: Conteúdo da mensagem atual
        
    Returns:
        str: Prompt para o modelo
    """
    return f"""
Analise a seguinte mensagem e contexto para identificar solicitações e prazos.

Contexto da conversa:
{conversation_context}

Mensagem atual:
{message}

Responda com as seguintes informações, uma por linha:
1. Há solicitação? (sim/não)
2. Descrição da solicitação (se houver)
3. Prazo mencionado (se houver)
"""

def get_evaluation_prompt(self, context: Dict[str, Any]) -> str:
    """
    Gera prompt para avaliação de uma conversa.
    
    Args:
        context: Dicionário com contexto da avaliação
        
    Returns:
        str: Prompt para o modelo
    """
    messages = context.get('messages', [])
    requests = context.get('requests', [])
    conversation = context.get('conversation', {})
    
    return f"""
Analise a seguinte conversa e atribua notas de 0 a 10 para cada critério:

Conversa ID: {conversation.get('id')}
Cliente: {conversation.get('cliente', {}).get('nome', 'Desconhecido')}
Data/Hora: {conversation.get('dataHoraInicio')}

Mensagens:
{self._format_messages(messages)}

Solicitações:
{self._format_requests(requests)}

Critérios de avaliação:
1. Comunicação Clara (clareza, objetividade)
2. Conhecimento Técnico (domínio do assunto)
3. Empatia/Cordialidade (tratamento, respeito)
4. Profissionalismo/Ética (postura profissional)
5. Orientação a Resultados (foco na solução)
6. Inteligência Emocional (manejo de situações)
7. Cumprimento de Prazos (respeito aos prazos)
8. Reclamações Detectadas (lista de reclamações)
9. Detalhes Críticos (observações importantes)

Responda com as notas e informações, uma por linha, no formato:
1. Nota Comunicação: [0-10]
2. Nota Conhecimento: [0-10]
3. Nota Empatia: [0-10]
4. Nota Profissionalismo: [0-10]
5. Nota Resultados: [0-10]
6. Nota Inteligência Emocional: [0-10]
7. Nota Prazos: [0-10]
8. Reclamações: [lista separada por vírgulas]
9. Detalhes: [texto livre]
"""

def get_summary_prompt(self, context: Dict[str, Any]) -> str:
    """
    Gera prompt para resumo de uma conversa.
    
    Args:
        context: Dicionário com contexto da conversa
        
    Returns:
        str: Prompt para o modelo
    """
    messages = context.get('messages', [])
    conversation = context.get('conversation', {})
    
    return f"""
Gere um resumo conciso da seguinte conversa, destacando os pontos principais:

Conversa ID: {conversation.get('id')}
Cliente: {conversation.get('cliente', {}).get('nome', 'Desconhecido')}
Data/Hora: {conversation.get('dataHoraInicio')}

Mensagens:
{self._format_messages(messages)}

O resumo deve ser objetivo e conter:
- Contexto inicial
- Problema principal
- Solução aplicada
- Resultado final

Responda com o resumo em um único parágrafo.
"""

def _format_messages(self, messages: List[Dict[str, Any]]) -> str:
    """
    Formata mensagens para exibição em prompts.
    
    Args:
        messages: Lista de mensagens
        
    Returns:
        str: Mensagens formatadas
    """
    formatted = []
    for msg in messages:
        sender = msg.get('sender', 'Desconhecido')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        formatted.append(f"[{timestamp}] {sender}: {content}")
    return "\n".join(formatted)

def _format_requests(self, requests: List[Dict[str, Any]]) -> str:
    """
    Formata solicitações para exibição em prompts.
    
    Args:
        requests: Lista de solicitações
        
    Returns:
        str: Solicitações formatadas
    """
    formatted = []
    for req in requests:
        desc = req.get('description', '')
        status = req.get('status', '')
        deadline = req.get('deadline', '')
        formatted.append(f"- {desc} (Status: {status}, Prazo: {deadline})")
    return "\n".join(formatted) 