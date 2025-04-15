const logger = require('../logger');

class GroupManager {
    constructor(client) {
        this.client = client;
        this.groups = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutos
    }

    /**
     * Lista todos os grupos
     * @returns {Promise<Array>} Lista de grupos
     */
    async listGroups() {
        try {
            const chats = await this.client.getChats();
            const groups = chats.filter(chat => chat.isGroup);
            
            // Atualiza cache
            groups.forEach(group => {
                this.groups.set(group.id._serialized, {
                    ...group,
                    lastUpdated: Date.now()
                });
            });

            return groups.map(group => ({
                id: group.id._serialized,
                name: group.name,
                participants: group.participants.length,
                isAdmin: group.isGroupAdmin,
                createdAt: group.createdAt
            }));
        } catch (error) {
            logger.error('Erro ao listar grupos', { error: error.message });
            throw error;
        }
    }

    /**
     * Obtém informações de um grupo específico
     * @param {string} groupId - ID do grupo
     * @returns {Promise<Object>} Informações do grupo
     */
    async getGroupInfo(groupId) {
        try {
            // Verifica cache
            const cachedGroup = this.groups.get(groupId);
            if (cachedGroup && Date.now() - cachedGroup.lastUpdated < this.cacheTimeout) {
                return this._formatGroupInfo(cachedGroup);
            }

            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            // Atualiza cache
            this.groups.set(groupId, {
                ...group,
                lastUpdated: Date.now()
            });

            return this._formatGroupInfo(group);
        } catch (error) {
            logger.error('Erro ao obter informações do grupo', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Envia mensagem para um grupo
     * @param {string} groupId - ID do grupo
     * @param {string} content - Conteúdo da mensagem
     * @param {Object} [media] - Objeto de mídia (opcional)
     * @returns {Promise<Object>} Resultado do envio
     */
    async sendMessage(groupId, content, media = null) {
        try {
            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            let result;
            if (media) {
                switch (media.type) {
                    case 'image':
                        result = await group.sendImage(media.buffer, media.filename, content);
                        break;
                    case 'document':
                        result = await group.sendDocument(media.buffer, media.filename, content);
                        break;
                    case 'audio':
                        result = await group.sendAudio(media.buffer, media.filename);
                        break;
                    case 'video':
                        result = await group.sendVideo(media.buffer, media.filename, content);
                        break;
                    case 'sticker':
                        result = await group.sendSticker(media.buffer);
                        break;
                    default:
                        throw new Error('Tipo de mídia não suportado');
                }
            } else {
                result = await group.sendMessage(content);
            }

            logger.info('Mensagem enviada para grupo', {
                groupId,
                contentLength: content?.length || 0,
                hasMedia: !!media
            });

            return {
                success: true,
                messageId: result.id._serialized,
                timestamp: result.timestamp
            };
        } catch (error) {
            logger.error('Erro ao enviar mensagem para grupo', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Adiciona participantes ao grupo
     * @param {string} groupId - ID do grupo
     * @param {Array<string>} numbers - Lista de números de telefone
     * @returns {Promise<Object>} Resultado da operação
     */
    async addParticipants(groupId, numbers) {
        try {
            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            const result = await group.addParticipants(numbers);
            
            logger.info('Participantes adicionados ao grupo', {
                groupId,
                participants: numbers.length
            });

            return {
                success: true,
                added: result.added,
                failed: result.failed
            };
        } catch (error) {
            logger.error('Erro ao adicionar participantes ao grupo', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Remove participantes do grupo
     * @param {string} groupId - ID do grupo
     * @param {Array<string>} numbers - Lista de números de telefone
     * @returns {Promise<Object>} Resultado da operação
     */
    async removeParticipants(groupId, numbers) {
        try {
            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            const result = await group.removeParticipants(numbers);
            
            logger.info('Participantes removidos do grupo', {
                groupId,
                participants: numbers.length
            });

            return {
                success: true,
                removed: result.removed,
                failed: result.failed
            };
        } catch (error) {
            logger.error('Erro ao remover participantes do grupo', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Promove participantes a administradores
     * @param {string} groupId - ID do grupo
     * @param {Array<string>} numbers - Lista de números de telefone
     * @returns {Promise<Object>} Resultado da operação
     */
    async promoteParticipants(groupId, numbers) {
        try {
            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            const result = await group.promoteParticipants(numbers);
            
            logger.info('Participantes promovidos a administradores', {
                groupId,
                participants: numbers.length
            });

            return {
                success: true,
                promoted: result.promoted,
                failed: result.failed
            };
        } catch (error) {
            logger.error('Erro ao promover participantes', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Rebaixa administradores a participantes
     * @param {string} groupId - ID do grupo
     * @param {Array<string>} numbers - Lista de números de telefone
     * @returns {Promise<Object>} Resultado da operação
     */
    async demoteParticipants(groupId, numbers) {
        try {
            const group = await this.client.getChatById(groupId);
            if (!group.isGroup) {
                throw new Error('Chat não é um grupo');
            }

            const result = await group.demoteParticipants(numbers);
            
            logger.info('Administradores rebaixados a participantes', {
                groupId,
                participants: numbers.length
            });

            return {
                success: true,
                demoted: result.demoted,
                failed: result.failed
            };
        } catch (error) {
            logger.error('Erro ao rebaixar administradores', {
                groupId,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Formata informações do grupo para resposta
     * @private
     */
    _formatGroupInfo(group) {
        return {
            id: group.id._serialized,
            name: group.name,
            description: group.description,
            participants: group.participants.map(p => ({
                id: p.id._serialized,
                name: p.name || p.number,
                isAdmin: p.isAdmin,
                isSuperAdmin: p.isSuperAdmin
            })),
            isAdmin: group.isGroupAdmin,
            createdAt: group.createdAt,
            lastUpdated: Date.now()
        };
    }
}

module.exports = GroupManager; 