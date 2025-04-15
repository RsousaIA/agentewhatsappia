const winston = require('winston');
const path = require('path');
const fs = require('fs');
const config = require('./config');

const { combine, timestamp, printf, colorize } = winston.format;

// Formato personalizado para logs
const logFormat = printf(({ level, message, timestamp, ...metadata }) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    if (Object.keys(metadata).length > 0) {
        msg += ` ${JSON.stringify(metadata)}`;
    }
    return msg;
});

// Configuração padrão do logger
const defaultConfig = {
    level: 'info',
    format: combine(
        timestamp(),
        logFormat
    ),
    transports: [
        new winston.transports.Console({
            format: combine(
                colorize(),
                logFormat
            )
        })
    ]
};

// Cria o logger
const logger = winston.createLogger(defaultConfig);

// Adiciona transporte de arquivo se configurado
if (process.env.LOG_FILE) {
    const logDir = path.dirname(process.env.LOG_FILE);
    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }
    
    logger.add(new winston.transports.File({
        filename: process.env.LOG_FILE,
        format: combine(
            timestamp(),
            logFormat
        )
    }));
}

module.exports = logger; 