const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const { db, bucket } = require('./firebase.config');
const dotenv = require('dotenv');

// Carrega variáveis de ambiente
dotenv.config();

// Configuração do cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth({
        clientId: "whatsapp-test",
        dataPath: "./whatsapp-sessions"
    }),
    puppeteer: {
        headless: "new",
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage'
        ]
    }
});

// Função para criar ou atualizar conversa
async function updateConversation(phoneNumber, messageData) {
    try {
        const conversationRef = db.collection('conversas').doc(phoneNumber);
        const conversationDoc = await conversationRef.get();
        const timestamp = new Date();

        if (!conversationDoc.exists) {
            // Cria nova conversa
            await conversationRef.set({
                cliente: {
                    nome: messageData.senderName || 'Cliente',
                    telefone: phoneNumber
                },
                status: 'ativa',
                dataHoraInicio: timestamp,
                dataHoraEncerramento: null,
                ultimaMensagem: timestamp,
                agentesEnvolvidos: []
            });
            console.log('✅ Nova conversa criada:', phoneNumber);
        } else {
            // Atualiza conversa existente
            await conversationRef.update({
                ultimaMensagem: timestamp
            });
            console.log('✅ Conversa atualizada:', phoneNumber);
        }

        return conversationRef;
    } catch (error) {
        console.error('❌ Erro ao atualizar conversa:', error);
        throw error;
    }
}

// Função para salvar mensagem
async function saveMessage(conversationRef, messageData) {
    try {
        const timestamp = new Date();
        
        // Salva a mensagem como subcoleção
        await conversationRef.collection('mensagens').add({
            tipo: messageData.type || 'texto',
            conteudo: messageData.body,
            remetente: messageData.fromMe ? 'atendente' : 'cliente',
            timestamp: timestamp
        });
        
        console.log('✅ Mensagem salva na conversa:', messageData.id);
        return true;
    } catch (error) {
        console.error('❌ Erro ao salvar mensagem:', error);
        return false;
    }
}

// Função para processar mensagem
async function processMessage(message) {
    console.log('📩 Nova mensagem:', message.body);
    
    try {
        // Prepara dados da mensagem
        const messageData = {
            id: message.id.id,
            from: message.from,
            to: message.to,
            body: message.body,
            type: message.type,
            fromMe: message.fromMe,
            senderName: message.notifyName
        };
        
        // Obtém o número do telefone (remove o @c.us)
        const phoneNumber = message.fromMe ? message.to.split('@')[0] : message.from.split('@')[0];
        
        // Atualiza a conversa
        const conversationRef = await updateConversation(phoneNumber, messageData);
        
        // Salva a mensagem
        await saveMessage(conversationRef, messageData);
        
    } catch (error) {
        console.error('❌ Erro ao processar mensagem:', error);
    }
}

// Evento de QR Code
client.on('qr', (qr) => {
    console.log('🔄 QR Code recebido, escaneie para conectar:');
    qrcode.generate(qr, { small: true });
});

// Evento de autenticação
client.on('authenticated', () => {
    console.log('✅ Autenticado com sucesso!');
});

// Evento de pronto
client.on('ready', () => {
    console.log('✅ Cliente WhatsApp pronto!');
});

// Evento de mensagem recebida
client.on('message', async (message) => {
    await processMessage(message);
});

// Evento de mensagem enviada
client.on('message_create', async (message) => {
    if (message.fromMe) {
        await processMessage(message);
    }
});

// Inicia o cliente
console.log('🔄 Iniciando cliente WhatsApp...');
client.initialize(); 