const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const config = require('./config');
const logger = require('./logger');
const { formatPhoneNumber, isValidWhatsAppNumber } = require('./utils/phone');
const { createError, errorHandler } = require('./utils/errorHandler');
const ReconnectionManager = require('./utils/reconnectionManager');
const multer = require('multer');
const path = require('path');
const { processMedia, MEDIA_TYPES, generateUniqueFilename } = require('./utils/media');
const queueManager = require('./utils/queueManager');
const GroupManager = require('./utils/groupManager');

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: config.socket.cors
});

// Middleware para tratamento de erros
app.use(errorHandler);

// Configuração do multer para upload de arquivos
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, path.join(__dirname, 'temp'));
    },
    filename: (req, file, cb) => {
        cb(null, generateUniqueFilename(file.originalname));
    }
});

const upload = multer({ storage });

// Inicializa o cliente do WhatsApp
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: 'whatsapp-agent',
        dataPath: config.whatsapp.sessionPath
    }),
    puppeteer: {
        args: ['--no-sandbox']
    }
});

// Inicializa o gerenciador de reconexão
const reconnectionManager = new ReconnectionManager(client, {
    maxAttempts: 5,
    initialDelay: 1000,
    maxDelay: 30000
});

// Importa o gerenciador de grupos
const groupManager = new GroupManager(client);

// Eventos do WhatsApp
client.on('qr', (qr) => {
    logger.info('Novo QR Code gerado');
    qrcode.generate(qr, { small: true });
    io.emit('qr', qr);
});

client.on('ready', () => {
    logger.info('Cliente WhatsApp conectado e pronto');
    io.emit('ready');
});

client.on('message', async (message) => {
    try {
        logger.info('Nova mensagem recebida', {
            from: message.from,
            body: message.body,
            hasMedia: message.hasMedia
        });

        // Se a mensagem contém mídia, processa
        if (message.hasMedia) {
            const media = await message.downloadMedia();
            io.emit('message', {
                from: message.from,
                body: message.body,
                timestamp: message.timestamp,
                media: {
                    data: media.data,
                    mimetype: media.mimetype,
                    filename: media.filename
                }
            });
        } else {
            io.emit('message', {
                from: message.from,
                body: message.body,
                timestamp: message.timestamp
            });
        }
    } catch (error) {
        logger.error('Erro ao processar mensagem', { error: error.message });
    }
});

client.on('disconnected', async (reason) => {
    logger.warn('Cliente WhatsApp desconectado', { reason });
    io.emit('disconnected', reason);

    // Tenta reconectar automaticamente
    try {
        await reconnectionManager.reconnect();
        logger.info('Reconexão bem-sucedida após desconexão');
    } catch (error) {
        logger.error('Falha na reconexão automática', { error: error.message });
    }
});

// Rotas da API
app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

// Adiciona endpoints para grupos
app.get('/groups', async (req, res) => {
    try {
        const groups = await groupManager.listGroups();
        res.json(groups);
    } catch (error) {
        logger.error('Erro ao listar grupos', { error: error.message });
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.get('/groups/:groupId', async (req, res) => {
    try {
        const groupInfo = await groupManager.getGroupInfo(req.params.groupId);
        res.json(groupInfo);
    } catch (error) {
        logger.error('Erro ao obter informações do grupo', {
            groupId: req.params.groupId,
            error: error.message
        });
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/groups/:groupId/message', upload.single('media'), async (req, res) => {
    try {
        const { content, priority = 0 } = req.body;
        const media = req.file ? {
            file: req.file,
            type: req.body.mediaType
        } : null;

        // Cria objeto da mensagem
        const message = {
            id: generateMessageId(),
            groupId: req.params.groupId,
            content,
            media,
            timestamp: Date.now()
        };

        // Adiciona à fila
        await queueManager.enqueue('group_messages', message, priority);

        res.json({
            success: true,
            messageId: message.id,
            queueStats: queueManager.getQueueStats('group_messages')
        });
    } catch (error) {
        logger.error('Erro ao enfileirar mensagem para grupo', {
            groupId: req.params.groupId,
            error: error.message
        });
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/groups/:groupId/participants', async (req, res) => {
    try {
        const { numbers, action } = req.body;

        if (!numbers || !Array.isArray(numbers) || numbers.length === 0) {
            throw new Error('Números de telefone inválidos');
        }

        let result;
        switch (action) {
            case 'add':
                result = await groupManager.addParticipants(req.params.groupId, numbers);
                break;
            case 'remove':
                result = await groupManager.removeParticipants(req.params.groupId, numbers);
                break;
            case 'promote':
                result = await groupManager.promoteParticipants(req.params.groupId, numbers);
                break;
            case 'demote':
                result = await groupManager.demoteParticipants(req.params.groupId, numbers);
                break;
            default:
                throw new Error('Ação inválida');
        }

        res.json(result);
    } catch (error) {
        logger.error('Erro ao gerenciar participantes do grupo', {
            groupId: req.params.groupId,
            error: error.message
        });
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Configura o processamento de mensagens de grupo na fila
queueManager.on('process', async ({ message, queueName }) => {
    if (queueName === 'group_messages') {
        try {
            const { groupId, content, media } = message;
            
            // Processa a mensagem
            if (media) {
                // Processa mídia
                const mediaData = await processMedia(media.file, media.type);
                await groupManager.sendMessage(groupId, content, mediaData);
            } else {
                // Envia mensagem de texto
                await groupManager.sendMessage(groupId, content);
            }

            // Notifica sucesso
            queueManager.notifyProcessed('group_messages', message.id);
            
            logger.info('Mensagem de grupo processada com sucesso', {
                messageId: message.id,
                groupId
            });
        } catch (error) {
            logger.error('Erro ao processar mensagem de grupo', {
                messageId: message.id,
                error: error.message
            });
            throw error;
        }
    }
});

// Configura o processamento de mensagens na fila
queueManager.on('process', async ({ message }) => {
    try {
        const { number, content, media } = message;
        
        // Valida o número de telefone
        if (!isValidWhatsAppNumber(number)) {
            throw new Error('Número de telefone inválido');
        }

        // Processa a mensagem
        if (media) {
            // Processa mídia
            const mediaData = await processMedia(media.file, media.type);
            await client.sendMessage(number, mediaData);
        } else {
            // Envia mensagem de texto
            await client.sendMessage(number, content);
        }

        // Notifica sucesso
        queueManager.notifyProcessed('messages', message.id);
        
        logger.info('Mensagem processada com sucesso', {
            messageId: message.id,
            number
        });
    } catch (error) {
        logger.error('Erro ao processar mensagem', {
            messageId: message.id,
            error: error.message
        });
        throw error;
    }
});

// Atualiza o endpoint de envio de mensagem
app.post('/send_message', upload.single('media'), async (req, res) => {
    try {
        const { number, content, priority = 0 } = req.body;
        const media = req.file ? {
            file: req.file,
            type: req.body.mediaType
        } : null;

        // Cria objeto da mensagem
        const message = {
            id: generateMessageId(),
            number,
            content,
            media,
            timestamp: Date.now()
        };

        // Adiciona à fila
        await queueManager.enqueue('messages', message, priority);

        res.json({
            success: true,
            messageId: message.id,
            queueStats: queueManager.getQueueStats('messages')
        });
    } catch (error) {
        logger.error('Erro ao enfileirar mensagem', { error: error.message });
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Adiciona endpoint para status da fila
app.get('/queue_status', (req, res) => {
    const stats = queueManager.getQueueStats('messages');
    res.json(stats);
});

// Eventos do Socket.IO
io.on('connection', (socket) => {
    logger.info('Novo cliente conectado', { id: socket.id });

    socket.on('send_message', async (data) => {
        try {
            const { to, message, media } = data;
            
            // Verifica se está tentando reconectar
            if (reconnectionManager.isReconnecting()) {
                throw createError('CONNECTION_ERROR', 'Servidor está reconectando, tente novamente em alguns segundos');
            }
            
            // Valida e formata o número de telefone
            const formattedNumber = formatPhoneNumber(to);
            if (!formattedNumber) {
                throw createError('INVALID_NUMBER', 'Número de telefone inválido', {
                    original: to
                });
            }

            // Verifica se o número está no formato correto do WhatsApp
            if (!isValidWhatsAppNumber(formattedNumber)) {
                throw createError('INVALID_NUMBER', 'Número não está no formato correto do WhatsApp', {
                    formatted: formattedNumber
                });
            }

            // Envia a mensagem
            try {
                let result;
                if (media) {
                    // Processa a mídia
                    const processedMedia = await processMedia(media.file, media.type);
                    
                    // Envia a mídia com base no tipo
                    switch (media.type) {
                        case MEDIA_TYPES.IMAGE:
                            result = await client.sendImage(
                                formattedNumber,
                                processedMedia.buffer,
                                processedMedia.filename,
                                message
                            );
                            break;
                        case MEDIA_TYPES.DOCUMENT:
                            result = await client.sendDocument(
                                formattedNumber,
                                processedMedia.buffer,
                                processedMedia.filename,
                                message
                            );
                            break;
                        case MEDIA_TYPES.AUDIO:
                            result = await client.sendAudio(
                                formattedNumber,
                                processedMedia.buffer,
                                processedMedia.filename
                            );
                            break;
                        case MEDIA_TYPES.VIDEO:
                            result = await client.sendVideo(
                                formattedNumber,
                                processedMedia.buffer,
                                processedMedia.filename,
                                message
                            );
                            break;
                        case MEDIA_TYPES.STICKER:
                            result = await client.sendSticker(
                                formattedNumber,
                                processedMedia.buffer
                            );
                            break;
                        default:
                            throw createError('INVALID_MEDIA_TYPE', 'Tipo de mídia não suportado');
                    }
                } else {
                    result = await client.sendMessage(formattedNumber, message);
                }

                logger.info('Mensagem enviada com sucesso', { 
                    to: formattedNumber,
                    messageLength: message?.length || 0,
                    hasMedia: !!media
                });

                // Notifica o cliente sobre o sucesso
                socket.emit('message_sent', {
                    to: formattedNumber,
                    timestamp: new Date().toISOString(),
                    messageId: result.id
                });
            } catch (error) {
                throw createError('SEND_MESSAGE_ERROR', 'Erro ao enviar mensagem', {
                    to: formattedNumber,
                    reason: error.message
                });
            }
        } catch (error) {
            logger.error('Erro ao enviar mensagem', { 
                error: error.message,
                details: error.details
            });
            socket.emit('error', { 
                message: error.message,
                code: error.code,
                details: error.details
            });
        }
    });

    socket.on('disconnect', () => {
        logger.info('Cliente desconectado', { id: socket.id });
    });
});

// Inicia o servidor
httpServer.listen(config.server.port, config.server.host, () => {
    logger.info(`Servidor iniciado em http://${config.server.host}:${config.server.port}`);
    client.initialize().catch(error => {
        logger.error('Erro ao inicializar cliente WhatsApp', { error: error.message });
        // Tenta reconectar automaticamente
        reconnectionManager.reconnect().catch(reconnectError => {
            logger.error('Falha na reconexão inicial', { error: reconnectError.message });
        });
    });
}); 