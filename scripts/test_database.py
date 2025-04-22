import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from database.schema import FirebaseSchema

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_conversation_structure():
    schema = FirebaseSchema()
    conversation_id = str(uuid.uuid4())
    
    try:
        # Cria uma conversa de teste
        success = schema.create_conversation_schema(conversation_id)
        assert success, "Falha ao criar conversa"
        
        # Obtém a referência do documento
        doc = schema.db.collection('conversas').document(conversation_id).get()
        data = doc.to_dict()
        
        # Verifica a estrutura do documento principal
        assert 'cliente' in data, "Campo 'cliente' não encontrado"
        assert 'nome' in data['cliente'], "Campo 'nome' não encontrado em cliente"
        assert 'telefone' in data['cliente'], "Campo 'telefone' não encontrado em cliente"
        
        assert 'status' in data, "Campo 'status' não encontrado"
        assert 'dataHoraInicio' in data, "Campo 'dataHoraInicio' não encontrado"
        assert 'dataHoraEncerramento' in data, "Campo 'dataHoraEncerramento' não encontrado"
        assert 'ultimaMensagem' in data, "Campo 'ultimaMensagem' não encontrado"
        
        # Verifica campos opcionais
        assert 'foiReaberta' in data, "Campo opcional 'foiReaberta' não encontrado"
        assert 'agentesEnvolvidos' in data, "Campo opcional 'agentesEnvolvidos' não encontrado"
        assert 'tempoTotal' in data, "Campo opcional 'tempoTotal' não encontrado"
        assert 'tempoRespostaMedio' in data, "Campo opcional 'tempoRespostaMedio' não encontrado"
        
        # Verifica subcoleção mensagens
        mensagens = schema.db.collection('conversas').document(conversation_id).collection('mensagens').get()
        if mensagens:
            msg = mensagens[0].to_dict()
            assert 'tipo' in msg, "Campo 'tipo' não encontrado em mensagem"
            assert 'conteudo' in msg, "Campo 'conteudo' não encontrado em mensagem"
            assert 'remetente' in msg, "Campo 'remetente' não encontrado em mensagem"
            assert 'timestamp' in msg, "Campo 'timestamp' não encontrado em mensagem"
        
        logger.info("✓ Teste de estrutura da conversa passou")
        return True
        
    except AssertionError as e:
        logger.error(f"✗ Teste de estrutura falhou: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Erro inesperado: {e}")
        return False

def test_conversation_creation():
    schema = FirebaseSchema()
    conversation_id = str(uuid.uuid4())
    
    try:
        # Testa criação de conversa
        success = schema.create_conversation_schema(conversation_id)
        assert success, "Falha ao criar conversa"
        logger.info("✓ Teste de criação de conversa passou")
        
        return True
    except AssertionError as e:
        logger.error(f"✗ Teste falhou: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Erro inesperado: {e}")
        return False

def test_consolidado_creation():
    schema = FirebaseSchema()
    
    try:
        # Testa criação de consolidado
        success = schema.create_consolidado_schema()
        assert success, "Falha ao criar consolidado"
        logger.info("✓ Teste de criação de consolidado passou")
        
        return True
    except AssertionError as e:
        logger.error(f"✗ Teste falhou: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Erro inesperado: {e}")
        return False

def main():
    logger.info("Iniciando testes da estrutura do banco de dados...")
    
    tests = [
        ("Teste de estrutura da conversa", test_conversation_structure),
        ("Teste de criação de conversa", test_conversation_creation),
        ("Teste de criação de consolidado", test_consolidado_creation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\nExecutando: {test_name}")
        if test_func():
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nResultados:")
    logger.info(f"Testes passados: {passed}")
    logger.info(f"Testes falhos: {failed}")
    logger.info(f"Total de testes: {len(tests)}")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main() 