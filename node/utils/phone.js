const logger = require('../logger');

/**
 * Valida e formata um número de telefone para o formato do WhatsApp
 * @param {string} phone - Número de telefone a ser validado
 * @returns {string|null} - Número formatado ou null se inválido
 */
function formatPhoneNumber(phone) {
    try {
        // Remove todos os caracteres não numéricos
        let cleaned = phone.replace(/\D/g, '');
        
        // Verifica se o número tem o tamanho correto
        if (cleaned.length < 10 || cleaned.length > 13) {
            logger.warn('Número de telefone com tamanho inválido', { phone, cleaned });
            return null;
        }

        // Adiciona o código do país se necessário
        if (!cleaned.startsWith('55')) {
            cleaned = '55' + cleaned;
        }

        // Formata para o padrão do WhatsApp (código do país + DDD + número)
        const formatted = cleaned + '@c.us';
        logger.debug('Número formatado com sucesso', { original: phone, formatted });
        
        return formatted;
    } catch (error) {
        logger.error('Erro ao formatar número de telefone', { 
            phone, 
            error: error.message 
        });
        return null;
    }
}

/**
 * Valida se um número de telefone está no formato correto do WhatsApp
 * @param {string} phone - Número de telefone a ser validado
 * @returns {boolean} - True se válido, False caso contrário
 */
function isValidWhatsAppNumber(phone) {
    try {
        // Verifica se o número termina com @c.us
        if (!phone.endsWith('@c.us')) {
            return false;
        }

        // Remove o sufixo @c.us e valida apenas os números
        const numbers = phone.replace('@c.us', '');
        
        // Verifica se contém apenas números
        if (!/^\d+$/.test(numbers)) {
            return false;
        }

        // Verifica o tamanho do número (código do país + DDD + número)
        if (numbers.length < 12 || numbers.length > 13) {
            return false;
        }

        return true;
    } catch (error) {
        logger.error('Erro ao validar número do WhatsApp', { 
            phone, 
            error: error.message 
        });
        return false;
    }
}

module.exports = {
    formatPhoneNumber,
    isValidWhatsAppNumber
}; 