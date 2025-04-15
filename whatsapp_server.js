const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');

// Carrega variáveis de ambiente
dotenv.config();

// Configuração do servidor WebSocket
const wss = new WebSocket.Server({ port: process.env.WHATSAPP_SERVER_PORT || 3000 });
const clients = new Set();

// Configuração do cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox'],
    }
});

// Gera um ID único para a conversa
function generateConversationId(from) {
    const date = new Date().toISOString().split('T')[0];
    return `${from}_${date}`;
}

// Processa mensagens de áudio
async function processAudioMessage(message) {
    try {
        const media = await message.downloadMedia();
        const buffer = Buffer.from(media.data, 'base64');
        
        // Salva o áudio temporariamente
        const audioPath = path.join(__dirname, 'temp', `${message.id.id}.ogg`);
        fs.writeFileSync(audioPath, buffer);
        
        // TODO: Implementar transcrição do áudio
        // Por enquanto, retornamos apenas o caminho do arquivo
        return {
            path: audioPath,
            mimetype: media.mimetype
        };
    } catch (error) {
        console.error('Erro ao processar áudio:', error);
        return null;
    }
}

// Evento quando o QR Code é gerado
client.on('qr', (qr) => {
    qrcode.generate(qr, { small: true });
    console.log('QR Code gerado. Escaneie com o WhatsApp.');
});

// Evento quando o cliente está pronto
client.on('ready', () => {
    console.log('Cliente WhatsApp está pronto!');
});

// Evento quando uma mensagem é recebida
client.on('message', async (message) => {
    try {
        const from = message.from;
        const conversationId = generateConversationId(from);
        
        let messageData = {
            conversation_id: conversationId,
            from: from,
            timestamp: new Date().toISOString(),
            direction: 'received',
            type: 'text',
            body: message.body
        };

        // Processa diferentes tipos de mensagem
        if (message.hasMedia) {
            if (message.type === 'audio') {
                const audioData = await processAudioMessage(message);
                messageData = {
                    ...messageData,
                    type: 'audio',
                    audio: audioData,
                    text: '[Áudio]' // Será substituído pela transcrição
                };
            } else {
                const media = await message.downloadMedia();
                messageData = {
                    ...messageData,
                    type: 'media',
                    mimetype: media.mimetype,
                    data: media.data
                };
            }
        }

        // Envia a mensagem para todos os clientes WebSocket conectados
        clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(messageData));
            }
        });
    } catch (error) {
        console.error('Erro ao processar mensagem:', error);
    }
});

// Evento quando uma mensagem é enviada
client.on('message_create', async (message) => {
    try {
        if (message.fromMe) {
            const to = message.to;
            const conversationId = generateConversationId(to);
            
            let messageData = {
                conversation_id: conversationId,
                to: to,
                timestamp: new Date().toISOString(),
                direction: 'sent',
                type: 'text',
                body: message.body
            };

            // Processa diferentes tipos de mensagem enviada
            if (message.hasMedia) {
                if (message.type === 'audio') {
                    const audioData = await processAudioMessage(message);
                    messageData = {
                        ...messageData,
                        type: 'audio',
                        audio: audioData,
                        text: '[Áudio]'
                    };
                } else {
                    const media = await message.downloadMedia();
                    messageData = {
                        ...messageData,
                        type: 'media',
                        mimetype: media.mimetype,
                        data: media.data
                    };
                }
            }

            // Envia a mensagem para todos os clientes WebSocket conectados
            clients.forEach(client => {
                if (client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify(messageData));
                }
            });
        }
    } catch (error) {
        console.error('Erro ao processar mensagem enviada:', error);
    }
});

// Inicializa o servidor WebSocket
wss.on('connection', (ws) => {
    console.log('Novo cliente WebSocket conectado');
    clients.add(ws);

    ws.on('message', async (message) => {
        try {
            const data = JSON.parse(message);
            
            if (data.to && data.message) {
                // Envia mensagem via WhatsApp
                await client.sendMessage(data.to, data.message);
            }
        } catch (error) {
            console.error('Erro ao processar mensagem do WebSocket:', error);
        }
    });

    ws.on('close', () => {
        console.log('Cliente WebSocket desconectado');
        clients.delete(ws);
    });
});

// Inicializa o cliente WhatsApp
client.initialize();

// Cria diretório temporário se não existir
const tempDir = path.join(__dirname, 'temp');
if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir);
} 