const logger = require('../logger');
const metricsManager = require('./metricsManager');

class NotificationManager {
    constructor() {
        this.notificationChannels = new Map();
        this.alertThresholds = new Map();
        this.initialize();
    }

    async initialize() {
        try {
            // Inicializa métricas
            await this.initializeMetrics();
            
            // Configura alertas padrão
            this.setupDefaultAlerts();
            
            logger.info('Gerenciador de notificações inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar gerenciador de notificações', {
                error: error.message
            });
            throw error;
        }
    }

    async initializeMetrics() {
        // Métricas de notificações
        await metricsManager.addMetric('notifications_sent', 'counter', 'Total de notificações enviadas');
        await metricsManager.addMetric('notifications_failed', 'counter', 'Total de notificações com falha');
        await metricsManager.addMetric('alerts_triggered', 'counter', 'Total de alertas disparados');
    }

    setupDefaultAlerts() {
        // Alertas para o Scheduler
        this.setAlertThreshold('scheduler_messages_failed', {
            threshold: 5,
            window: 3600000, // 1 hora
            message: 'Alto número de falhas no envio de mensagens'
        });

        this.setAlertThreshold('scheduler_processing_time', {
            threshold: 5000, // 5 segundos
            window: 300000, // 5 minutos
            message: 'Tempo de processamento elevado'
        });

        this.setAlertThreshold('scheduler_cache_misses', {
            threshold: 100,
            window: 3600000, // 1 hora
            message: 'Alto número de misses no cache'
        });
    }

    registerChannel(name, channel) {
        this.notificationChannels.set(name, channel);
        logger.info('Canal de notificação registrado', { channel: name });
    }

    setAlertThreshold(metricName, config) {
        this.alertThresholds.set(metricName, config);
        logger.info('Limite de alerta configurado', { metric: metricName, config });
    }

    async checkAlerts() {
        for (const [metricName, config] of this.alertThresholds.entries()) {
            const metric = await metricsManager.getMetric(metricName);
            
            if (metric && this.isThresholdExceeded(metric, config)) {
                await this.sendAlert(metricName, config.message, metric.value);
            }
        }
    }

    isThresholdExceeded(metric, config) {
        if (metric.type === 'counter') {
            return metric.value > config.threshold;
        } else if (metric.type === 'histogram') {
            return metric.value > config.threshold;
        }
        return false;
    }

    async sendAlert(metricName, message, value) {
        try {
            const alert = {
                type: 'alert',
                metric: metricName,
                message,
                value,
                timestamp: new Date().toISOString()
            };

            await this.sendNotification(alert);
            await metricsManager.increment('alerts_triggered');
            
            logger.warn('Alerta disparado', alert);
        } catch (error) {
            logger.error('Erro ao enviar alerta', {
                error: error.message,
                metric: metricName
            });
        }
    }

    async sendNotification(notification) {
        try {
            for (const channel of this.notificationChannels.values()) {
                await channel.send(notification);
            }
            
            await metricsManager.increment('notifications_sent');
            logger.info('Notificação enviada', { notification });
        } catch (error) {
            await metricsManager.increment('notifications_failed');
            logger.error('Erro ao enviar notificação', {
                error: error.message,
                notification
            });
            throw error;
        }
    }

    async notifyError(error, context = {}) {
        const notification = {
            type: 'error',
            error: error.message,
            context,
            timestamp: new Date().toISOString()
        };

        await this.sendNotification(notification);
    }
}

module.exports = new NotificationManager(); 