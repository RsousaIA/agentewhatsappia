const fs = require('fs');
const path = require('path');
const logger = require('../logger');
const { createError } = require('./errorHandler');

/**
 * Tipos de mídia suportados
 */
const MEDIA_TYPES = {
    IMAGE: 'image',
    DOCUMENT: 'document',
    AUDIO: 'audio',
    VIDEO: 'video',
    STICKER: 'sticker'
};

/**
 * Extensões permitidas por tipo de mídia
 */
const ALLOWED_EXTENSIONS = {
    [MEDIA_TYPES.IMAGE]: ['.jpg', '.jpeg', '.png', '.gif'],
    [MEDIA_TYPES.DOCUMENT]: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'],
    [MEDIA_TYPES.AUDIO]: ['.mp3', '.ogg', '.wav'],
    [MEDIA_TYPES.VIDEO]: ['.mp4', '.avi', '.mov'],
    [MEDIA_TYPES.STICKER]: ['.webp']
};

/**
 * Valida e processa um arquivo de mídia
 * @param {Object} file - Arquivo a ser processado
 * @param {string} mediaType - Tipo de mídia
 * @returns {Promise<Object>} - Informações do arquivo processado
 */
async function processMedia(file, mediaType) {
    try {
        // Verifica se o tipo de mídia é suportado
        if (!MEDIA_TYPES[mediaType.toUpperCase()]) {
            throw createError('INVALID_MEDIA_TYPE', 'Tipo de mídia não suportado', {
                type: mediaType,
                supported: Object.values(MEDIA_TYPES)
            });
        }

        // Verifica se o arquivo existe
        if (!fs.existsSync(file.path)) {
            throw createError('FILE_NOT_FOUND', 'Arquivo não encontrado', {
                path: file.path
            });
        }

        // Verifica a extensão do arquivo
        const ext = path.extname(file.originalname).toLowerCase();
        if (!ALLOWED_EXTENSIONS[mediaType].includes(ext)) {
            throw createError('INVALID_FILE_EXTENSION', 'Extensão de arquivo não permitida', {
                extension: ext,
                allowed: ALLOWED_EXTENSIONS[mediaType]
            });
        }

        // Verifica o tamanho do arquivo (máximo 16MB)
        const maxSize = 16 * 1024 * 1024; // 16MB
        const stats = fs.statSync(file.path);
        if (stats.size > maxSize) {
            throw createError('FILE_TOO_LARGE', 'Arquivo muito grande', {
                size: stats.size,
                maxSize
            });
        }

        // Lê o arquivo como buffer
        const buffer = fs.readFileSync(file.path);

        // Retorna as informações do arquivo
        return {
            buffer,
            mimetype: file.mimetype,
            filename: file.originalname,
            size: stats.size
        };
    } catch (error) {
        logger.error('Erro ao processar mídia', {
            error: error.message,
            details: error.details
        });
        throw error;
    } finally {
        // Remove o arquivo temporário
        if (file.path && fs.existsSync(file.path)) {
            fs.unlinkSync(file.path);
        }
    }
}

/**
 * Gera um nome único para o arquivo
 * @param {string} originalName - Nome original do arquivo
 * @returns {string} - Nome único para o arquivo
 */
function generateUniqueFilename(originalName) {
    const ext = path.extname(originalName);
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `${timestamp}-${random}${ext}`;
}

module.exports = {
    MEDIA_TYPES,
    processMedia,
    generateUniqueFilename
}; 