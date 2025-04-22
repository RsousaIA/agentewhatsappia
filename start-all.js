const { exec, spawn } = require('child_process');
const express = require('express');
const { Server } = require('socket.io');
const path = require('path');
const open = require('open');
const cors = require('cors');

// Configurações
const DASHBOARD_PORT = 3000;
const WHATSAPP_PORT = 5000;
const API_PORT = 8000;

// Inicializa Express
const app = express();
const server = require('http').createServer(app);
const io = new Server(server);

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Função para executar comandos
function executarComando(comando) {
  return new Promise((resolve, reject) => {
    exec(comando, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ Erro ao executar comando: ${error.message}`);
        reject(error);
        return;
      }
      if (stderr) {
        console.warn(`⚠️ Aviso: ${stderr}`);
      }
      resolve(stdout);
    });
  });
}

// Iniciar servidor WhatsApp
function iniciarServidorWhatsApp() {
  console.log('🚀 Iniciando servidor WhatsApp...');
  
  const whatsappProcess = spawn('node', ['server.js'], {
    detached: true,
    stdio: 'pipe'
  });
  
  whatsappProcess.stdout.on('data', (data) => {
    console.log(`📱 WhatsApp: ${data}`);
    
    // Enviar informações do WhatsApp para o frontend via Socket.io
    const logLine = data.toString();
    if (logLine.includes('QR Code gerado')) {
      io.emit('whatsapp:qr', 'QR Code gerado. Acesse http://localhost:5000 para escanear.');
    } else if (logLine.includes('Cliente WhatsApp conectado')) {
      io.emit('whatsapp:connected', 'WhatsApp conectado com sucesso!');
    } else if (logLine.includes('Nova mensagem recebida')) {
      io.emit('whatsapp:message', 'Nova mensagem recebida.');
    }
  });
  
  whatsappProcess.stderr.on('data', (data) => {
    console.error(`❌ WhatsApp Erro: ${data}`);
  });
  
  whatsappProcess.on('close', (code) => {
    console.log(`📱 Servidor WhatsApp encerrado com código ${code}`);
  });
  
  console.log('✅ Servidor WhatsApp iniciado em segundo plano!');
  return whatsappProcess;
}

// Iniciar o frontend React
function iniciarFrontend() {
  console.log('🚀 Iniciando o frontend React...');
  
  const frontendProcess = spawn('npm', ['start'], {
    cwd: path.join(__dirname, 'frontend'),
    detached: true,
    stdio: 'pipe'
  });
  
  frontendProcess.stdout.on('data', (data) => {
    console.log(`🌐 Frontend: ${data}`);
  });
  
  frontendProcess.stderr.on('data', (data) => {
    console.error(`❌ Frontend Erro: ${data}`);
  });
  
  frontendProcess.on('close', (code) => {
    console.log(`🌐 Frontend encerrado com código ${code}`);
  });
  
  console.log('✅ Frontend iniciado em segundo plano!');
  return frontendProcess;
}

// Iniciar o agente coletor
async function iniciarAgenteColetor() {
  console.log('🤖 Iniciando Agente Coletor...');
  
  try {
    const comando = `start cmd /c "title Agente Coletor && "${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python -c "from agent.collector_agent import get_collector_agent; agent = get_collector_agent(); agent.start()""`;
    
    exec(comando, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ Erro ao iniciar Agente Coletor: ${error.message}`);
        return;
      }
      if (stderr) {
        console.warn(`⚠️ Aviso: ${stderr}`);
      }
    });
    
    console.log('✅ Agente Coletor iniciado em segundo plano!');
  } catch (error) {
    console.error(`❌ Erro ao iniciar Agente Coletor: ${error.message}`);
  }
}

// Iniciar o agente avaliador
async function iniciarAgenteAvaliador() {
  console.log('📊 Iniciando Agente Avaliador...');
  
  try {
    const comando = `start cmd /c "title Agente Avaliador && "${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python -c "from agent.evaluator_agent import get_evaluator_agent; agent = get_evaluator_agent(); agent.start()""`;
    
    exec(comando, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ Erro ao iniciar Agente Avaliador: ${error.message}`);
        return;
      }
      if (stderr) {
        console.warn(`⚠️ Aviso: ${stderr}`);
      }
    });
    
    console.log('✅ Agente Avaliador iniciado em segundo plano!');
  } catch (error) {
    console.error(`❌ Erro ao iniciar Agente Avaliador: ${error.message}`);
  }
}

// Rotas do painel de controle
app.get('/api/status', (req, res) => {
  res.json({
    whatsapp: 'conectado',
    frontendReact: 'ativo',
    agenteColetor: 'ativo',
    agenteAvaliador: 'ativo',
    ultimaAtualizacao: new Date().toISOString()
  });
});

// Iniciar todo o sistema
async function iniciarTudo() {
  try {
    // 1. Iniciar o servidor de controle
    server.listen(DASHBOARD_PORT, () => {
      console.log(`🚀 Servidor de controle iniciado na porta ${DASHBOARD_PORT}`);
    });
    
    // 2. Iniciar servidor WhatsApp
    const whatsappProcess = iniciarServidorWhatsApp();
    
    // 3. Iniciar frontend React
    const frontendProcess = iniciarFrontend();
    
    // 4. Iniciar agentes Python
    await iniciarAgenteColetor();
    await iniciarAgenteAvaliador();
    
    // 5. Abrir o dashboard no navegador após 5 segundos
    setTimeout(async () => {
      try {
        await open(`http://localhost:${DASHBOARD_PORT}`);
        console.log('🌐 Dashboard aberto no navegador!');
      } catch (error) {
        console.error(`❌ Erro ao abrir dashboard: ${error.message}`);
      }
    }, 5000);
    
    console.log('✅ Sistema completo iniciado com sucesso!');
    
    // Gerenciar encerramento do processo
    process.on('SIGINT', () => {
      console.log('👋 Recebido sinal de encerramento. Parando todos os serviços...');
      whatsappProcess.kill();
      frontendProcess.kill();
      process.exit(0);
    });
    
  } catch (error) {
    console.error(`❌ Erro ao iniciar o sistema: ${error.message}`);
  }
}

// Iniciar o sistema
iniciarTudo(); 