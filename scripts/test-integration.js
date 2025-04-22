const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const admin = require('firebase-admin');
const axios = require('axios');

// Inicializa Firebase
const serviceAccount = require('../firebase-credentials.json');
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

// Configuração do cliente WhatsApp
const client = new Client();

// Gera QR Code para autenticação
client.on('qr', (qr) => {
  qrcode.generate(qr, { small: true });
  console.log('QR Code gerado. Por favor, escaneie com seu WhatsApp.');
});

// Quando autenticado
client.on('ready', () => {
  console.log('Cliente WhatsApp conectado!');
  runIntegrationTests();
});

// Inicializa o cliente
client.initialize();

async function runIntegrationTests() {
  try {
    console.log('Iniciando testes de integração...');

    // 1. Teste de recebimento de mensagem
    console.log('Testando recebimento de mensagem...');
    const testMessage = {
      from: '5511999999999@c.us',
      body: 'Teste de integração',
      timestamp: Date.now()
    };

    // Simula recebimento de mensagem
    client.on('message', async (message) => {
      console.log('Mensagem recebida:', message.body);

      // 2. Verifica se a conversa foi criada no Firebase
      console.log('Verificando criação da conversa no Firebase...');
      const conversations = await db.collection('conversas')
        .where('cliente', '==', message.from)
        .get();

      if (conversations.empty) {
        throw new Error('Conversa não foi criada no Firebase');
      }
      console.log('Conversa criada com sucesso!');

      // 3. Verifica se a mensagem foi salva
      console.log('Verificando salvamento da mensagem...');
      const conversation = conversations.docs[0];
      const messages = await conversation.ref.collection('mensagens')
        .orderBy('timestamp', 'desc')
        .limit(1)
        .get();

      if (messages.empty) {
        throw new Error('Mensagem não foi salva');
      }
      console.log('Mensagem salva com sucesso!');

      // 4. Verifica se o agente coletor processou a mensagem
      console.log('Verificando processamento pelo agente coletor...');
      const processedMessage = messages.docs[0].data();
      if (!processedMessage.intent || !processedMessage.sentiment) {
        throw new Error('Mensagem não foi processada pelo agente coletor');
      }
      console.log('Mensagem processada com sucesso!');

      // 5. Verifica se o frontend está acessível
      console.log('Verificando acessibilidade do frontend...');
      try {
        const response = await axios.get('http://localhost:3000/api/health');
        if (response.status !== 200) {
          throw new Error('Frontend não está respondendo');
        }
        console.log('Frontend acessível!');
      } catch (error) {
        throw new Error('Erro ao acessar frontend: ' + error.message);
      }

      console.log('Todos os testes de integração foram concluídos com sucesso!');
      process.exit(0);
    });

    // Envia mensagem de teste
    await client.sendMessage(testMessage.from, testMessage.body);

  } catch (error) {
    console.error('Erro durante os testes de integração:', error);
    process.exit(1);
  }
} 