const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;
const fs = require('fs');
const path = require('path');

// Configurações para comunicação com Python
const PYTHON_SERVER_URL = process.env.PYTHON_SERVER_URL || 'http://127.0.0.1:5000';
const axios = require('axios');

// Configuração para armazenamento temporário de mensagens quando o servidor Python estiver offline
const MENSAGENS_PENDENTES_DIR = path.join(__dirname, '../data/mensagens_pendentes');
let serverRetryCount = 0;
const MAX_RETRY_COUNT = 5;

// Garantir que o diretório de mensagens pendentes exista
if (!fs.existsSync(MENSAGENS_PENDENTES_DIR)) {
    fs.mkdirSync(MENSAGENS_PENDENTES_DIR, { recursive: true });
    console.log(`Diretório para mensagens pendentes criado: ${MENSAGENS_PENDENTES_DIR}`);
}

// Importação do Firebase
const admin = require('firebase-admin');
let firebaseInitialized = false;

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

// Função para inicializar o Firebase
function initFirebase() {
    if (firebaseInitialized) return;
    
    try {
        // Verificar se as credenciais estão definidas como variável de ambiente ou arquivo
        const credPath = process.env.FIREBASE_CREDENTIALS_PATH;
        const credJson = process.env.FIREBASE_CREDENTIALS_JSON;
        
        let serviceAccount;
        
        if (credJson) {
            // Usar credenciais como JSON string
            serviceAccount = JSON.parse(credJson);
        } else if (credPath) {
            // Usar arquivo de credenciais
            serviceAccount = require(credPath);
        } else {
            console.error("Credenciais do Firebase não configuradas");
            return;
        }
        
        // Inicializar o Firebase
        admin.initializeApp({
            credential: admin.credential.cert(serviceAccount)
        });
        
        firebaseInitialized = true;
        console.log("Firebase inicializado com sucesso");
    } catch (error) {
        console.error(`Erro ao inicializar Firebase: ${error.message}`);
    }
}

// Função para salvar mensagem no Firebase
async function saveMessageToFirebase(messageData) {
    if (!firebaseInitialized) {
        initFirebase();
    }
    
    if (!firebaseInitialized) {
        console.error("Firebase não inicializado. Não é possível salvar mensagem.");
        return;
    }
    
    try {
        const db = admin.firestore();
        
        // Preparar dados
        const messageId = messageData.id;
        const fromNumber = messageData.from.split('@')[0];
        const toNumber = messageData.to ? messageData.to.split('@')[0] : '';
        const isFromClient = messageData.from !== messageData.to;
        const clientPhone = isFromClient ? fromNumber : toNumber;
        
        // Verificar se já existe uma conversa ativa para este cliente
        const conversationQuery = await db.collection('conversas')
            .where('cliente_telefone', '==', clientPhone)
            .where('status', '==', 'ativo')
            .limit(1)
            .get();
        
        let conversationId;
        
        if (conversationQuery.empty) {
            // Criar nova conversa
            const conversationRef = db.collection('conversas').doc();
            await conversationRef.set({
                cliente_telefone: clientPhone,
                status: 'ativo',
                data_inicio: admin.firestore.FieldValue.serverTimestamp(),
                ultima_atualizacao: admin.firestore.FieldValue.serverTimestamp()
            });
            conversationId = conversationRef.id;
            console.log(`Nova conversa criada: ${conversationId}`);
        } else {
            // Usar conversa existente
            conversationId = conversationQuery.docs[0].id;
        }
        
        // Salvar mensagem
        await db.collection('mensagens').doc(messageId).set({
            conversa_id: conversationId,
            message_id: messageId,
            remetente_tipo: isFromClient ? 'cliente' : 'atendente',
            data_hora: new Date(messageData.timestamp * 1000),
            conteudo: messageData.body,
            tipo_mensagem: messageData.type || 'texto'
        });
        
        // Atualizar timestamp da conversa
        await db.collection('conversas').doc(conversationId).update({
            ultima_atualizacao: admin.firestore.FieldValue.serverTimestamp()
        });
        
        console.log(`Mensagem ${messageId} salva no Firebase com sucesso`);
    } catch (error) {
        console.error(`Erro ao salvar mensagem no Firebase: ${error.message}`);
    }
}

// Função para salvar mensagem temporariamente
function salvarMensagemLocalmente(messageData) {
    try {
        const messageId = messageData.id;
        const filePath = path.join(MENSAGENS_PENDENTES_DIR, `msg_${messageId}.json`);
        fs.writeFileSync(filePath, JSON.stringify(messageData, null, 2));
        console.log(`📥 Mensagem ${messageId} salva localmente para processamento posterior`);
        return true;
    } catch (error) {
        console.error(`❌ Erro ao salvar mensagem localmente: ${error.message}`);
        return false;
    }
}

// Função para verificar servidor Python
async function verificarServidorPython() {
    try {
        await axios.get(`${PYTHON_SERVER_URL}/api/status`);
        console.log('✅ Servidor Python está online');
        return true;
    } catch (error) {
        console.error(`❌ Servidor Python não está disponível: ${error.message}`);
        return false;
    }
}

// Função para enviar mensagens pendentes
async function enviarMensagensPendentes() {
    try {
        // Verificar se o servidor está online
        const servidorOnline = await verificarServidorPython();
        if (!servidorOnline) return;
        
        // Ler diretório de mensagens pendentes
        const files = fs.readdirSync(MENSAGENS_PENDENTES_DIR);
        
        if (files.length > 0) {
            console.log(`🔄 Enviando ${files.length} mensagens pendentes...`);
            
            for (const file of files) {
                try {
                    const filePath = path.join(MENSAGENS_PENDENTES_DIR, file);
                    const messageData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                    
                    // Tentar enviar para o servidor Python
                    await axios.post(`${PYTHON_SERVER_URL}/api/webhook/message`, messageData);
                    
                    // Se enviou com sucesso, remover arquivo
                    fs.unlinkSync(filePath);
                    console.log(`✅ Mensagem pendente ${file} processada e removida com sucesso`);
                } catch (error) {
                    console.error(`❌ Erro ao processar mensagem pendente ${file}: ${error.message}`);
                }
            }
        }
    } catch (error) {
        console.error(`❌ Erro ao verificar mensagens pendentes: ${error.message}`);
    }
}

// Verificar mensagens pendentes a cada 30 segundos
setInterval(enviarMensagensPendentes, 30000);

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
    
    // Desativado temporariamente (será usado quando migrarmos para Firebase)
    // await saveMessageToFirebase(messageData);
    
    // Callback para Python (se houver)
    if (messageCallback) {
        messageCallback(messageData);
    }
    
    // Enviar notificação para o servidor Python
    try {
        console.log(`📤 Tentando enviar mensagem para Python API: ${message.id.id}`);
        console.log(`URL: ${PYTHON_SERVER_URL}/api/webhook/message`);
        console.log(`Dados: ${JSON.stringify(messageData)}`);
        
        await axios.post(`${PYTHON_SERVER_URL}/api/webhook/message`, messageData);
        console.log(`✅ Mensagem enviada para Python API: ${message.id.id}`);
        serverRetryCount = 0; // Resetar contador de tentativas
    } catch (error) {
        console.error(`❌ Erro ao enviar mensagem para Python: ${error.message}`);
        console.error('Detalhes do erro:', error.response ? error.response.data : 'Sem resposta');
        
        // Salvar mensagem localmente para tentar novamente depois
        salvarMensagemLocalmente(messageData);
        
        // Incrementar contador de falhas
        serverRetryCount++;
        
        // Se servidor falhar muitas vezes, tentar reiniciar
        if (serverRetryCount >= MAX_RETRY_COUNT) {
            console.log(`⚠️ Servidor Python falhou ${MAX_RETRY_COUNT} vezes, tentando reiniciar...`);
            try {
                const { exec } = require('child_process');
                exec('start cmd /c "title Servidor Flask && cd /d %CD% && venv\\Scripts\\activate.bat && python app.py"', (err) => {
                    if (err) {
                        console.error(`❌ Erro ao tentar reiniciar servidor Flask: ${err.message}`);
                    } else {
                        console.log('🔄 Comando para reiniciar Flask executado');
                        serverRetryCount = 0;
                    }
                });
            } catch (restartError) {
                console.error(`❌ Erro ao tentar reiniciar servidor Flask: ${restartError.message}`);
            }
        }
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

// Rota para obter métricas do Firebase
app.get('/api/metricas/todas-metricas', async (req, res) => {
    if (!firebaseInitialized) {
        initFirebase();
    }
    
    if (!firebaseInitialized) {
        return res.status(500).json({ error: "Firebase não inicializado" });
    }
    
    try {
        const db = admin.firestore();
        
        // Contar total de conversas
        const conversasSnapshot = await db.collection('conversas').get();
        const totalConversas = conversasSnapshot.size;
        
        // Contar mensagens
        const mensagensSnapshot = await db.collection('mensagens').get();
        const totalMensagens = mensagensSnapshot.size;
        
        // Métricas
        const metricas = {
            total_atendimentos: totalConversas,
            total_mensagens: totalMensagens,
            tempo_medio_resolucao: 0, // Implementar cálculo real posteriormente
            mensagens_por_conversa: totalConversas > 0 ? totalMensagens / totalConversas : 0
        };
        
        res.json(metricas);
    } catch (error) {
        console.error(`Erro ao obter métricas: ${error.message}`);
        res.status(500).json({ error: error.message });
    }
});

// Rota para listar conversas
app.get('/api/conversas', async (req, res) => {
    if (!firebaseInitialized) {
        initFirebase();
    }
    
    if (!firebaseInitialized) {
        return res.status(500).json({ error: "Firebase não inicializado" });
    }
    
    try {
        const db = admin.firestore();
        const conversasRef = db.collection('conversas')
            .orderBy('ultima_atualizacao', 'desc')
            .limit(50);
        
        const snapshot = await conversasRef.get();
        
        const conversas = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            conversas.push({
                id: doc.id,
                ...data
            });
        });
        
        res.json(conversas);
    } catch (error) {
        console.error(`Erro ao listar conversas: ${error.message}`);
        res.status(500).json({ error: error.message });
    }
});

// Rota para status de mensagens pendentes
app.get('/api/mensagens-pendentes', (req, res) => {
    try {
        const files = fs.readdirSync(MENSAGENS_PENDENTES_DIR);
        res.json({
            count: files.length,
            messages: files.map(file => {
                try {
                    const data = JSON.parse(fs.readFileSync(path.join(MENSAGENS_PENDENTES_DIR, file), 'utf8'));
                    return {
                        id: data.id,
                        from: data.from,
                        body: data.body && data.body.length > 30 ? data.body.substring(0, 30) + '...' : data.body,
                        timestamp: data.timestamp
                    };
                } catch (e) {
                    return { id: file, error: e.message };
                }
            })
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Adicionar rota de status para o servidor Python verificar
app.get('/api/status', (req, res) => {
    res.json({
        status: 'online',
        timestamp: new Date().toISOString()
    });
});

// Força o envio de mensagens pendentes na inicialização
setTimeout(enviarMensagensPendentes, 10000);

// Inicia o servidor
app.listen(port, () => {
    console.log(`📡 Servidor Node.js rodando na porta ${port}`);
});

// Inicia o cliente WhatsApp
console.log('🔄 Inicializando cliente WhatsApp...');
client.initialize(); 