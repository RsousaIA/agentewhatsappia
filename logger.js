const winston = require('winston');
const path = require('path');
const fs = require('fs');

// Cria diretório de logs se não existir
const logDir = 'logs';
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir);
}

// Formato personalizado para logs
const logFormat = winston.format.combine(
    winston.format.timestamp({
        format: 'YYYY-MM-DD HH:mm:ss'
    }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json()
);

// Transportes para diferentes níveis de log
const transports = {
    error: new winston.transports.File({
        filename: path.join(logDir, 'error.log'),
        level: 'error',
        maxsize: 5242880, // 5MB
        maxFiles: 5,
        format: logFormat
    }),
    combined: new winston.transports.File({
        filename: path.join(logDir, 'combined.log'),
        maxsize: 5242880, // 5MB
        maxFiles: 5,
        format: logFormat
    }),
    console: new winston.transports.Console({
        format: winston.format.combine(
            winston.format.colorize(),
            winston.format.simple()
        )
    })
};

// Cria o logger principal
const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: logFormat,
    transports: [
        transports.error,
        transports.combined,
        transports.console
    ]
});

// Funções auxiliares para diferentes tipos de log
const log = {
    // Log de erro
    error: (message, meta = {}) => {
        logger.error(message, {
            ...meta,
            timestamp: new Date().toISOString()
        });
    },

    // Log de aviso
    warn: (message, meta = {}) => {
        logger.warn(message, {
            ...meta,
            timestamp: new Date().toISOString()
        });
    },

    // Log de informação
    info: (message, meta = {}) => {
        logger.info(message, {
            ...meta,
            timestamp: new Date().toISOString()
        });
    },

    // Log de debug
    debug: (message, meta = {}) => {
        logger.debug(message, {
            ...meta,
            timestamp: new Date().toISOString()
        });
    },

    // Log de conexão WhatsApp
    whatsapp: (message, meta = {}) => {
        logger.info(`[WhatsApp] ${message}`, {
            ...meta,
            service: 'whatsapp',
            timestamp: new Date().toISOString()
        });
    },

    // Log de mensagens
    message: (message, meta = {}) => {
        logger.info(`[Mensagem] ${message}`, {
            ...meta,
            service: 'message',
            timestamp: new Date().toISOString()
        });
    },

    // Log de mídia
    media: (message, meta = {}) => {
        logger.info(`[Mídia] ${message}`, {
            ...meta,
            service: 'media',
            timestamp: new Date().toISOString()
        });
    },

    // Log de Firebase
    firebase: (message, meta = {}) => {
        logger.info(`[Firebase] ${message}`, {
            ...meta,
            service: 'firebase',
            timestamp: new Date().toISOString()
        });
    },

    // Log de WebSocket
    websocket: (message, meta = {}) => {
        logger.info(`[WebSocket] ${message}`, {
            ...meta,
            service: 'websocket',
            timestamp: new Date().toISOString()
        });
    }
};

module.exports = log; 