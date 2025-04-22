import os
import sys
import json
from loguru import logger

# Adiciona o diretório pai ao path para permitir imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configura o logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")

# Importa as funções após configurar o logger
from agent.core.ollama_integration import (
    analyze_message,
    detect_requests,
    should_close_conversation,
    detect_complaints,
    evaluate_response
)

def pretty_print_json(data):
    """Imprime um dicionário como JSON formatado"""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def demonstrar_simulacao():
    """Demonstra o funcionamento do modo de simulação do Ollama"""
    logger.info("=== INICIANDO DEMONSTRAÇÃO DO MODO DE SIMULAÇÃO ===")
    
    # Testa os dois modos para comparação
    modos = [
        {"nome": "MODO REAL", "ativar_simulacao": "false"},
        {"nome": "MODO SIMULAÇÃO", "ativar_simulacao": "true"}
    ]
    
    for modo in modos:
        logger.info(f"\n=== {modo['nome']} ===")
        
        # Configura o modo de simulação
        os.environ["OLLAMA_SIMULATION_MODE"] = modo["ativar_simulacao"]
        
        # === Teste 1: Análise de mensagem ===
        try:
            mensagem = "Olá, gostaria de saber onde está meu pedido #12345. Já se passaram 5 dias e não recebi nada!"
            logger.info(f"Testando análise de mensagem: \"{mensagem}\"")
            resultado = analyze_message(mensagem)
            logger.info("Resultado da análise:")
            pretty_print_json(resultado)
        except Exception as e:
            logger.error(f"Erro na análise de mensagem: {str(e)}")
        
        # === Teste 2: Detecção de solicitações ===
        try:
            contexto = "Cliente perguntou sobre status do pedido #12345"
            mensagem = "Ainda não recebi! Preciso que me informem quando vai chegar."
            logger.info(f"\nTestando detecção de solicitações:")
            resultado = detect_requests(contexto, mensagem)
            logger.info("Resultado da detecção:")
            pretty_print_json(resultado)
        except Exception as e:
            logger.error(f"Erro na detecção de solicitações: {str(e)}")
        
        # === Teste 3: Verificação de encerramento ===
        try:
            mensagens = [
                {"role": "cliente", "content": "Obrigado pela ajuda!"},
                {"role": "atendente", "content": "Foi um prazer. Mais alguma coisa?"},
                {"role": "cliente", "content": "Não, isso é tudo. Tenha um bom dia!"}
            ]
            logger.info(f"\nTestando verificação de encerramento:")
            resultado = should_close_conversation(mensagens)
            logger.info("Resultado da verificação:")
            pretty_print_json(resultado)
        except Exception as e:
            logger.error(f"Erro na verificação de encerramento: {str(e)}")
        
        # === Teste 4: Detecção de reclamações ===
        try:
            mensagens = [
                {"role": "cliente", "content": "Olá, meu pedido ainda não chegou!"},
                {"role": "atendente", "content": "Vou verificar para você."},
                {"role": "cliente", "content": "Isso é um absurdo! Já se passaram 10 dias!"}
            ]
            logger.info(f"\nTestando detecção de reclamações:")
            resultado = detect_complaints(mensagens)
            logger.info("Resultado da detecção:")
            pretty_print_json(resultado)
        except Exception as e:
            logger.error(f"Erro na detecção de reclamações: {str(e)}")
        
        # === Teste 5: Avaliação de resposta ===
        try:
            mensagem_cliente = "Quero cancelar meu pedido #54321"
            resposta_atendente = "Vou processar o cancelamento do seu pedido #54321 imediatamente. Pode me informar o motivo do cancelamento?"
            logger.info(f"\nTestando avaliação de resposta:")
            resultado = evaluate_response(mensagem_cliente, resposta_atendente)
            logger.info("Resultado da avaliação:")
            pretty_print_json(resultado)
        except Exception as e:
            logger.error(f"Erro na avaliação de resposta: {str(e)}")

if __name__ == "__main__":
    demonstrar_simulacao() 