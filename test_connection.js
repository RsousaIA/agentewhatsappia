const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const log = require('./logger');
const sessionManager = require('./session_manager');

async function testConnection() {
    log.info('Iniciando teste de conexão...');

    try {
        // Configura o cliente WhatsApp
        const client = new Client({
            authStrategy: {
                async get() {
                    return await sessionManager.loadSession('test-connection');
                },
                async set(sessionData) {
                    await sessionManager.saveSession({ ...sessionData, clientId: 'test-connection' });
                },
                async clear() {
                    await sessionManager.clearSession('test-connection');
                }
            },
            puppeteer: {
                headless: true,
                args: ['--no-sandbox']
            }
        });

        // Evento de QR Code
        client.on('qr', (qr) => {
            qrcode.generate(qr, { small: true });
            log.whatsapp('QR Code gerado para teste');
        });

        // Evento de ready
        client.on('ready', () => {
            log.whatsapp('Cliente WhatsApp está pronto para teste');
            console.log('✅ Conexão com WhatsApp estabelecida com sucesso!');
        });

        // Evento de mensagem
        client.on('message', async (message) => {
            log.message('Mensagem recebida durante teste', {
                from: message.from,
                type: message.type,
                hasMedia: message.hasMedia
            });

            if (message.hasMedia) {
                log.media('Mídia recebida durante teste', {
                    type: message.type
                });
            }
        });

        // Inicializa o cliente
        await client.initialize();
        log.info('Cliente WhatsApp inicializado para teste');

        // Aguarda 30 segundos para testar recebimento de mensagens
        console.log('Aguardando 30 segundos para testar recebimento de mensagens...');
        await new Promise(resolve => setTimeout(resolve, 30000));

        // Desconecta o cliente
        await client.destroy();
        log.info('Teste de conexão concluído');

    } catch (error) {
        log.error('Erro durante teste de conexão', {
            error: error.message,
            stack: error.stack
        });
        console.error('❌ Erro durante teste de conexão:', error.message);
        process.exit(1);
    }
}

// Executa o teste
testConnection(); 