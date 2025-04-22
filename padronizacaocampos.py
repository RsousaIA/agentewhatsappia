import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
import time
from loguru import logger

# Configurar logger
logger.add("logs/migracao_campos.log", rotation="1 day", retention="7 days")

def init_firebase():
    """Inicializa a conexão com o Firebase"""
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("agentewhatsappv1-firebase-adminsdk-fbsvc-54b4b70f96.json")
        firebase_admin.initialize_app(cred)

def migrar_campos_conversas(batch_size=500):
    """
    Migra os campos das conversas para o padrão camelCase
    
    Args:
        batch_size: Quantidade de documentos a serem processados por vez
    """
    db = firestore.client()
    total_processado = 0
    
    try:
        # Buscar todas as conversas em lotes
        query = db.collection('conversas')
        docs = query.stream()
        
        batch = db.batch()
        count = 0
        
        for doc in docs:
            data = doc.to_dict()
            updates = {}
            
            # Mapeamento de campos antigos para novos (se necessário fazer alteração)
            campo_mapping = {
                'data_hora_inicio': 'dataHoraInicio',
                'ultima_mensagem': 'ultimaMensagem',
                'foi_reaberta': 'foiReaberta',
                'reopen_count': 'reopenCount',
                'avaliada': 'avaliada'
            }
            
            # Verificar e atualizar campos
            for campo_antigo, campo_novo in campo_mapping.items():
                if campo_antigo in data:
                    updates[campo_novo] = data[campo_antigo]
                    updates[campo_antigo] = firestore.DELETE_FIELD
            
            # Se houver atualizações, adicionar ao batch
            if updates:
                batch.update(doc.reference, updates)
                count += 1
                logger.info(f"Documento {doc.id} preparado para atualização")
            
            # Quando atingir o tamanho do lote, commit
            if count >= batch_size:
                batch.commit()
                total_processado += count
                logger.info(f"Lote de {count} documentos processado. Total: {total_processado}")
                batch = db.batch()
                count = 0
                time.sleep(1)  # Evitar sobrecarga do Firestore
        
        # Commit final se houver documentos restantes
        if count > 0:
            batch.commit()
            total_processado += count
            logger.info(f"Lote final de {count} documentos processado. Total: {total_processado}")
        
        logger.success(f"Migração concluída! Total de documentos processados: {total_processado}")
        
    except Exception as e:
        logger.error(f"Erro durante a migração: {str(e)}")
        raise

def verificar_campos():
    """Verifica se ainda existem campos no formato antigo"""
    db = firestore.client()
    
    try:
        docs = db.collection('conversas').stream()
        campos_antigos_encontrados = False
        
        for doc in docs:
            data = doc.to_dict()
            campos_antigos = [
                'data_hora_inicio',
                'ultima_mensagem',
                'foi_reaberta',
                'reopen_count'
            ]
            
            for campo in campos_antigos:
                if campo in data:
                    logger.warning(f"Campo antigo '{campo}' encontrado no documento {doc.id}")
                    campos_antigos_encontrados = True
        
        if not campos_antigos_encontrados:
            logger.success("Nenhum campo antigo encontrado!")
        
    except Exception as e:
        logger.error(f"Erro durante a verificação: {str(e)}")

if __name__ == "__main__":
    logger.info("Iniciando processo de migração de campos...")
    
    # Inicializar Firebase
    init_firebase()
    
    # Verificar campos antes da migração
    logger.info("Verificando campos antes da migração...")
    verificar_campos()
    
    # Executar migração
    resposta = input("Deseja prosseguir com a migração? (s/n): ")
    if resposta.lower() == 's':
        logger.info("Iniciando migração...")
        migrar_campos_conversas()
        
        # Verificar campos após migração
        logger.info("Verificando campos após a migração...")
        verificar_campos()
    else:
        logger.info("Migração cancelada pelo usuário.")