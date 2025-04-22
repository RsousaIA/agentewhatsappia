/**
 * Script para corrigir a função de salvamento de mensagens no Firebase
 * Este script deve ser implementado no arquivo whatsapp_server.js,
 * substituindo a função saveMessageToFirebase original.
 */

/**
 * Salva uma mensagem no Firebase seguindo a estrutura padrão definida
 * @param {Object} messageData - Dados da mensagem
 * @param {string} messageData.from - ID do remetente
 * @param {string} messageData.body - Corpo da mensagem
 * @param {string} messageData.timestamp - Timestamp da mensagem
 * @param {string} messageData.messageId - ID da mensagem
 * @param {boolean} messageData.isFromMe - Se a mensagem é do próprio usuário
 * @param {string} [messageData.mediaUrl] - URL da mídia (opcional)
 * @param {string} [messageData.mediaType] - Tipo de mídia (opcional)
 * @param {boolean} [messageData.isGroup] - Se a mensagem é de um grupo
 * @param {string} [messageData.groupId] - ID do grupo (se for mensagem de grupo)
 * @param {string} [messageData.groupName] - Nome do grupo (se for mensagem de grupo)
 * @param {string} [messageData.authorId] - ID do autor (se for mensagem de grupo)
 * @param {string} [messageData.authorName] - Nome do autor (se for mensagem de grupo)
 * @returns {Promise<Object>} - Resultado da operação
 */
async function saveMessageToFirebase(messageData) {
    if (!dbAdmin) {
        logger.error('Não foi possível salvar mensagem: Firestore Admin não inicializado');
        return { success: false, error: 'Firestore Admin não inicializado' };
    }
    try {
        const { 
            from, 
            body, 
            timestamp, 
            messageId, 
            isFromMe, 
            mediaUrl,
            mediaType,
            isGroup,
            groupId,
            groupName,
            authorId,
            authorName
        } = messageData;

        // Determinar o ID da conversa (diferente para grupos e conversas individuais)
        let conversationId;
        
        if (isGroup) {
            // Para grupos, o ID da conversa é baseado no ID do grupo
            conversationId = groupId;
        } else {
            // Para conversas individuais, mantém a lógica existente
            // Obtém apenas a parte numérica do número de telefone (remove o sufixo @c.us)
            conversationId = from.split('@')[0];
        }

        // Verificar se a conversa já existe
        const conversationRef = dbAdmin.collection('conversas').doc(conversationId);
        const conversationDoc = await conversationRef.get();
        let isNewConversation = false;

        // Se a conversa não existir, criar uma nova
        if (!conversationDoc.exists) {
            isNewConversation = true;
            
            // Criar a conversa de acordo com a estrutura definida em estrutura_banco.txt
            let conversationData = {
                cliente: {
                    nome: isGroup ? groupName : '',
                    telefone: conversationId
                },
                status: 'novo',
                dataHoraInicio: timestamp instanceof Date ? timestamp : new Date(timestamp),
                dataHoraEncerramento: null,
                foiReaberta: false,
                agentesEnvolvidos: [],
                tempoTotal: 0,
                tempoRespostaMedio: 0,
                ultimaMensagem: timestamp instanceof Date ? timestamp : new Date(timestamp)
            };
            
            logger.info(`Nova conversa criada: ${conversationId}`);
            
            // Criar a conversa no Firestore
            await conversationRef.set(conversationData);
        } else {
            // Atualizar timestamp da última mensagem
            await conversationRef.update({
                ultimaMensagem: timestamp instanceof Date ? timestamp : new Date(timestamp)
            });
        }

        // Determinar o tipo de mensagem
        let tipo = 'texto';
        if (mediaUrl) {
            if (mediaType === 'image' || (typeof mediaUrl === 'string' && mediaUrl.includes('image'))) {
                tipo = 'imagem';
            } else if (mediaType === 'audio' || (typeof mediaUrl === 'string' && mediaUrl.includes('audio'))) {
                tipo = 'audio';
            } else if (mediaType === 'video' || (typeof mediaUrl === 'string' && mediaUrl.includes('video'))) {
                tipo = 'video';
            } else if (mediaType === 'document' || (typeof mediaUrl === 'string' && mediaUrl.includes('document'))) {
                tipo = 'arquivo';
            } else {
                tipo = 'arquivo';
            }
        }

        // Determinar o remetente
        let remetente = 'cliente';
        if (isFromMe) {
            remetente = 'atendente';
        } else if (isGroup && authorId) {
            remetente = authorId; // Para identificar diferentes remetentes em grupos
        }

        // Preparar os dados da mensagem conforme a estrutura definida
        const messageContent = {
            tipo: tipo,
            conteudo: mediaUrl ? mediaUrl : body,
            remetente: remetente,
            timestamp: timestamp instanceof Date ? timestamp : new Date(timestamp)
        };

        // Salvar a mensagem como um subdocumento na coleção de mensagens
        const messagesRef = conversationRef.collection('mensagens');
        await messagesRef.doc(messageId).set(messageContent);

        if (isGroup) {
            logger.info(`Mensagem de grupo salva no Firebase`, {
                groupId,
                groupName,
                authorId,
                messageId
            });
        } else {
            logger.info(`Mensagem salva no Firebase: ${messageId}`);
        }

        return {
            success: true,
            isNewConversation,
            conversationId
        };
    } catch (error) {
        logger.error('Erro ao salvar mensagem no Firebase:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Como implementar esta correção:
// 1. Copie esta função e substitua a função saveMessageToFirebase 
//    existente no arquivo whatsapp_server.js
// 2. Se preferir, você pode importar esta função do arquivo atual:
//    const { saveMessageToFirebase } = require('./save_message_fix.js');

// Exportando a função para permitir importação
module.exports = {
    saveMessageToFirebase
}; 