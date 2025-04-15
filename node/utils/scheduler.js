const logger = require('../logger');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const schedule = require('node-schedule');
const backupManager = require('./backupManager');
const metricsManager = require('./metricsManager');
const notificationManager = require('./notificationManager');

class Scheduler {
    constructor() {
        this.jobs = new Map();
        this.scheduledMessages = new Map();
        this.schedulerPath = path.join(__dirname, '../data/scheduled_messages');
        this.backupPath = path.join(__dirname, '../data/scheduled_messages/backup');
        this.renderedCache = new Map();
        this.maxMessages = 10000;
        this.processingTimeout = 30000;
        this.retryCounts = new Map();
        this.maxRetries = 3;
        this.retryDelay = 5000;
        this.messageCache = new Map();
        this.cacheTTL = 3600000; // 1 hora
        this.initialize();
    }

    /**
     * Inicializa o gerenciador de agendamentos
     */
    async initialize() {
        try {
            // Cria diretórios necessários
            await fs.mkdir(this.schedulerPath, { recursive: true });
            await fs.mkdir(this.backupPath, { recursive: true });
            
            // Carrega mensagens agendadas
            await this.loadScheduledMessages();
            
            // Inicializa métricas
            await this.initializeMetrics();
            
            // Agenda limpeza periódica
            schedule.scheduleJob('0 0 * * *', () => this.cleanOldMessages());
            
            // Agenda backup periódico
            schedule.scheduleJob('0 2 * * *', () => this.createBackup());
            
            // Agenda limpeza do cache
            schedule.scheduleJob('0 * * * *', () => this.cleanCache());
            
            // Registra canal de notificação
            notificationManager.registerChannel('whatsapp', require('./whatsappNotificationChannel'));
            
            // Agenda verificação de alertas
            schedule.scheduleJob('*/5 * * * *', () => this.checkAlerts());
            
            logger.info('Gerenciador de agendamentos inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar gerenciador de agendamentos', {
                error: error.message
            });
            throw error;
        }
    }

    async initializeMetrics() {
        // Métricas de performance
        await metricsManager.addMetric('scheduler_messages_total', 'counter', 'Total de mensagens agendadas');
        await metricsManager.addMetric('scheduler_messages_processed', 'counter', 'Total de mensagens processadas');
        await metricsManager.addMetric('scheduler_messages_failed', 'counter', 'Total de mensagens com falha');
        await metricsManager.addMetric('scheduler_cache_hits', 'counter', 'Total de hits no cache');
        await metricsManager.addMetric('scheduler_cache_misses', 'counter', 'Total de misses no cache');
        await metricsManager.addMetric('scheduler_processing_time', 'histogram', 'Tempo de processamento das mensagens');
    }

    /**
     * Carrega mensagens agendadas do diretório
     */
    async loadScheduledMessages() {
        try {
            const files = await fs.readdir(this.schedulerPath);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    try {
                        const content = await fs.readFile(
                            path.join(this.schedulerPath, file),
                            'utf8'
                        );
                        const message = JSON.parse(content);
                        
                        this.scheduledMessages.set(message.id, message);
                        
                        // Agenda a mensagem se ainda não foi enviada
                        if (message.status === 'scheduled') {
                            this.scheduleMessage(message);
                        }
                    } catch (error) {
                        logger.error(`Erro ao carregar mensagem ${file}`, {
                            error: error.message
                        });
                        // Tenta restaurar do backup
                        await this.restoreFromBackup(file);
                    }
                }
            }
            
            logger.info('Mensagens agendadas carregadas com sucesso', {
                count: this.scheduledMessages.size
            });
        } catch (error) {
            logger.error('Erro ao carregar mensagens agendadas', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Agenda uma nova mensagem
     * @param {Object} message - Dados da mensagem
     * @returns {Object} Mensagem agendada
     */
    async scheduleMessage(message) {
        try {
            // Valida a mensagem
            this.validateMessage(message);

            // Verifica limite de mensagens
            if (this.scheduledMessages.size >= this.maxMessages) {
                throw new Error('Limite máximo de mensagens agendadas atingido');
            }

            // Gera ID único
            const id = uuidv4();
            const scheduledMessage = {
                id,
                ...message,
                status: 'scheduled',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                retryCount: 0
            };

            // Cria backup antes de salvar
            await this.createBackup();

            // Salva no sistema de arquivos
            await fs.writeFile(
                path.join(this.schedulerPath, `${id}.json`),
                JSON.stringify(scheduledMessage, null, 2)
            );

            // Adiciona ao cache
            this.messageCache.set(id, {
                message: scheduledMessage,
                timestamp: Date.now()
            });

            // Adiciona ao cache
            this.scheduledMessages.set(id, scheduledMessage);

            // Incrementa métrica de mensagens agendadas
            await metricsManager.increment('scheduler_messages_total');

            // Agenda o envio
            const job = schedule.scheduleJob(
                new Date(message.scheduledTime),
                async () => {
                    try {
                        await this.processMessage(scheduledMessage);
                    } catch (error) {
                        logger.error('Erro ao processar mensagem agendada', {
                            id,
                            error: error.message
                        });
                        await this.handleProcessingError(id, error);
                    }
                }
            );

            this.jobs.set(id, job);

            logger.info('Mensagem agendada com sucesso', { id });

            return scheduledMessage;
        } catch (error) {
            logger.error('Erro ao agendar mensagem', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Processa uma mensagem agendada
     * @private
     */
    async processMessage(message) {
        const startTime = Date.now();
        const timeout = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Timeout ao processar mensagem')), this.processingTimeout);
        });

        try {
            await Promise.race([
                this.sendMessage(message),
                timeout
            ]);

            await this.updateMessageStatus(message.id, 'sent');
            this.retryCounts.delete(message.id);

            // Atualiza métricas
            await metricsManager.increment('scheduler_messages_processed');
            await metricsManager.observe('scheduler_processing_time', Date.now() - startTime);
        } catch (error) {
            await metricsManager.increment('scheduler_messages_failed');
            
            // Notifica erro
            await notificationManager.notifyError(error, {
                messageId: message.id,
                recipient: message.recipient,
                scheduledTime: message.scheduledTime
            });
            
            throw error;
        }
    }

    /**
     * Trata erros no processamento de mensagens
     * @private
     */
    async handleProcessingError(id, error) {
        const retryCount = (this.retryCounts.get(id) || 0) + 1;
        this.retryCounts.set(id, retryCount);

        if (retryCount <= this.maxRetries) {
            logger.info(`Tentando reenviar mensagem (tentativa ${retryCount}/${this.maxRetries})`, { id });
            
            setTimeout(async () => {
                const message = this.scheduledMessages.get(id);
                if (message) {
                    await this.processMessage(message);
                }
            }, this.retryDelay);
        } else {
            logger.error('Número máximo de tentativas excedido', { id });
            await this.updateMessageStatus(id, 'failed');
            this.retryCounts.delete(id);
        }
    }

    /**
     * Atualiza o status de uma mensagem
     * @param {string} id - ID da mensagem
     * @param {string} status - Novo status
     */
    async updateMessageStatus(id, status) {
        try {
            const message = this.scheduledMessages.get(id);
            if (!message) {
                throw new Error('Mensagem não encontrada');
            }

            // Atualiza o status
            message.status = status;
            message.updatedAt = new Date().toISOString();

            // Salva no sistema de arquivos
            await fs.writeFile(
                path.join(this.schedulerPath, `${id}.json`),
                JSON.stringify(message, null, 2)
            );

            // Atualiza o cache
            this.scheduledMessages.set(id, message);

            logger.info('Status da mensagem atualizado', { id, status });
        } catch (error) {
            logger.error('Erro ao atualizar status da mensagem', {
                id,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Cancela uma mensagem agendada
     * @param {string} id - ID da mensagem
     */
    async cancelMessage(id) {
        try {
            const message = this.scheduledMessages.get(id);
            if (!message) {
                throw new Error('Mensagem não encontrada');
            }

            // Cancela o job
            const job = this.jobs.get(id);
            if (job) {
                job.cancel();
                this.jobs.delete(id);
            }

            // Atualiza o status
            await this.updateMessageStatus(id, 'cancelled');

            logger.info('Mensagem cancelada com sucesso', { id });
        } catch (error) {
            logger.error('Erro ao cancelar mensagem', {
                id,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Lista mensagens agendadas
     * @param {Object} filters - Filtros de busca
     * @returns {Array} Lista de mensagens
     */
    listMessages(filters = {}) {
        let messages = Array.from(this.scheduledMessages.values());

        if (filters.status) {
            messages = messages.filter(m => m.status === filters.status);
        }

        if (filters.startDate) {
            const startDate = new Date(filters.startDate);
            messages = messages.filter(m => new Date(m.scheduledTime) >= startDate);
        }

        if (filters.endDate) {
            const endDate = new Date(filters.endDate);
            messages = messages.filter(m => new Date(m.scheduledTime) <= endDate);
        }

        return messages;
    }

    /**
     * Envia uma mensagem agendada
     * @private
     */
    async sendMessage(message) {
        // TODO: Implementar envio da mensagem
        logger.info('Enviando mensagem agendada', { id: message.id });
    }

    /**
     * Valida uma mensagem
     * @private
     */
    validateMessage(message) {
        if (!message.to) {
            throw new Error('Destinatário é obrigatório');
        }

        if (!message.content) {
            throw new Error('Conteúdo da mensagem é obrigatório');
        }

        if (!message.scheduledTime) {
            throw new Error('Data de agendamento é obrigatória');
        }

        const scheduledTime = new Date(message.scheduledTime);
        if (isNaN(scheduledTime.getTime())) {
            throw new Error('Data de agendamento inválida');
        }

        if (scheduledTime < new Date()) {
            throw new Error('Data de agendamento deve ser futura');
        }
    }

    /**
     * Limpa mensagens antigas
     * @private
     */
    async cleanOldMessages() {
        try {
            const now = new Date();
            const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));

            for (const [id, message] of this.scheduledMessages) {
                if (new Date(message.createdAt) < thirtyDaysAgo) {
                    await this.deleteMessage(id);
                }
            }

            logger.info('Limpeza de mensagens antigas concluída');
        } catch (error) {
            logger.error('Erro ao limpar mensagens antigas', {
                error: error.message
            });
        }
    }

    /**
     * Cria backup das mensagens
     * @private
     */
    async createBackup() {
        try {
            const backupFile = path.join(
                this.backupPath,
                `backup_${Date.now()}.json`
            );

            const messages = Array.from(this.scheduledMessages.values());
            await fs.writeFile(
                backupFile,
                JSON.stringify(messages, null, 2)
            );

            logger.info('Backup de mensagens criado com sucesso');
        } catch (error) {
            logger.error('Erro ao criar backup de mensagens', {
                error: error.message
            });
        }
    }

    /**
     * Restaura mensagem do backup
     * @private
     */
    async restoreFromBackup(filename) {
        try {
            const backups = await fs.readdir(this.backupPath);
            const templateBackups = backups
                .filter(f => f.startsWith(filename.replace('.json', '')))
                .sort()
                .reverse();

            if (templateBackups.length > 0) {
                const backupContent = await fs.readFile(
                    path.join(this.backupPath, templateBackups[0]),
                    'utf8'
                );
                const message = JSON.parse(backupContent);
                await fs.writeFile(
                    path.join(this.schedulerPath, filename),
                    backupContent
                );
                this.scheduledMessages.set(message.id, message);
                logger.info(`Mensagem ${filename} restaurada do backup`);
            }
        } catch (error) {
            logger.error(`Erro ao restaurar mensagem ${filename} do backup`, {
                error: error.message
            });
        }
    }

    async getMessage(id) {
        // Verifica cache primeiro
        const cached = this.messageCache.get(id);
        if (cached && (Date.now() - cached.timestamp) < this.cacheTTL) {
            await metricsManager.increment('scheduler_cache_hits');
            return cached.message;
        }

        await metricsManager.increment('scheduler_cache_misses');
        
        // Se não estiver no cache, carrega do sistema de arquivos
        const message = this.scheduledMessages.get(id);
        if (message) {
            this.messageCache.set(id, {
                message,
                timestamp: Date.now()
            });
        }
        return message;
    }

    async cleanCache() {
        const now = Date.now();
        for (const [id, cached] of this.messageCache.entries()) {
            if (now - cached.timestamp > this.cacheTTL) {
                this.messageCache.delete(id);
            }
        }
    }

    async checkAlerts() {
        try {
            await notificationManager.checkAlerts();
        } catch (error) {
            logger.error('Erro ao verificar alertas', {
                error: error.message
            });
        }
    }
}

module.exports = new Scheduler(); 