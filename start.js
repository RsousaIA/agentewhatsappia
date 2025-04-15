const express = require('express');
const path = require('path');
const { exec } = require('child_process');
const readline = require('readline');
const open = require('open');
const cors = require('cors');

const app = express();
const PORT = 3001;

// Configurar pasta estática e CORS
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.static(path.join(__dirname, 'templates')));
app.use(cors());
app.use(express.json());

// Rotas da API
app.get('/api/metricas/todas-metricas', async (req, res) => {
    try {
        const result = await executarComando(`"${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python "${process.cwd()}\\utils/get_metricas.py"`);
        res.json(JSON.parse(result));
    } catch (error) {
        console.error(`❌ Erro ao obter métricas: ${error.message}`);
        res.status(500).json({ erro: true, mensagem: error.message });
    }
});

app.get('/api/metricas/avaliacoes', async (req, res) => {
    try {
        const result = await executarComando(`"${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python "${process.cwd()}\\utils/get_avaliacoes.py"`);
        res.json(JSON.parse(result));
    } catch (error) {
        console.error(`❌ Erro ao obter avaliações: ${error.message}`);
        res.status(500).json({ erro: true, mensagem: error.message });
    }
});

app.get('/api/metricas/eficiencia-atendentes', async (req, res) => {
    try {
        const result = await executarComando(`"${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python "${process.cwd()}\\utils/get_eficiencia.py"`);
        res.json(JSON.parse(result));
    } catch (error) {
        console.error(`❌ Erro ao obter eficiência dos atendentes: ${error.message}`);
        res.status(500).json({ erro: true, mensagem: error.message });
    }
});

// Criar interface para leitura do console
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

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

// Função para perguntar
function perguntar(pergunta) {
    return new Promise((resolve) => {
        rl.question(pergunta, (resposta) => {
            resolve(resposta);
        });
    });
}

// Iniciar o servidor web
app.listen(PORT, () => {
    console.log(`📱 Servidor web iniciado na porta ${PORT}`);
});

// Função principal - menu
async function mostrarMenu() {
    console.log('\n📱 Menu Principal:');
    console.log('1. Iniciar Agente Coletor');
    console.log('2. Iniciar Agente Avaliador');
    console.log('3. Ver Dashboard');
    console.log('4. Ver Logs');
    console.log('5. Sair');
    console.log('');
    
    const opcao = await perguntar('Escolha uma opção: ');
    
    switch (opcao.trim()) {
        case '1':
            await iniciarAgenteColetor();
            break;
        case '2':
            await iniciarAgenteAvaliador();
            break;
        case '3':
            await verDashboard();
            break;
        case '4':
            await verLogs();
            break;
        case '5':
            console.log('👋 Encerrando o sistema...');
            process.exit(0);
            break;
        default:
            console.log('❌ Opção inválida. Por favor, tente novamente.');
    }
    
    await mostrarMenu();
}

async function iniciarAgenteColetor() {
    console.log("\n🔄 Iniciando Agente Coletor...");
    
    // O servidor Node.js já está rodando em segundo plano
    // Iniciar o agente Python em segundo plano (usando start em vez de await)
    try {
        const comando = `start cmd /c "title Agente Coletor && "${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python -c "from agent.collector_agent import get_collector_agent; agent = get_collector_agent(); agent.start()""`;
        
        // Executar sem aguardar (para não bloquear)
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

async function iniciarAgenteAvaliador() {
    console.log('\n📊 Iniciando Agente Avaliador...');
    try {
        const comando = `start cmd /c "title Agente Avaliador && "${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python -c "from agent.evaluator_agent import get_evaluator_agent; agent = get_evaluator_agent(); agent.start()""`;
        
        // Executar sem aguardar (para não bloquear)
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

async function verDashboard() {
    console.log('\n🌐 Abrindo dashboard no navegador...');
    try {
        // Tentar abrir o dashboard de várias formas para garantir que funcione
        try {
            // Tenta primeiro pelo método tradicional
            await open('http://localhost:3001/dashboard.html');
        } catch (e) {
            console.log('Tentando método alternativo para abrir o dashboard...');
            // Método alternativo usando o comando do sistema
            const comando = `start http://localhost:3001/dashboard.html`;
            exec(comando);
        }
        console.log('✅ Dashboard aberto no navegador!');
    } catch (error) {
        console.error(`❌ Erro ao abrir dashboard: ${error.message}`);
    }
}

async function verLogs() {
    console.log('\n📜 Exibindo logs do sistema...');
    try {
        const comando = `"${process.cwd()}\\venv\\Scripts\\activate.bat" && set PYTHONPATH=${process.cwd()} && python "${process.cwd()}\\utils\\view_logs.py"`;
        const logs = await executarComando(comando);
        console.log(logs);
    } catch (error) {
        console.error(`❌ Erro ao exibir logs: ${error.message}`);
    }
}

// Iniciar o menu principal
mostrarMenu(); 