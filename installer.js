const { exec } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

console.log('👋 Bem-vindo ao Instalador do Agente de Suporte WhatsApp!');
console.log('Este instalador vai te guiar em todo o processo de configuração.\n');

async function perguntar(pergunta) {
    return new Promise((resolve) => {
        rl.question(pergunta, (resposta) => {
            resolve(resposta);
        });
    });
}

async function executarComando(comando) {
    return new Promise((resolve, reject) => {
        exec(comando, (error, stdout, stderr) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout);
        });
    });
}

async function verificarNode() {
    console.log('\n🔍 Verificando se o Node.js está instalado...');
    try {
        await executarComando('node --version');
        console.log('✅ Node.js encontrado!');
        return true;
    } catch (error) {
        console.log('❌ Node.js não encontrado!');
        console.log('Por favor, instale o Node.js em: https://nodejs.org/');
        return false;
    }
}

async function verificarNPM() {
    console.log('\n🔍 Verificando se o NPM está instalado...');
    try {
        await executarComando('npm --version');
        console.log('✅ NPM encontrado!');
        return true;
    } catch (error) {
        console.log('❌ NPM não encontrado!');
        return false;
    }
}

async function instalarDependencias() {
    console.log('\n📦 Instalando dependências...');
    try {
        await executarComando('npm install');
        console.log('✅ Dependências instaladas com sucesso!');
        return true;
    } catch (error) {
        console.log('❌ Erro ao instalar dependências:', error.message);
        return false;
    }
}

async function configurarBanco() {
    console.log('\n💾 Configurando banco de dados...');
    
    const host = await perguntar('Digite o host do banco de dados (padrão: localhost): ') || 'localhost';
    const user = await perguntar('Digite o usuário do banco de dados: ');
    const pass = await perguntar('Digite a senha do banco de dados: ');
    const db = await perguntar('Digite o nome do banco de dados (padrão: whatsapp_avaliacoes): ') || 'whatsapp_avaliacoes';

    const config = {
        DB_HOST: host,
        DB_USER: user,
        DB_PASS: pass,
        DB_NAME: db
    };

    // Salva configuração
    fs.writeFileSync('.env', Object.entries(config)
        .map(([key, value]) => `${key}=${value}`)
        .join('\n'));

    console.log('✅ Configuração do banco salva!');
    return true;
}

async function configurarWhatsApp() {
    console.log('\n📱 Configurando WhatsApp...');
    
    const apiKey = await perguntar('Digite sua chave da API do WhatsApp Business: ');
    
    // Adiciona ao .env
    fs.appendFileSync('.env', `\nWHATSAPP_API_KEY=${apiKey}`);
    
    console.log('✅ Configuração do WhatsApp salva!');
    return true;
}

async function iniciarSistema() {
    console.log('\n🚀 Iniciando o sistema...');
    try {
        await executarComando('node start.js');
    } catch (error) {
        console.log('❌ Erro ao iniciar o sistema:', error.message);
    }
}

async function main() {
    console.log('📋 Vamos começar a instalação!');
    
    // Verifica requisitos
    if (!await verificarNode()) return;
    if (!await verificarNPM()) return;
    
    // Instala dependências
    if (!await instalarDependencias()) return;
    
    // Configura banco
    if (!await configurarBanco()) return;
    
    // Configura WhatsApp
    if (!await configurarWhatsApp()) return;
    
    // Inicia sistema
    await iniciarSistema();
    
    rl.close();
}

main(); 