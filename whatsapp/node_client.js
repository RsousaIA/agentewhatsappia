const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;

console.log("==============================================");
console.log("      INICIANDO SERVIDOR WHATSAPP NODE.JS      ");
console.log("==============================================");

// Configurar CORS e JSON parsing
app.use(cors());
app.use(express.json());

// Configuração do cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: 'whatsapp-support-agent'
    }),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-extensions'],
        headless: true
    }
});

// Variáveis para callbacks
let messageCallback = null;
let qrCallback = null;

// Eventos do cliente
client.on('qr', (qr) => {
    // Gera e mostra o QR code no terminal
    console.log('\n\n==== ESCANEIE O QR CODE COM SEU WHATSAPP ====\n\n');
    qrcode.generate(qr, { small: true });
    console.log('\n\n=========================================\n\n');
    
    // Emite evento para o frontend ou Python (se houver callback)
    if (qrCallback) {
        qrCallback(qr);
    }
});

client.on('ready', () => {
    console.log('\n✅ WHATSAPP CONECTADO COM SUCESSO!\n');
});

client.on('message', async (message) => {
    // Processa mensagem recebida
    const messageData = {
        id: message.id.id,
        from: message.from,
        to: message.to,
        body: message.body,
        timestamp: message.timestamp,
        type: message.type,
        isGroup: message.isGroup
    };
    
    console.log(`📱 Nova mensagem de ${message.from}: ${message.body}`);
    
    // Callback para Python (se houver)
    if (messageCallback) {
        messageCallback(messageData);
    }
});

// API REST
app.get('/', (req, res) => {
    res.send('Servidor WhatsApp Node.js em execução');
});

// Rota para verificar status do cliente
app.get('/status', (req, res) => {
    const isReady = client.info !== undefined;
    res.json({
        status: isReady ? 'connected' : 'disconnected',
        info: isReady ? {
            name: client.info.pushname,
            phone: client.info.wid.user
        } : null
    });
});

// Rota para enviar mensagem
app.post('/send-message', async (req, res) => {
    try {
        const { to, message } = req.body;
        
        // Formata número se necessário
        const formattedNumber = to.includes('@c.us') ? to : `${to}@c.us`;
        
        // Envia mensagem
        const response = await client.sendMessage(formattedNumber, message);
        
        res.json({
            success: true,
            messageId: response.id.id
        });
    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Rota para obter histórico de conversa
app.get('/chat-history/:phone', async (req, res) => {
    try {
        const { phone } = req.params;
        const { limit = 100 } = req.query;
        
        const formattedNumber = phone.includes('@c.us') ? phone : `${phone}@c.us`;
        const chat = await client.getChatById(formattedNumber);
        const messages = await chat.fetchMessages({ limit: parseInt(limit) });
        
        const formattedMessages = messages.map(msg => ({
            id: msg.id.id,
            from: msg.from,
            to: msg.to,
            body: msg.body,
            timestamp: msg.timestamp,
            type: msg.type
        }));
        
        res.json({
            success: true,
            messages: formattedMessages
        });
    } catch (error) {
        console.error('Erro ao obter histórico:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Rota para marcar mensagens como lidas
app.post('/mark-as-read', async (req, res) => {
    try {
        const { messageIds } = req.body;
        
        for (const msgId of messageIds) {
            const msg = await client.getMessageById(msgId);
            if (msg) {
                await msg.markAsSeen();
            }
        }
        
        res.json({
            success: true
        });
    } catch (error) {
        console.error('Erro ao marcar como lido:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Rota para registrar callback de mensagem
app.post('/register-message-callback', (req, res) => {
    messageCallback = (data) => {
        console.log('Callback de mensagem registrado');
    };
    res.json({ success: true });
});

// Inicia o servidor
app.listen(port, () => {
    console.log(`📡 Servidor Node.js rodando na porta ${port}`);
});

// Inicia o cliente WhatsApp
console.log('🔄 Inicializando cliente WhatsApp...');
client.initialize(); 