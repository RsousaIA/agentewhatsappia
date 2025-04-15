require('dotenv').config();
const path = require('path');

const config = {
    // Configurações do WhatsApp
    whatsapp: {
        sessionPath: process.env.WHATSAPP_SESSION_PATH || path.join(__dirname, '.wwebjs_auth'),
        phoneNumber: process.env.WHATSAPP_PHONE_NUMBER,
        puppeteer: {
            headless: true,
            args: ['--no-sandbox']
        }
    },

    // Configurações do Servidor
    server: {
        host: process.env.SERVER_HOST || 'localhost',
        port: parseInt(process.env.SERVER_PORT, 10) || 3000
    },

    // Configurações do Socket.IO
    socketio: {
        cors: {
            origin: process.env.SOCKETIO_CORS_ORIGIN || 'http://localhost:3000',
            methods: ['GET', 'POST']
        }
    },

    // Configurações de Log
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        file: process.env.LOG_FILE || path.join(__dirname, 'logs', 'app.log')
    }
};

module.exports = config; 