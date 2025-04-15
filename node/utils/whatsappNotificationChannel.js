const logger = require('../logger');
const whatsappService = require('../services/whatsappService');

class WhatsAppNotificationChannel {
    constructor() {
        this.recipients = new Set();
    }

    async initialize() {
        try {
            // Carrega destinatários de notificações
            await this.loadRecipients();
            logger.info('Canal de notificação WhatsApp inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar canal de notificação WhatsApp', {
                error: error.message
            });
            throw error;
        }
    }

    async loadRecipients() {
        // TODO: Carregar destinatários de um arquivo de configuração ou banco de dados
        this.recipients.add('5511999999999'); // Número de exemplo
    }

    async send(notification) {
        try {
            const message = this.formatNotification(notification);
            
            for (const recipient of this.recipients) {
                await whatsappService.sendMessage({
                    to: recipient,
                    content: message
                });
            }
        } catch (error) {
            logger.error('Erro ao enviar notificação via WhatsApp', {
                error: error.message,
                notification
            });
            throw error;
        }
    }

    formatNotification(notification) {
        let message = '';

        switch (notification.type) {
            case 'alert':
                message = `🚨 *ALERTA*\n\n`;
                message += `*Métrica:* ${notification.metric}\n`;
                message += `*Mensagem:* ${notification.message}\n`;
                message += `*Valor:* ${notification.value}\n`;
                message += `*Data:* ${new Date(notification.timestamp).toLocaleString()}`;
                break;

            case 'error':
                message = `❌ *ERRO*\n\n`;
                message += `*Mensagem:* ${notification.error}\n`;
                if (notification.context) {
                    message += `*Contexto:* ${JSON.stringify(notification.context, null, 2)}\n`;
                }
                message += `*Data:* ${new Date(notification.timestamp).toLocaleString()}`;
                break;

            default:
                message = `*Notificação*\n\n`;
                message += JSON.stringify(notification, null, 2);
        }

        return message;
    }

    addRecipient(phoneNumber) {
        this.recipients.add(phoneNumber);
        logger.info('Destinatário adicionado ao canal WhatsApp', { phoneNumber });
    }

    removeRecipient(phoneNumber) {
        this.recipients.delete(phoneNumber);
        logger.info('Destinatário removido do canal WhatsApp', { phoneNumber });
    }
}

module.exports = new WhatsAppNotificationChannel(); 