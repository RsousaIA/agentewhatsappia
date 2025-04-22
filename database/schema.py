from typing import Dict, List
from firebase_admin import firestore
from .firebase_db import get_firestore_db, init_firebase
import logging

logger = logging.getLogger(__name__)

class FirebaseSchema:
    def __init__(self):
        init_firebase()
        self.db = get_firestore_db()

    def create_conversation_schema(self, conversation_id: str):
        """
        Cria a estrutura base de uma conversa com suas subcoleções
        """
        try:
            # Documento principal da conversa
            conversation_ref = self.db.collection('conversas').document(conversation_id)
            conversation_ref.set({
                'cliente': {
                    'nome': '',
                    'telefone': ''
                },
                'status': 'novo',  # novo, em_andamento, finalizado
                'dataHoraInicio': firestore.SERVER_TIMESTAMP,
                'dataHoraEncerramento': None,
                'foiReaberta': False,
                'agentesEnvolvidos': [],
                'tempoTotal': 0,
                'tempoRespostaMedio': 0,
                'ultimaMensagem': firestore.SERVER_TIMESTAMP
            })

            # Criar subcoleção mensagens
            mensagens_ref = conversation_ref.collection('mensagens').document()
            mensagens_ref.set({
                'tipo': 'texto',  # texto, audio, imagem
                'conteudo': 'Conversa iniciada',
                'remetente': 'sistema',  # cliente ou idDoAtendente
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            # Criar subcoleção solicitacoes
            solicitacoes_ref = conversation_ref.collection('solicitacoes').document()
            solicitacoes_ref.set({
                'descricao': 'Atendimento inicial',
                'dataHoraCriacao': firestore.SERVER_TIMESTAMP,
                'prazo': firestore.SERVER_TIMESTAMP,
                'status': 'pendente',  # pendente, atrasada, atendida, nao_atendida
                'dataHoraAtendimento': None,
                'motivoNaoAtendimento': None
            })

            # Criar subcoleção avaliacoes
            avaliacoes_ref = conversation_ref.collection('avaliacoes').document()
            avaliacoes_ref.set({
                'dataAvaliacao': firestore.SERVER_TIMESTAMP,
                'reclamacoes': [],
                'notaComunicacaoClara': None,  # 0-10
                'notaConhecimentoTecnico': None,  # 0-10
                'notaEmpatiaCordialidade': None,  # 0-10
                'notaProfissionalismoEtica': None,  # 0-10
                'notaOrientacaoResultados': None,  # 0-10
                'notaInteligenciaEmocional': None,  # 0-10
                'notaCumprimentoPrazos': None,  # 0-10
                'notaGeral': None,  # 0-10
                'zerouPorCordialidade': False,
                'detalhesCriticos': None
            })

            logger.info(f"Estrutura da conversa {conversation_id} criada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar estrutura da conversa: {e}")
            return False

    def create_consolidado_schema(self):
        """
        Cria a coleção de dados consolidados
        """
        try:
            consolidado_ref = self.db.collection('consolidadoAtendimentos').document()
            consolidado_ref.set({
                'conversationId': '',
                'clienteNome': '',
                'agentesEnvolvidos': [],
                'dataHoraInicio': firestore.SERVER_TIMESTAMP,
                'dataHoraEncerramento': None,
                'notaGeral': None,
                'statusFinal': '',
                'resumoFinal': ''
            })

            logger.info("Estrutura de consolidação criada com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao criar estrutura de consolidação: {e}")
            return False

    def setup_database(self):
        """
        Configura a estrutura inicial do banco de dados
        """
        try:
            # Criar uma conversa de exemplo
            conversation_id = 'exemplo_conversa'
            self.create_conversation_schema(conversation_id)
            
            # Criar estrutura de consolidação
            self.create_consolidado_schema()

            logger.info("Banco de dados configurado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao configurar banco de dados: {e}")
            return False 