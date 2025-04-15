const logger = require('../logger');

/**
 * Classe base para erros personalizados
 */
class WhatsAppError extends Error {
    constructor(message, code, details = {}) {
        super(message);
        this.name = this.constructor.name;
        this.code = code;
        this.details = details;
        Error.captureStackTrace(this, this.constructor);
    }
}

/**
 * Erro de validação de número
 */
class InvalidNumberError extends WhatsAppError {
    constructor(number, details = {}) {
        super('Número de telefone inválido', 'INVALID_NUMBER', {
            number,
            ...details
        });
    }
}

/**
 * Erro de conexão com WhatsApp
 */
class ConnectionError extends WhatsAppError {
    constructor(reason, details = {}) {
        super('Erro de conexão com WhatsApp', 'CONNECTION_ERROR', {
            reason,
            ...details
        });
    }
}

/**
 * Erro ao enviar mensagem
 */
class SendMessageError extends WhatsAppError {
    constructor(to, reason, details = {}) {
        super('Erro ao enviar mensagem', 'SEND_MESSAGE_ERROR', {
            to,
            reason,
            ...details
        });
    }
}

/**
 * Middleware para tratamento de erros
 */
function errorHandler(err, req, res, next) {
    if (err instanceof WhatsAppError) {
        logger.error(err.message, {
            code: err.code,
            details: err.details
        });

        return res.status(400).json({
            error: {
                message: err.message,
                code: err.code,
                details: err.details
            }
        });
    }

    // Erro não tratado
    logger.error('Erro interno do servidor', {
        error: err.message,
        stack: err.stack
    });

    return res.status(500).json({
        error: {
            message: 'Erro interno do servidor',
            code: 'INTERNAL_ERROR'
        }
    });
}

/**
 * Função para criar erros personalizados
 */
function createError(type, message, code, details = {}) {
    const errorClasses = {
        INVALID_NUMBER: InvalidNumberError,
        CONNECTION_ERROR: ConnectionError,
        SEND_MESSAGE_ERROR: SendMessageError
    };

    const ErrorClass = errorClasses[type] || WhatsAppError;
    return new ErrorClass(message, code, details);
}

module.exports = {
    WhatsAppError,
    InvalidNumberError,
    ConnectionError,
    SendMessageError,
    errorHandler,
    createError
}; 