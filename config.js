require('dotenv').config();
const { LocalAuth } = require('whatsapp-web.js');
const puppeteer = require('puppeteer');

module.exports = {
    // Configurações do servidor
    port: process.env.API_PORT || 3000,
    
    // Configurações do Firebase
    firebase: {
        projectId: process.env.FIREBASE_PROJECT_ID,
        privateKey: process.env.FIREBASE_PRIVATE_KEY,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        apiKey: process.env.FIREBASE_API_KEY,
        authDomain: process.env.FIREBASE_AUTH_DOMAIN,
        storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
        messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
        appId: process.env.FIREBASE_APP_ID,
        databaseURL: process.env.FIREBASE_DATABASE_URL
    },

    // Configurações do WhatsApp
    whatsapp: {
        // Tempo máximo de espera para reconexão (em milissegundos)
        reconnectTimeout: parseInt(process.env.WHATSAPP_RECONNECT_INTERVAL) || 30000,
        
        // Número máximo de tentativas de reconexão
        maxReconnectAttempts: parseInt(process.env.WHATSAPP_MAX_RETRIES) || 5,
        
        // Intervalo entre tentativas de reconexão (em milissegundos)
        reconnectInterval: parseInt(process.env.WHATSAPP_RECONNECT_INTERVAL) || 5000,
        
        // Configurações do cliente
        clientConfig: {
            authStrategy: new LocalAuth({
                clientId: "agente-suporte",
                dataPath: process.env.WHATSAPP_SESSION_PATH || "./whatsapp-sessions"
            }),
            puppeteer: {
                headless: true,
                args: (process.env.WHATSAPP_PUPPETEER_ARGS || '--no-sandbox,--disable-setuid-sandbox').split(','),
                executablePath: puppeteer.executablePath()
            }
        }
    },

    // Configurações de logging
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        file: process.env.PM2_LOG_PATH || 'logs/whatsapp-server.log'
    },

    // Configurações de cache
    cache: {
        // Tempo de expiração do cache em segundos
        ttl: parseInt(process.env.CACHE_TTL) || 3600,
        
        // Tamanho máximo do cache em bytes
        maxSize: parseInt(process.env.MAX_CACHE_SIZE) * 1024 * 1024 || 100 * 1024 * 1024 // 100MB
    },

    // Configurações de rate limiting
    rateLimit: {
        // Número máximo de requisições por IP
        maxRequests: parseInt(process.env.API_RATE_LIMIT) || 100,
        
        // Janela de tempo em minutos
        windowMs: parseInt(process.env.API_RATE_WINDOW) * 60 * 1000 || 15 * 60 * 1000 // 15 minutos
    }
}; 