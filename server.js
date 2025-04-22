const express = require('express');
const { Server } = require('socket.io');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const path = require('path');
const config = require('./config');
const admin = require('firebase-admin');
const rateLimit = require('express-rate-limit');
const winston = require('winston');

// Configuração do logger
const logger = winston.createLogger({
    level: config.logging.level,
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: config.logging.file }),
        new winston.transports.Console()
    ]
});

// Inicialização do Firebase Admin
try {
    const serviceAccount = require('./agentewhatsappv1-firebase-adminsdk-fbsvc-54b4b70f96.json');
    
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        databaseURL: config.firebase.databaseURL
    });

    logger.info('Firebase Admin inicializado com sucesso');
} catch (error) {
    logger.error('Erro ao inicializar Firebase Admin:', error);
    process.exit(1);
}

const db = admin.firestore();

// Configuração do Express
const app = express();
const server = require('http').createServer(app);
const io = new Server(server);

// Configuração do rate limiting
const limiter = rateLimit({
    windowMs: config.rateLimit.windowMs,
    max: config.rateLimit.maxRequests
});

app.use(limiter);
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Estado da conexão
let connectionState = {
    status: 'disconnected',
    qr: null,
    lastError: null
};

// Criação do cliente WhatsApp
const client = new Client(config.whatsapp.clientConfig);

// Eventos do cliente WhatsApp
client.on('qr', async (qr) => {
    try {
        connectionState.qr = await qrcode.toDataURL(qr);
        connectionState.status = 'qr_ready';
        io.emit('qr', connectionState.qr);
        logger.info('QR Code gerado');
    } catch (error) {
        logger.error('Erro ao gerar QR code:', error);
    }
});

client.on('ready', () => {
    connectionState.status = 'connected';
    connectionState.qr = null;
    io.emit('ready');
    logger.info('Cliente WhatsApp conectado');
});

client.on('disconnected', (reason) => {
    connectionState.status = 'disconnected';
    connectionState.lastError = reason;
    io.emit('disconnected', reason);
    logger.warn('Cliente WhatsApp desconectado:', reason);
    
    // Tenta reconectar
    setTimeout(() => {
        if (connectionState.status === 'disconnected') {
            logger.info('Tentando reconectar...');
            client.initialize();
        }
    }, config.whatsapp.reconnectInterval);
});

client.on('message', async (message) => {
    try {
        // Extrair informações da mensagem
        const sender = await message.getContact();
        const chat = await message.getChat();
        
        // Formatação do nome do contato
        const contactName = sender.name || sender.pushname || 'Desconhecido';
        
        // Obter ID de conversa existente ou criar nova
        let conversationId = message.from;
        
        // Estruturar mensagem para salvar no Firebase
        const messageData = {
            conversationId: conversationId,
            from: message.from,
            fromName: contactName,
            body: message.body,
            timestamp: admin.firestore.FieldValue.serverTimestamp(),
            type: message.type,
            hasMedia: message.hasMedia,
            direction: 'received', // Para diferenciar de mensagens enviadas
            isProcessed: false,
            isRead: false
        };

        // Verificar se a conversa já existe
        const conversationRef = db.collection('conversations').doc(conversationId);
        const conversationDoc = await conversationRef.get();
        
        // Se não existir, criar nova conversa
        if (!conversationDoc.exists) {
            await conversationRef.set({
                id: conversationId,
                client: {
                    id: message.from,
                    name: contactName,
                    phone: message.from.replace('@c.us', '')
                },
                status: 'active',
                createdAt: admin.firestore.FieldValue.serverTimestamp(),
                updatedAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageBody: message.body,
                unreadCount: 1
            });
            
            logger.info('Nova conversa criada:', { 
                conversationId: conversationId,
                client: contactName
            });
        } else {
            // Atualizar conversa existente
            await conversationRef.update({
                updatedAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageBody: message.body,
                unreadCount: admin.firestore.FieldValue.increment(1)
            });
        }
        
        // Salvar mensagem na coleção de mensagens
        const messagesRef = db.collection('conversations').doc(conversationId).collection('messages');
        const docRef = await messagesRef.add(messageData);
        
        // Emitir evento para o frontend
        io.emit('message', {
            id: docRef.id,
            ...messageData,
            conversationId: conversationId
        });
        
        logger.info('Mensagem salva no Firebase:', { 
            id: docRef.id,
            from: contactName,
            conversationId: conversationId
        });
    } catch (error) {
        logger.error('Erro ao processar mensagem:', {
            error: error.message,
            from: message.from,
            body: message.body
        });
    }
});

// Enviar mensagem via API
app.post('/api/send-message', async (req, res) => {
    try {
        const { to, message } = req.body;
        
        if (!to || !message) {
            return res.status(400).json({
                status: false,
                message: 'Número e mensagem são obrigatórios'
            });
        }
        
        // Formatar número se necessário
        const formattedNumber = to.includes('@c.us') ? to : `${to}@c.us`;
        
        // Enviar mensagem
        const sentMessage = await client.sendMessage(formattedNumber, message);
        
        // Salvar mensagem enviada no Firebase
        const conversationId = formattedNumber;
        
        // Verificar se a conversa existe
        const conversationRef = db.collection('conversations').doc(conversationId);
        const conversationDoc = await conversationRef.get();
        
        if (!conversationDoc.exists) {
            // Criar conversa se não existir
            await conversationRef.set({
                id: conversationId,
                client: {
                    id: formattedNumber,
                    name: 'Cliente',
                    phone: to
                },
                status: 'active',
                createdAt: admin.firestore.FieldValue.serverTimestamp(),
                updatedAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageBody: message,
                unreadCount: 0
            });
        } else {
            // Atualizar conversa existente
            await conversationRef.update({
                updatedAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageAt: admin.firestore.FieldValue.serverTimestamp(),
                lastMessageBody: message
            });
        }
        
        // Salvar mensagem enviada
        const messageData = {
            conversationId: conversationId,
            from: 'system',
            fromName: 'Sistema',
            body: message,
            timestamp: admin.firestore.FieldValue.serverTimestamp(),
            type: 'chat',
            hasMedia: false,
            direction: 'sent',
            isProcessed: true,
            isRead: true,
            messageId: sentMessage.id._serialized
        };
        
        const messagesRef = db.collection('conversations').doc(conversationId).collection('messages');
        await messagesRef.add(messageData);
        
        res.status(200).json({
            status: true,
            message: 'Mensagem enviada com sucesso',
            data: {
                messageId: sentMessage.id._serialized
            }
        });
        
        logger.info('Mensagem enviada:', {
            to: formattedNumber,
            messageId: sentMessage.id._serialized
        });
    } catch (error) {
        logger.error('Erro ao enviar mensagem:', error);
        res.status(500).json({
            status: false,
            message: 'Erro ao enviar mensagem',
            error: error.message
        });
    }
});

// Rota para verificar mensagens
app.get('/api/messages/:number', async (req, res) => {
    try {
        const number = req.params.number + '@c.us';
        const conversationRef = db.collection('conversations').doc(number);
        const messagesRef = conversationRef.collection('messages');
        const snapshot = await messagesRef
            .orderBy('timestamp', 'desc')
            .limit(10)
            .get();

        const messages = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            messages.push({
                id: doc.id,
                ...data,
                timestamp: data.timestamp ? data.timestamp.toDate() : new Date()
            });
        });

        logger.info('Mensagens encontradas:', { 
            number, 
            count: messages.length 
        });
        
        res.json(messages);
    } catch (error) {
        logger.error('Erro ao buscar mensagens:', error);
        res.status(500).json({ error: 'Erro ao buscar mensagens' });
    }
});

// Rota para status
app.get('/status', (req, res) => {
    res.json(connectionState);
});

// Rota para conversas
app.get('/api/conversations', async (req, res) => {
    try {
        const conversationsRef = db.collection('conversations');
        const snapshot = await conversationsRef
            .orderBy('lastMessageAt', 'desc')
            .limit(20)
            .get();

        const conversations = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            conversations.push({
                id: doc.id,
                ...data,
                createdAt: data.createdAt ? data.createdAt.toDate() : null,
                updatedAt: data.updatedAt ? data.updatedAt.toDate() : null,
                lastMessageAt: data.lastMessageAt ? data.lastMessageAt.toDate() : null
            });
        });

        res.json(conversations);
    } catch (error) {
        logger.error('Erro ao buscar conversas:', error);
        res.status(500).json({ error: 'Erro ao buscar conversas' });
    }
});

// Inicialização do servidor
server.listen(config.port, () => {
    logger.info(`Servidor iniciado na porta ${config.port}`);
    client.initialize().catch(error => {
        logger.error('Erro ao inicializar cliente WhatsApp:', error);
    });
}); 
}); 