import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class WhatsappIntegration:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.is_ready = True  # Assuming the client is always ready

    async def _handle_message(self, message):
        try:
            # Validação mínima da mensagem - apenas verificamos se existe algo
            if not message:
                logger.warning('Mensagem vazia recebida, tentando criar estrutura mínima...')
                message = {}

            # Garantir que temos um remetente
            if not message.get('from'):
                logger.warning('Mensagem sem remetente, usando valor padrão...')
                # Se não tiver remetente, usamos um valor padrão temporário
                # Isso deve ser corrigido em nível superior
                message['from'] = 'unknown@c.us'

            # Garantir que temos um corpo de mensagem
            if not message.get('body'):
                logger.warning('Mensagem sem corpo, usando valor padrão...')
                message['body'] = '(Mensagem sem conteúdo)'

            # Garantir que temos um ID
            if not message.get('id'):
                logger.warning('Mensagem sem ID, gerando ID baseado no timestamp...')
                # Gerar um ID baseado no timestamp atual
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f")
                message['id'] = f"gerado_{message.get('from', 'unknown').split('@')[0]}_{timestamp_str}"

            # Verificar se o cliente está pronto
            if not self.is_ready:
                logger.warning('Cliente não está pronto, mas tentaremos processar a mensagem mesmo assim')

            # Tentamos obter informações do chat, mas permitimos prosseguir mesmo que falhe
            is_group = False
            group_id = None
            group_name = None
            author_id = None
            author_name = None
            
            try:
                chat = await self.client.get_chat(message['from'])
                is_group = chat.get('isGroup', False)
                
                if is_group:
                    group_id = chat.get('id')
                    group_name = chat.get('name')
                    
                    if not message.get('fromMe'):
                        contact = await self.client.get_contact(message['from'])
                        author_id = contact.get('id')
                        author_name = contact.get('name') or contact.get('pushname') or contact.get('id', {}).get('user')
                    else:
                        client_info = await self.client.get_contact(self.client.info['wid'])
                        author_id = client_info.get('id')
                        author_name = client_info.get('name') or client_info.get('pushname') or 'Eu'
            except Exception as chat_error:
                logger.warning(f'Erro ao obter informações do chat, prosseguindo com valores padrão: {str(chat_error)}')
                # Se não conseguirmos obter informações do chat, usamos valores padrão
                # Isso permite que a mensagem seja processada mesmo assim
            
            # Dados básicos da mensagem - garantimos que todos os campos tenham valores padrão
            message_data = {
                'from': message.get('from', 'unknown@c.us'),
                'body': message.get('body', '(Mensagem sem conteúdo)'),
                'timestamp': datetime.now().isoformat(),
                'messageId': message.get('id', f"auto_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"),
                'isFromMe': message.get('fromMe', False),
                'isGroup': is_group,
                'groupId': group_id,
                'groupName': group_name,
                'authorId': author_id,
                'authorName': author_name
            }

            # Determinar o ID da conversa
            if is_group and group_id:
                conversation_id = group_id
            else:
                # Extrair o número de telefone do remetente
                phone_part = message['from'].split('@')[0]
                # Substituir caracteres não numéricos, verificando se o método existe (Python vs JavaScript)
                # No Python, usamos o módulo re para substituir
                conversation_id = re.sub(r'\D', '', phone_part)
                # Se ainda não temos ID válido, geramos um baseado no timestamp
                if not conversation_id:
                    conversation_id = f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Verificar se a conversa já existe
            conversation_ref = self.db.collection('conversas').document(conversation_id)
            conversation_doc = await conversation_ref.get()
            
            is_new_conversation = False
            
            if not conversation_doc.exists:
                # Criar nova conversa
                conversation_data = {
                    'cliente': {
                        'nome': message_data.get('authorName') or 'Desconhecido',
                        'telefone': conversation_id
                    },
                    'status': 'novo',
                    'dataHoraInicio': datetime.now().isoformat(),
                    'dataHoraEncerramento': None,
                    'foiReaberta': False,
                    'agentesEnvolvidos': [],
                    'tempoTotal': 0,
                    'tempoRespostaMedio': 0,
                    'ultimaMensagem': datetime.now().isoformat()
                }
                
                await conversation_ref.set(conversation_data)
                is_new_conversation = True
                logger.info(f'Nova conversa criada: {conversation_id}')
            
            # Salvar a mensagem - garantimos que temos um ID válido
            message_id = message_data['messageId']
            message_ref = conversation_ref.collection('mensagens').document(message_id)
            await message_ref.set(message_data)
            
            # Atualizar última mensagem da conversa
            await conversation_ref.update({
                'ultimaMensagem': datetime.now().isoformat()
            })
            
            logger.info(f'Mensagem {message_id} processada e salva na conversa {conversation_id}')
            
            if is_group:
                logger.info(f'Mensagem de grupo {"enviada" if message_data["isFromMe"] else "recebida"} e processada', {
                    'groupId': group_id,
                    'groupName': group_name,
                    'author': author_name,
                    'messageId': message_data['messageId']
                })
            else:
                logger.info(f'Mensagem {"enviada" if message_data["isFromMe"] else "recebida"} e processada', {
                    'from': message_data['isFromMe'] and message_data.get('to') or message_data['from'],
                    'isNewConversation': is_new_conversation
                })

            return {
                'success': True,
                'message_id': message_id,
                'conversation_id': conversation_id,
                'is_new_conversation': is_new_conversation
            }

        except Exception as error:
            logger.error(f'Erro ao processar mensagem: {str(error)}')
            # Retornamos o erro para que o chamador possa lidar com ele
            return {
                'success': False,
                'error': str(error)
            } 