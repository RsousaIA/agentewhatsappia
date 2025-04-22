const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const { initializeApp } = require('firebase/app');
const { getFirestore, collection, addDoc, doc, setDoc, getDoc, updateDoc, serverTimestamp } = require('firebase/firestore');
const http = require('http');
const socketIO = require('socket.io');
const qrcode = require('qrcode');
const path = require('path');
const dotenv = require('dotenv');
const winston = require('winston');
const { Server } = require('socket.io');
const WebSocket = require('ws');
const admin = require('firebase-admin');
const logger = require('./logger');
const fs = require('fs');

// Carrega variáveis de ambiente
dotenv.config();

// Configuração adicional do logger, se necessário
// Não redeclare a variável logger aqui, apenas configure-a
winston.configure({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
        new winston.transports.Console({
            format: winston.format.simple()
        })
    ]
});

// Configuração do Express
const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Configuração do WebSocket Server para clientes Python
const wss = new WebSocket.Server({ server });

// Array para armazenar todos os clientes WebSocket conectados
const wsClients = [];

// Eventos do WebSocket Server
wss.on('connection', (ws) => {
    logger.info('Cliente WebSocket conectado');
    console.log('Cliente WebSocket conectado');
    
    // Adicionar cliente à lista
    wsClients.push(ws);
    
    // Enviar status atual
    if (clientStatus === 'connected') {
        ws.send(JSON.stringify({ type: 'status', status: 'connected' }));
    } else if (lastQrCode && clientStatus === 'disconnected') {
        ws.send(JSON.stringify({ type: 'qr', qrCode: lastQrCode }));
    }
    
    // Lidar com mensagens recebidas do cliente Python
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            logger.info(`Mensagem recebida do cliente WebSocket: ${JSON.stringify(data)}`);
            
            // Processar diferentes tipos de mensagens
            if (data.action === 'send_message') {
                const { to, message, mediaUrl } = data;
                // Enviar mensagem via WhatsApp
                client.sendMessage(to, message).then(response => {
                    ws.send(JSON.stringify({ 
                        type: 'message_sent', 
                        success: true, 
                        messageId: response.id 
                    }));
                }).catch(err => {
                    ws.send(JSON.stringify({ 
                        type: 'error', 
                        message: 'Erro ao enviar mensagem', 
                        error: err.message 
                    }));
                });
            } else if (data.action === 'mark_as_read') {
                // Implementar marcação como lido
                // ...
            }
        } catch (error) {
            logger.error(`Erro ao processar mensagem WebSocket: ${error.message}`);
            ws.send(JSON.stringify({ type: 'error', message: 'Erro ao processar mensagem' }));
        }
    });
    
    // Tratar desconexão do cliente
    ws.on('close', () => {
        logger.info('Cliente WebSocket desconectado');
        console.log('Cliente WebSocket desconectado');
        
        // Remover cliente da lista
        const index = wsClients.indexOf(ws);
        if (index !== -1) {
            wsClients.splice(index, 1);
        }
    });
    
    // Tratar erros
    ws.on('error', (error) => {
        logger.error(`Erro no WebSocket: ${error.message}`);
        console.error('Erro no WebSocket:', error);
    });
});

// Função para transmitir mensagens para todos os clientes WebSocket
function broadcastToWebSocketClients(message) {
    wsClients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

// Configuração do Firebase
const firebaseConfig = {
    apiKey: process.env.FIREBASE_API_KEY,
    authDomain: process.env.FIREBASE_AUTH_DOMAIN,
    projectId: process.env.FIREBASE_PROJECT_ID,
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.FIREBASE_APP_ID
};

// Inicializa o Firebase
const firebaseApp = initializeApp(firebaseConfig);
const db = getFirestore(firebaseApp);

// Status e armazenamento de QR
let lastQrCode = null;
let clientStatus = 'disconnected';

// Armazenamento de conversas ativas
const activeConversations = {};

// Configuração do cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: 'agente-suporte-whatsapp'
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

// Inicializar Firebase Admin de forma segura
let dbAdmin = null;
const saPath = path.join(__dirname, 'agentewhatsappv1-firebase-adminsdk-fbsvc-54b4b70f96.json');
if (fs.existsSync(saPath)) {
    try {
        const serviceAccount = require(saPath);
        admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
        logger.info('Firebase Admin inicializado com sucesso');
        try {
            dbAdmin = admin.firestore();
        } catch (err) {
            logger.error('Erro ao obter instância do Firestore Admin:', err);
        }
    } catch (error) {
        logger.error('Erro ao inicializar Firebase Admin (arquivo de credenciais inválido):', error);
    }
} else {
    logger.warn('Arquivo de credenciais do Firebase não encontrado. Continuando sem Firebase Admin');
}

/**
 * Salva uma mensagem no Firebase
 * @param {Object} messageData - Dados da mensagem
 * @param {string} messageData.from - ID do remetente
 * @param {string} messageData.body - Corpo da mensagem
 * @param {string} messageData.timestamp - Timestamp da mensagem
 * @param {string} messageData.messageId - ID da mensagem
 * @param {boolean} messageData.isFromMe - Se a mensagem é do próprio usuário
 * @param {string} [messageData.mediaUrl] - URL da mídia (opcional)
 * @param {boolean} [messageData.isGroup] - Se a mensagem é de um grupo
 * @param {string} [messageData.groupId] - ID do grupo (se for mensagem de grupo)
 * @param {string} [messageData.groupName] - Nome do grupo (se for mensagem de grupo)
 * @param {string} [messageData.authorId] - ID do autor (se for mensagem de grupo)
 * @param {string} [messageData.authorName] - Nome do autor (se for mensagem de grupo)
 * @param {string} [messageData.mediaType] - Tipo de mídia (opcional)
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
            isGroup,
            groupId,
            groupName,
            authorId,
            authorName,
            mediaType
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
            if (mediaType === 'image' || mediaUrl.includes('image')) {
                tipo = 'imagem';
            } else if (mediaType === 'audio' || mediaUrl.includes('audio')) {
                tipo = 'audio';
            } else if (mediaType === 'video' || mediaUrl.includes('video')) {
                tipo = 'video';
            } else if (mediaType === 'document' || mediaUrl.includes('document')) {
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

// Rota principal
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Rota de status
app.get('/status', (req, res) => {
    const response = {
        status: clientStatus
    };
    
    if (lastQrCode && clientStatus === 'disconnected') {
        response.qr = lastQrCode;
    }
    
    res.json(response);
});

// Socket.IO - Gerencia conexões
io.on('connection', (socket) => {
    logger.info('Cliente web conectado');
    console.log('Cliente web conectado');
    
    // Envia o QR Code salvo se disponível
    if (lastQrCode && clientStatus === 'disconnected') {
        socket.emit('qr', lastQrCode);
    }
    
    // Envia status atual
    if (clientStatus === 'connected') {
        socket.emit('ready');
    }

    socket.on('disconnect', () => {
        logger.info('Cliente web desconectado');
        console.log('Cliente web desconectado');
    });
});

// Eventos do WhatsApp
client.on('qr', async (qr) => {
    logger.info('QR Code gerado');
    console.log('QR Code gerado. Por favor, escaneie com o WhatsApp.');
    
    // Converter QR para imagem Base64
    try {
        const qrImage = await qrcode.toDataURL(qr);
        lastQrCode = qrImage.split(',')[1]; // Remover prefixo data:image/png;base64,
        clientStatus = 'disconnected';
        io.emit('qr', lastQrCode);
        
        // Transmitir QR para clientes WebSocket
        broadcastToWebSocketClients(JSON.stringify({ type: 'qr', qrCode: lastQrCode }));
    } catch (err) {
        logger.error('Erro ao gerar QR Code', err);
        console.error('Erro ao gerar QR Code:', err);
    }
});

client.on('ready', () => {
    logger.info('Cliente WhatsApp está pronto');
    console.log('Cliente WhatsApp está pronto!');
    clientStatus = 'connected';
    lastQrCode = null;
    io.emit('ready');
    
    // Transmitir status para clientes WebSocket
    broadcastToWebSocketClients(JSON.stringify({ type: 'status', status: 'connected' }));
});

client.on('authenticated', () => {
    logger.info('Cliente WhatsApp autenticado');
    console.log('Cliente WhatsApp autenticado!');
});

client.on('auth_failure', (msg) => {
    logger.error('Falha na autenticação', { msg });
    console.error('Falha na autenticação:', msg);
    clientStatus = 'disconnected';
    io.emit('disconnected', 'Falha na autenticação');
});

client.on('disconnected', (reason) => {
    logger.warn('Cliente WhatsApp desconectado', { reason });
    console.warn('Cliente WhatsApp desconectado:', reason);
    clientStatus = 'disconnected';
    io.emit('disconnected', reason);
});

// Quando receber uma mensagem
client.on('message', async (message) => {
    try {
        // Ignorar atualizações de status
        if (message.type === 'status') {
            logger.debug('Atualização de status ignorada');
            return;
        }

        logger.info(`Nova mensagem recebida: ${message.body}`);
        
        // Verificar se é mensagem de grupo
        const chat = await message.getChat();
        const isGroup = chat.isGroup;
        
        // Processar e salvar a mensagem
        const messageData = {
            from: message.from,
            body: message.body,
            timestamp: new Date().toISOString(),
            messageId: message.id._serialized,
            isFromMe: message.fromMe,
            isGroup: isGroup
        };
        
        // Se for mensagem de grupo, adicionar informações de grupo
        if (isGroup) {
            messageData.groupId = chat.id._serialized;
            messageData.groupName = chat.name;
            
            // Obter informações do autor
            const contact = await message.getContact();
            messageData.authorId = contact.id._serialized;
            messageData.authorName = contact.name || contact.pushname || contact.id.user;
            
            logger.info(`Mensagem de grupo recebida - Grupo: ${messageData.groupName}, Autor: ${messageData.authorName}`);
        }
        
        // Se a mensagem contiver mídia, processá-la
        if (message.hasMedia) {
            const media = await message.downloadMedia();
            if (media) {
                // Determinar tipo de mídia
                let mediaType = 'unknown';
                if (media.mimetype.startsWith('image/')) {
                    mediaType = 'image';
                } else if (media.mimetype.startsWith('audio/')) {
                    mediaType = 'audio';
                } else if (media.mimetype.startsWith('video/')) {
                    mediaType = 'video';
                } else if (media.mimetype.startsWith('application/')) {
                    mediaType = 'document';
                }
                
                // Adicionar informações de mídia
                messageData.mediaUrl = `mídia_${message.id._serialized}`;
                messageData.mediaType = mediaType;
                messageData.mimetype = media.mimetype;
                messageData.filename = media.filename;
                messageData.body = message.caption || 'Mídia enviada';
                
                // TODO: Implementar upload para Firebase Storage
            }
        }
        
        // Salvar mensagem no Firebase
        const result = await saveMessageToFirebase(messageData);
        
        // Transmitir mensagem para todos os clientes WebSocket
        broadcastToWebSocketClients(JSON.stringify({ 
            type: 'message', 
            data: messageData 
        }));
        
        // Emitir evento para clientes Socket.IO
        io.emit('message', messageData);
        
    } catch (error) {
        logger.error('Erro ao processar nova mensagem', { error: error.message });
        console.error('Erro ao processar nova mensagem:', error);
    }
});

// Quando enviar uma mensagem
client.on('message_create', async (message) => {
    // Apenas processar mensagens enviadas por mim
    if (message.fromMe) {
        try {
            // Verificar se é mensagem de grupo
            const chat = await message.getChat();
            const isGroup = chat.isGroup;
            
            logger.info(`Mensagem enviada para ${isGroup ? 'grupo' : 'contato'}`, {
                to: message.to,
                body: message.body
            });
            
            // Construir dados da mensagem
            const messageData = {
                from: message.to,
                body: message.body,
                timestamp: new Date().toISOString(),
                messageId: message.id._serialized,
                isFromMe: true,
                isGroup: isGroup
            };
            
            // Se for mensagem de grupo, adicionar informações de grupo
            if (isGroup) {
                messageData.groupId = chat.id._serialized;
                messageData.groupName = chat.name;
                
                // Obter informações do autor (neste caso, eu mesmo)
                const clientInfo = await client.getContactById(client.info.wid._serialized);
                messageData.authorId = clientInfo.id._serialized;
                messageData.authorName = clientInfo.name || clientInfo.pushname || 'Eu';
            }
            
            // Verificar se é mensagem com mídia
            if (message.hasMedia) {
                try {
                    const media = await message.downloadMedia();
                    
                    // Determinar tipo de mídia
                    let mediaType = 'unknown';
                    if (media.mimetype.startsWith('image/')) {
                        mediaType = 'image';
                    } else if (media.mimetype.startsWith('audio/')) {
                        mediaType = 'audio';
                    } else if (media.mimetype.startsWith('video/')) {
                        mediaType = 'video';
                    } else if (media.mimetype.startsWith('application/')) {
                        mediaType = 'document';
                    }
                    
                    // Adicionar informações de mídia
                    messageData.mediaUrl = `mídia_${message.id._serialized}`;
                    messageData.mediaType = mediaType;
                    messageData.mimetype = media.mimetype;
                    messageData.filename = media.filename;
                    messageData.body = message.caption || 'Mídia enviada';
                } catch (mediaErr) {
                    logger.error('Erro ao baixar mídia:', { error: mediaErr.message });
                }
            }
            
            // Salvar mensagem enviada no Firebase
            await saveMessageToFirebase(messageData);
        } catch (error) {
            logger.error('Erro ao processar mensagem enviada', { error: error.message });
            console.error('Erro ao processar mensagem enviada:', error);
        }
    }
});

// Rotas da API
app.post('/send-message', async (req, res) => {
    try {
        const { to, message } = req.body;
        
        if (!to || !message) {
            return res.status(400).json({
                status: false,
                message: 'Número e mensagem são obrigatórios'
            });
        }

        const msg = await client.sendMessage(to + '@c.us', message);
        
        // Salvar mensagem enviada no Firebase
        const messageData = {
            from: to + '@c.us',
            body: message,
            timestamp: new Date(),
            isFromMe: true,
            messageId: msg.id._serialized
        };
        
        await saveMessageToFirebase(messageData);
        
        logger.info('Mensagem enviada', {
            to: to,
            messageId: msg.id._serialized
        });

        res.status(200).json({
            status: true,
            message: 'Mensagem enviada com sucesso',
            data: {
                messageId: msg.id._serialized
            }
        });

    } catch (error) {
        logger.error('Erro ao enviar mensagem', {
            error: error.message
        });

        res.status(500).json({
            status: false,
            message: 'Erro ao enviar mensagem',
            error: error.message
        });
    }
});

// Inicia o servidor HTTP/WebSocket assim que o script for carregado
server.listen(5000, () => {
    console.log('Servidor WebSocket rodando na porta 5000');
    logger.info('Servidor WebSocket iniciado na porta 5000');
});

// Inicialização com tratamento de erros do cliente WhatsApp
const startServer = async () => {
    console.log('Inicializando o WhatsApp...');
    try {
        await client.initialize();
        console.log('Cliente WhatsApp iniciado com sucesso');
        logger.info('Cliente WhatsApp iniciado com sucesso');
    } catch (error) {
        console.error('Erro ao inicializar cliente WhatsApp:', error);
        logger.error('Erro ao inicializar cliente WhatsApp', { error });
    }
};

startServer();