const logger = require('../logger');
const { createError } = require('./errorHandler');

class ReconnectionManager {
    constructor(client, options = {}) {
        this.client = client;
        this.maxAttempts = options.maxAttempts || 5;
        this.initialDelay = options.initialDelay || 1000; // 1 segundo
        this.maxDelay = options.maxDelay || 30000; // 30 segundos
        this.attempts = 0;
        this.isReconnecting = false;
        this.reconnectTimeout = null;
    }

    /**
     * Inicia o processo de reconexão
     */
    async reconnect() {
        if (this.isReconnecting) {
            logger.warn('Tentativa de reconexão já em andamento');
            return;
        }

        this.isReconnecting = true;
        this.attempts = 0;

        try {
            await this._attemptReconnect();
        } catch (error) {
            logger.error('Falha na reconexão', { error: error.message });
            throw createError('CONNECTION_ERROR', 'Falha na reconexão', {
                reason: error.message
            });
        }
    }

    /**
     * Tenta reconectar com backoff exponencial
     */
    async _attemptReconnect() {
        if (this.attempts >= this.maxAttempts) {
            this.isReconnecting = false;
            throw new Error('Número máximo de tentativas de reconexão atingido');
        }

        const delay = Math.min(
            this.initialDelay * Math.pow(2, this.attempts),
            this.maxDelay
        );

        logger.info('Tentando reconectar', {
            attempt: this.attempts + 1,
            maxAttempts: this.maxAttempts,
            delay
        });

        try {
            await this.client.initialize();
            this.isReconnecting = false;
            this.attempts = 0;
            logger.info('Reconexão bem-sucedida');
        } catch (error) {
            this.attempts++;
            logger.warn('Falha na tentativa de reconexão', {
                attempt: this.attempts,
                error: error.message
            });

            // Agenda próxima tentativa
            this.reconnectTimeout = setTimeout(() => {
                this._attemptReconnect();
            }, delay);
        }
    }

    /**
     * Cancela a reconexão em andamento
     */
    cancelReconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        this.isReconnecting = false;
        this.attempts = 0;
        logger.info('Reconexão cancelada');
    }

    /**
     * Verifica se está tentando reconectar
     */
    isReconnecting() {
        return this.isReconnecting;
    }

    /**
     * Retorna o número de tentativas
     */
    getAttempts() {
        return this.attempts;
    }
}

module.exports = ReconnectionManager; 