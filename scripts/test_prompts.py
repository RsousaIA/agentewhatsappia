"""
Script para testar a biblioteca de prompts e a integração com o Ollama.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Adiciona o diretório raiz ao PATH para importar os módulos do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configura o modo de simulação explicitamente
os.environ["OLLAMA_SIMULATION_MODE"] = "true"

from agent.prompts_library import (
    get_default_message_analysis_prompt,
    get_default_request_detection_prompt,
    get_default_conversation_closure_prompt,
    get_default_complaint_detection_prompt,
    PromptLibrary
)
from agent.ollama_integration import (
    analyze_message,
    detect_requests,
    should_close_conversation,
    detect_complaints
)
from loguru import logger

# Configura o logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Carrega variáveis de ambiente
load_dotenv()

def pretty_print_json(data):
    """Imprime dados JSON de forma legível"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def test_prompt_library():
    """Testa a biblioteca de prompts com o Ollama"""
    logger.info("Iniciando testes da biblioteca de prompts...")
    
    # Testa análise de mensagem
    mensagem_teste = "Olá, gostaria de saber onde está meu pedido #12345. Já se passaram 5 dias úteis e ainda não recebi. Preciso urgentemente!"
    
    logger.info("Testando análise de mensagem...")
    resultado = analyze_message(mensagem_teste)
    logger.info("Resultado da análise de mensagem:")
    pretty_print_json(resultado)
    
    # Testa detecção de solicitações
    contexto = "Cliente perguntou sobre status do pedido #12345"
    mensagem_solicitacao = "Ainda não recebi e já se passaram 5 dias úteis. Preciso saber quando vai chegar!"
    
    logger.info("\nTestando detecção de solicitações...")
    resultado = detect_requests(contexto, mensagem_solicitacao)
    logger.info("Resultado da detecção de solicitações:")
    pretty_print_json(resultado)
    
    # Testa verificação de encerramento
    mensagens = [
        {"role": "cliente", "content": "Não, obrigado por toda ajuda!"},
        {"role": "atendente", "content": "Foi um prazer ajudar. Tenha um ótimo dia!"}
    ]
    
    logger.info("\nTestando verificação de encerramento de conversa...")
    resultado = should_close_conversation(mensagens)
    logger.info("Resultado da verificação de encerramento:")
    pretty_print_json(resultado)
    
    # Testa detecção de reclamações
    mensagens_reclamacao = [
        {"role": "cliente", "content": "Olá, gostaria de saber onde está meu pedido #12345"},
        {"role": "atendente", "content": "Olá! Vou verificar para você"},
        {"role": "cliente", "content": "Já se passaram 5 dias úteis e vocês prometeram entregar em 3 dias no máximo!"}
    ]
    
    logger.info("\nTestando detecção de reclamações...")
    resultado = detect_complaints(mensagens_reclamacao)
    logger.info("Resultado da detecção de reclamações:")
    pretty_print_json(resultado)
    
    logger.info("\nTestes concluídos!")

def test_ollama_integration():
    """Testa a integração com o Ollama"""
    print("\n===== TESTANDO INTEGRAÇÃO COM OLLAMA =====")
    
    # Inicializa a integração
    ollama = OllamaIntegration()
    
    # Testa a análise de mensagem
    message = "Olá, preciso de ajuda com meu pedido #12345. Ainda não recebi e já se passaram 5 dias úteis."
    
    print(f"\nAnalisando mensagem: '{message}'")
    try:
        result = ollama.analyze_message(message)
        print("\n--- Resultado da análise de mensagem ---")
        pretty_print_json(result)
    except Exception as e:
        logger.error(f"Erro ao analisar mensagem: {e}")
        print(f"ERRO: {e}")
    
    # Testa a detecção de solicitações
    context = "[atendente]: Olá, como posso ajudar?\n[cliente]: Bom dia, tenho uma dúvida."
    
    print(f"\nDetectando solicitações na mensagem com contexto")
    try:
        result = ollama.detect_requests(context, message)
        print("\n--- Resultado da detecção de solicitações ---")
        pretty_print_json(result)
    except Exception as e:
        logger.error(f"Erro ao detectar solicitações: {e}")
        print(f"ERRO: {e}")
    
    # Testa a detecção de encerramento
    messages = [
        {"remetente": "atendente", "conteudo": "Posso ajudar com mais alguma coisa?"},
        {"remetente": "cliente", "conteudo": "Não, obrigado por toda ajuda!"},
        {"remetente": "atendente", "conteudo": "Por nada! Foi um prazer ajudar. Tenha um bom dia!"}
    ]
    
    print(f"\nVerificando encerramento de conversa")
    try:
        result = ollama.should_close_conversation(messages)
        print("\n--- Resultado da verificação de encerramento ---")
        pretty_print_json(result)
    except Exception as e:
        logger.error(f"Erro ao verificar encerramento: {e}")
        print(f"ERRO: {e}")
    
    # Testa a função de conveniência para análise de mensagem
    print(f"\nTestando função de conveniência analyze_message()")
    try:
        result = analyze_message("Preciso que vocês resolvam isso com urgência!")
        print("\n--- Resultado da função de conveniência ---")
        pretty_print_json(result)
    except Exception as e:
        logger.error(f"Erro na função de conveniência: {e}")
        print(f"ERRO: {e}")

def main():
    """Função principal"""
    print("Iniciando testes da biblioteca de prompts e integração com Ollama...\n")
    
    # Testa a biblioteca de prompts
    test_prompt_library()
    
    # Testa a integração com o Ollama
    test_ollama_integration()
    
    print("\nTestes concluídos!")

if __name__ == "__main__":
    main() 