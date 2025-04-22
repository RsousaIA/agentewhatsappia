// Importar dependências necessárias
const fs = require('fs');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const logger = require('./logger');
const { saveMessageToFirebase } = require('./whatsapp_server');
const { dbAdmin } = require('./firebase_admin');

// Criar instância do cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-accelerated-2d-canvas', '--no-first-run', '--no-zygote', '--single-process', '--disable-gpu'],
        headless: true,
    }
});

let isReady = false;

// Função para inicializar o cliente WhatsApp
async function initializeWhatsAppClient() {
    try {
        // Evento gerado ao inicializar o cliente
        client.on('qr', (qr) => {
            logger.info('QR Code gerado para autenticação');
            // Gerar QR code no terminal
            qrcode.generate(qr, { small: true });
            
            // Salvar QR code em um arquivo para uso posterior (opcional)
            fs.writeFileSync('qrcode.txt', qr);
        });

        // Evento acionado quando o cliente está pronto
        client.on('ready', async () => {
            isReady = true;
            logger.info('Cliente WhatsApp inicializado e pronto para uso');
            
            try {
                // Obter informações do cliente (número do telefone)
                const info = await client.getInfo();
                logger.info('Informações do cliente:', info);
                
                // Notificar todos os clientes WebSocket que o sistema está pronto
                broadcastToWebSocketClients(JSON.stringify({
                    type: 'status',
                    status: 'ready',
                    clientInfo: info
                }));
            } catch (error) {
                logger.error('Erro ao obter informações do cliente:', error);
            }
        });

        // Manipular mensagens recebidas
        client.on('message', async (message) => {
            // Só processa mensagens se o cliente estiver pronto
            if (isReady) {
                await processMessage(message);
            } else {
                logger.warn('Mensagem recebida antes do cliente estar pronto, ignorando...');
            }
        });

        // Manipular mensagens enviadas por este cliente
        client.on('message_create', async (message) => {
            if (message.fromMe) {
                await processMessage(message);
            }
        });

        // Manipular mudanças de participantes em grupos
        client.on('group_join', async (notification) => {
            try {
                const chat = await notification.getChat();
                logger.info(`Novo participante no grupo: ${chat.name}`, {
                    groupId: chat.id._serialized,
                    participantId: notification.id.participant
                });
                
                // Atualizar contagem de participantes no Firebase
                // Implementar essa funcionalidade conforme necessário
            } catch (error) {
                logger.error('Erro ao processar entrada em grupo', { error: error.message });
            }
        });

        client.on('group_leave', async (notification) => {
            try {
                const chat = await notification.getChat();
                logger.info(`Participante saiu do grupo: ${chat.name}`, {
                    groupId: chat.id._serialized,
                    participantId: notification.id.participant
                });
                
                // Atualizar contagem de participantes no Firebase
                // Implementar essa funcionalidade conforme necessário
            } catch (error) {
                logger.error('Erro ao processar saída de grupo', { error: error.message });
            }
        });

        // Iniciar o cliente
        await client.initialize();
        
        return client;
    } catch (error) {
        logger.error('Erro ao inicializar cliente WhatsApp', { error: error.message });
        console.error('Erro ao inicializar cliente WhatsApp:', error);
        throw error;
    }
}

// Função para processar mensagens (tanto recebidas quanto enviadas)
async function processMessage(message) {
    try {
        // Validação básica da mensagem
        if (!message || !message.from) {
            logger.warn('Mensagem inválida recebida, ignorando...');
            return;
        }

        // Verificar se o cliente está pronto
        if (!isReady) {
            logger.warn('Mensagem recebida antes do cliente estar pronto, ignorando...');
            return;
        }

        // Ignorar atualizações de status
        if (message.type === 'status') {
            logger.debug('Atualização de status ignorada');
            return;
        }

        const chat = await message.getChat();
        const isGroup = chat.isGroup;
        
        // Se for mensagem de grupo, obter informações adicionais
        let groupId = null;
        let groupName = null;
        let authorId = null;
        let authorName = null;
        
        if (isGroup) {
            groupId = chat.id._serialized;
            groupName = chat.name;
            
            // Para mensagens de grupo, obter informações do autor
            if (!message.fromMe) {
                const contact = await message.getContact();
                authorId = contact.id._serialized;
                authorName = contact.name || contact.pushname || contact.id.user;
            } else {
                // Se a mensagem for nossa, usar informações do cliente
                const clientInfo = await client.getContactById(client.info.wid._serialized);
                authorId = clientInfo.id._serialized;
                authorName = clientInfo.name || clientInfo.pushname || 'Eu';
            }
        }
        
        // Dados básicos da mensagem
        const messageData = {
            from: message.from,
            body: message.body,
            timestamp: new Date().toISOString(),
            messageId: message.id._serialized,
            isFromMe: message.fromMe,
            isGroup: isGroup,
            groupId: groupId,
            groupName: groupName,
            authorId: authorId,
            authorName: authorName
        };

        // Determinar o ID da conversa (diferente para grupos e conversas individuais)
        let conversationId;
        
        if (isGroup) {
            // Para grupos, o ID da conversa é baseado no ID do grupo
            conversationId = groupId;
        } else {
            // Para conversas individuais, formata o número de telefone
            // Remove o sufixo @c.us e qualquer caractere não numérico
            conversationId = message.from.split('@')[0].replace(/\D/g, '');
        }

        // Verificar se a conversa já existe
        const conversationRef = dbAdmin.collection('conversas').doc(conversationId);
        const conversationDoc = await conversationRef.get();
        
        let isNewConversation = false;
        
        if (!conversationDoc.exists) {
            // Criar nova conversa
            const conversationData = {
                cliente: {
                    nome: messageData.authorName || 'Desconhecido',
                    telefone: conversationId
                },
                status: 'novo',
                dataHoraInicio: new Date().toISOString(),
                dataHoraEncerramento: null,
                foiReaberta: false,
                agentesEnvolvidos: [],
                tempoTotal: 0,
                tempoRespostaMedio: 0,
                ultimaMensagem: new Date().toISOString()
            };
            
            await conversationRef.set(conversationData);
            isNewConversation = true;
            logger.info(`Nova conversa criada: ${conversationId}`);
        }
        
        // Salvar a mensagem
        const messageRef = conversationRef.collection('mensagens').doc(messageData.messageId);
        await messageRef.set(messageData);
        
        // Atualizar última mensagem da conversa
        await conversationRef.update({
            ultimaMensagem: new Date().toISOString()
        });
        
        if (isGroup) {
            logger.info(`Mensagem de grupo ${message.fromMe ? 'enviada' : 'recebida'} e processada`, {
                groupId,
                groupName,
                author: authorName,
                messageId: message.id._serialized
            });
        } else {
            logger.info(`Mensagem ${message.fromMe ? 'enviada' : 'recebida'} e processada`, { 
                from: message.fromMe ? message.to : message.from, 
                isNewConversation 
            });
        }
    } catch (error) {
        logger.error(`Erro ao processar mensagem: ${error.message}`);
    }
}

// Função para enviar mensagem
async function sendMessage(to, message) {
    try {
        if (!isReady) {
            throw new Error('Cliente WhatsApp não está pronto');
        }
        
        const result = await client.sendMessage(to, message);
        logger.info(`Mensagem enviada para ${to}`);
        return result;
    } catch (error) {
        logger.error('Erro ao enviar mensagem', { error: error.message, to });
        throw error;
    }
}

// Função para enviar mídia
async function sendMedia(to, mediaPath, caption = '') {
    try {
        if (!isReady) {
            throw new Error('Cliente WhatsApp não está pronto');
        }
        
        const media = MessageMedia.fromFilePath(mediaPath);
        const result = await client.sendMessage(to, media, { caption });
        logger.info(`Mídia enviada para ${to}`);
        return result;
    } catch (error) {
        logger.error('Erro ao enviar mídia', { error: error.message, to });
        throw error;
    }
}

// Exportar funções e cliente
module.exports = {
    client,
    initializeWhatsAppClient,
    sendMessage,
    sendMedia
}; 