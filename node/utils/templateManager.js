const logger = require('../logger');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const crypto = require('crypto');

class TemplateManager {
    constructor() {
        this.templates = new Map();
        this.categories = new Set();
        this.templatePath = path.join(__dirname, '../templates');
        this.backupPath = path.join(__dirname, '../templates/backup');
        this.renderedCache = new Map();
        this.maxTemplateSize = 1024 * 1024; // 1MB
        this.cacheTTL = 5 * 60 * 1000; // 5 minutos
        this.initialize();
    }

    /**
     * Inicializa o gerenciador de templates
     */
    async initialize() {
        try {
            // Cria diretórios necessários
            await fs.mkdir(this.templatePath, { recursive: true });
            await fs.mkdir(this.backupPath, { recursive: true });
            
            // Carrega templates existentes
            await this.loadTemplates();
            
            // Limpa cache antigo periodicamente
            setInterval(() => this.clearExpiredCache(), this.cacheTTL);
            
            logger.info('Gerenciador de templates inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar gerenciador de templates', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Carrega templates do diretório
     */
    async loadTemplates() {
        try {
            const files = await fs.readdir(this.templatePath);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    try {
                        const content = await fs.readFile(
                            path.join(this.templatePath, file),
                            'utf8'
                        );
                        
                        // Valida tamanho do arquivo
                        if (content.length > this.maxTemplateSize) {
                            logger.warn(`Template ${file} excede o tamanho máximo permitido`);
                            continue;
                        }
                        
                        const template = JSON.parse(content);
                        
                        // Valida estrutura do template
                        if (!this.isValidTemplateStructure(template)) {
                            logger.warn(`Template ${file} possui estrutura inválida`);
                            continue;
                        }
                        
                        this.templates.set(template.id, template);
                        if (template.category) {
                            this.categories.add(template.category);
                        }
                    } catch (error) {
                        logger.error(`Erro ao carregar template ${file}`, {
                            error: error.message
                        });
                        // Tenta restaurar do backup
                        await this.restoreFromBackup(file);
                    }
                }
            }
            
            logger.info('Templates carregados com sucesso', {
                count: this.templates.size,
                categories: Array.from(this.categories)
            });
        } catch (error) {
            logger.error('Erro ao carregar templates', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Cria um novo template
     * @param {Object} template - Dados do template
     * @returns {Object} Template criado
     */
    async createTemplate(template) {
        try {
            // Valida o template
            this.validateTemplate(template);

            // Verifica duplicidade
            if (this.isDuplicateTemplate(template)) {
                throw new Error('Template com conteúdo similar já existe');
            }

            // Gera ID único
            const id = uuidv4();
            const newTemplate = {
                id,
                ...template,
                version: 1,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };

            // Cria backup antes de salvar
            await this.createBackup(newTemplate);

            // Salva no sistema de arquivos
            await fs.writeFile(
                path.join(this.templatePath, `${id}.json`),
                JSON.stringify(newTemplate, null, 2)
            );

            // Adiciona ao cache
            this.templates.set(id, newTemplate);
            if (newTemplate.category) {
                this.categories.add(newTemplate.category);
            }

            logger.info('Template criado com sucesso', { id });

            return newTemplate;
        } catch (error) {
            logger.error('Erro ao criar template', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Atualiza um template existente
     * @param {string} id - ID do template
     * @param {Object} updates - Atualizações do template
     * @returns {Object} Template atualizado
     */
    async updateTemplate(id, updates) {
        try {
            const template = this.templates.get(id);
            if (!template) {
                throw new Error('Template não encontrado');
            }

            // Valida as atualizações
            this.validateTemplate({ ...template, ...updates });

            // Cria backup antes de atualizar
            await this.createBackup(template);

            // Atualiza o template
            const updatedTemplate = {
                ...template,
                ...updates,
                version: template.version + 1,
                updatedAt: new Date().toISOString()
            };

            // Salva no sistema de arquivos
            await fs.writeFile(
                path.join(this.templatePath, `${id}.json`),
                JSON.stringify(updatedTemplate, null, 2)
            );

            // Atualiza o cache
            this.templates.set(id, updatedTemplate);
            if (updatedTemplate.category) {
                this.categories.add(updatedTemplate.category);
            }

            // Limpa cache de renderização
            this.renderedCache.delete(id);

            logger.info('Template atualizado com sucesso', { id });

            return updatedTemplate;
        } catch (error) {
            logger.error('Erro ao atualizar template', {
                id,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Remove um template
     * @param {string} id - ID do template
     */
    async deleteTemplate(id) {
        try {
            const template = this.templates.get(id);
            if (!template) {
                throw new Error('Template não encontrado');
            }

            // Cria backup antes de remover
            await this.createBackup(template);

            // Remove do sistema de arquivos
            await fs.unlink(path.join(this.templatePath, `${id}.json`));

            // Remove do cache
            this.templates.delete(id);
            this.renderedCache.delete(id);

            logger.info('Template removido com sucesso', { id });
        } catch (error) {
            logger.error('Erro ao remover template', {
                id,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Obtém um template pelo ID
     * @param {string} id - ID do template
     * @returns {Object} Template
     */
    getTemplate(id) {
        const template = this.templates.get(id);
        if (!template) {
            throw new Error('Template não encontrado');
        }
        return template;
    }

    /**
     * Lista todos os templates
     * @param {Object} filters - Filtros de busca
     * @returns {Array} Lista de templates
     */
    listTemplates(filters = {}) {
        let templates = Array.from(this.templates.values());

        if (filters.category) {
            templates = templates.filter(t => t.category === filters.category);
        }

        if (filters.search) {
            const search = filters.search.toLowerCase();
            templates = templates.filter(t => 
                t.name.toLowerCase().includes(search) ||
                t.description?.toLowerCase().includes(search)
            );
        }

        return templates;
    }

    /**
     * Lista todas as categorias
     * @returns {Array} Lista de categorias
     */
    listCategories() {
        return Array.from(this.categories);
    }

    /**
     * Renderiza um template com as variáveis fornecidas
     * @param {string} id - ID do template
     * @param {Object} variables - Variáveis para substituição
     * @returns {string} Mensagem renderizada
     */
    renderTemplate(id, variables = {}) {
        const template = this.getTemplate(id);
        
        // Verifica cache
        const cacheKey = this.generateCacheKey(id, variables);
        const cached = this.renderedCache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
            return cached.content;
        }

        let content = template.content;

        // Substitui variáveis
        for (const [key, value] of Object.entries(variables)) {
            const regex = new RegExp(`{{${key}}}`, 'g');
            content = content.replace(regex, value);
        }

        // Valida se todas as variáveis foram substituídas
        const missingVars = content.match(/{{[^}]+}}/g);
        if (missingVars) {
            throw new Error(`Variáveis não fornecidas: ${missingVars.join(', ')}`);
        }

        // Atualiza cache
        this.renderedCache.set(cacheKey, {
            content,
            timestamp: Date.now()
        });

        return content;
    }

    /**
     * Valida um template
     * @private
     */
    validateTemplate(template) {
        if (!template.name) {
            throw new Error('Nome do template é obrigatório');
        }

        if (!template.content) {
            throw new Error('Conteúdo do template é obrigatório');
        }

        // Valida variáveis no conteúdo
        const variables = template.content.match(/{{[^}]+}}/g) || [];
        const uniqueVars = new Set(variables.map(v => v.slice(2, -2)));

        if (template.variables) {
            // Verifica se todas as variáveis definidas estão no conteúdo
            for (const varName of template.variables) {
                if (!uniqueVars.has(varName)) {
                    throw new Error(`Variável "${varName}" definida mas não utilizada no conteúdo`);
                }
            }
        }

        // Verifica se todas as variáveis no conteúdo estão definidas
        for (const varName of uniqueVars) {
            if (template.variables && !template.variables.includes(varName)) {
                throw new Error(`Variável "${varName}" utilizada no conteúdo mas não definida`);
            }
        }
    }

    /**
     * Métodos auxiliares
     */

    isValidTemplateStructure(template) {
        return template &&
            typeof template === 'object' &&
            template.id &&
            template.name &&
            template.content &&
            template.version &&
            template.createdAt &&
            template.updatedAt;
    }

    isDuplicateTemplate(template) {
        const contentHash = crypto
            .createHash('sha256')
            .update(template.content)
            .digest('hex');

        return Array.from(this.templates.values())
            .some(t => {
                const existingHash = crypto
                    .createHash('sha256')
                    .update(t.content)
                    .digest('hex');
                return existingHash === contentHash;
            });
    }

    async createBackup(template) {
        const backupFile = path.join(
            this.backupPath,
            `${template.id}_${Date.now()}.json`
        );
        await fs.writeFile(
            backupFile,
            JSON.stringify(template, null, 2)
        );
    }

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
                const template = JSON.parse(backupContent);
                await fs.writeFile(
                    path.join(this.templatePath, filename),
                    backupContent
                );
                this.templates.set(template.id, template);
                logger.info(`Template ${filename} restaurado do backup`);
            }
        } catch (error) {
            logger.error(`Erro ao restaurar template ${filename} do backup`, {
                error: error.message
            });
        }
    }

    generateCacheKey(id, variables) {
        return `${id}_${JSON.stringify(variables)}`;
    }

    clearExpiredCache() {
        const now = Date.now();
        for (const [key, value] of this.renderedCache.entries()) {
            if (now - value.timestamp > this.cacheTTL) {
                this.renderedCache.delete(key);
            }
        }
    }
}

module.exports = new TemplateManager(); 