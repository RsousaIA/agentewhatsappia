const { EventEmitter } = require('events');
const logger = require('../logger');

class QueueManager extends EventEmitter {
    constructor() {
        super();
        this.queues = new Map();
        this.processing = new Map();
        this.retryCounts = new Map();
        this.maxRetries = 3;
        this.retryDelay = 5000;
        this.maxQueueSize = 1000;
        this.processingTimeout = 30000;
        this.messageIds = new Set();
    }

    validateMessage(message) {
        if (!message || typeof message !== 'object') {
            throw new Error('Mensagem inválida: deve ser um objeto');
        }
        if (!message.id) {
            throw new Error('Mensagem inválida: ID é obrigatório');
        }
        if (this.messageIds.has(message.id)) {
            throw new Error('Mensagem duplicada: ID já existe');
        }
        return true;
    }

    /**
     * Adiciona uma mensagem à fila
     * @param {string} queueName - Nome da fila
     * @param {Object} message - Objeto da mensagem
     * @param {number} [priority=0] - Prioridade da mensagem (0 = normal, 1 = alta)
     */
    async enqueue(queueName, message, priority = 0) {
        this.validateMessage(message);

        if (!this.queues.has(queueName)) {
            this.queues.set(queueName, []);
            this.processing.set(queueName, false);
            this.retryCounts.set(queueName, new Map());
        }

        const queue = this.queues.get(queueName);
        
        if (queue.length >= this.maxQueueSize) {
            throw new Error(`Fila ${queueName} está cheia. Limite: ${this.maxQueueSize} mensagens`);
        }

        const queueItem = {
            message,
            priority,
            timestamp: Date.now(),
            retryCount: 0
        };

        const insertIndex = queue.findIndex(item => item.priority < priority);
        if (insertIndex === -1) {
            queue.push(queueItem);
        } else {
            queue.splice(insertIndex, 0, queueItem);
        }

        this.messageIds.add(message.id);

        logger.info(`Mensagem adicionada à fila ${queueName}`, {
            queueName,
            messageId: message.id,
            priority,
            queueSize: queue.length
        });

        if (!this.processing.get(queueName)) {
            this.processQueue(queueName);
        }
    }

    /**
     * Processa a fila de mensagens
     * @param {string} queueName - Nome da fila
     */
    async processQueue(queueName) {
        if (!this.queues.has(queueName) || this.processing.get(queueName)) {
            return;
        }

        this.processing.set(queueName, true);
        const queue = this.queues.get(queueName);

        while (queue.length > 0) {
            const item = queue.shift();
            const messageId = item.message.id;

            try {
                logger.info(`Processando mensagem da fila ${queueName}`, {
                    queueName,
                    messageId,
                    retryCount: item.retryCount
                });

                this.emit('process', {
                    queueName,
                    message: item.message,
                    retryCount: item.retryCount
                });

                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Timeout no processamento da mensagem'));
                    }, this.processingTimeout);

                    const handler = (result) => {
                        clearTimeout(timeout);
                        this.removeListener('processed', handler);
                        if (result.error) {
                            reject(result.error);
                        } else {
                            resolve(result);
                        }
                    };

                    this.once('processed', handler);
                });

                this.retryCounts.get(queueName).delete(messageId);
                this.messageIds.delete(messageId);

            } catch (error) {
                logger.error(`Erro ao processar mensagem da fila ${queueName}`, {
                    queueName,
                    messageId,
                    error: error.message,
                    retryCount: item.retryCount
                });

                if (item.retryCount < this.maxRetries) {
                    item.retryCount++;
                    const retryDelay = this.retryDelay * item.retryCount;
                    
                    logger.info(`Agendando retentativa para mensagem`, {
                        queueName,
                        messageId,
                        retryCount: item.retryCount,
                        delay: retryDelay
                    });

                    setTimeout(() => {
                        this.enqueue(queueName, item.message, 1);
                    }, retryDelay);
                } else {
                    logger.error(`Máximo de retentativas atingido para mensagem`, {
                        queueName,
                        messageId,
                        maxRetries: this.maxRetries
                    });

                    this.messageIds.delete(messageId);

                    this.emit('failed', {
                        queueName,
                        message: item.message,
                        error: error.message
                    });
                }
            }
        }

        this.processing.set(queueName, false);
    }

    /**
     * Notifica que uma mensagem foi processada com sucesso
     * @param {string} queueName - Nome da fila
     * @param {string} messageId - ID da mensagem
     */
    notifyProcessed(queueName, messageId) {
        this.emit('processed', {
            queueName,
            messageId,
            success: true
        });
    }

    /**
     * Obtém estatísticas da fila
     * @param {string} queueName - Nome da fila
     * @returns {Object} Estatísticas da fila
     */
    getQueueStats(queueName) {
        if (!this.queues.has(queueName)) {
            return null;
        }

        const queue = this.queues.get(queueName);
        const retryCounts = this.retryCounts.get(queueName);

        return {
            queueName,
            size: queue.length,
            processing: this.processing.get(queueName),
            messagesInRetry: Array.from(retryCounts.values()).filter(count => count > 0).length,
            nextRetryTimestamp: queue.length > 0 ? queue[0].timestamp + this.retryDelay : null,
            maxSize: this.maxQueueSize,
            uniqueMessages: this.messageIds.size
        };
    }

    /**
     * Limpa a fila
     * @param {string} queueName - Nome da fila
     */
    clearQueue(queueName) {
        if (this.queues.has(queueName)) {
            const queue = this.queues.get(queueName);
            queue.forEach(item => {
                this.messageIds.delete(item.message.id);
            });
            
            this.queues.set(queueName, []);
            this.retryCounts.set(queueName, new Map());
            logger.info(`Fila ${queueName} limpa`);
        }
    }
}

module.exports = new QueueManager(); 