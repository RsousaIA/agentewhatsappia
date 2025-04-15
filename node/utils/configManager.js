const fs = require('fs').promises;
const path = require('path');
const logger = require('../logger');

class ConfigManager {
    constructor() {
        this.config = {};
        this.configPath = path.join(__dirname, '../config');
        this.configFile = path.join(this.configPath, 'config.json');
        this.initialize();
    }

    /**
     * Inicializa o gerenciador de configurações
     */
    async initialize() {
        try {
            // Cria diretório de configurações se não existir
            await fs.mkdir(this.configPath, { recursive: true });
            
            // Carrega configurações existentes
            await this.loadConfig();
            
            logger.info('Gerenciador de configurações inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar gerenciador de configurações', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Carrega configurações do arquivo
     */
    async loadConfig() {
        try {
            // Verifica se o arquivo existe
            try {
                await fs.access(this.configFile);
            } catch {
                // Se não existir, cria com configurações padrão
                await this.saveConfig(this.getDefaultConfig());
                return;
            }

            // Lê o arquivo de configuração
            const content = await fs.readFile(this.configFile, 'utf8');
            this.config = JSON.parse(content);

            logger.info('Configurações carregadas com sucesso');
        } catch (error) {
            logger.error('Erro ao carregar configurações', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Salva configurações no arquivo
     * @param {Object} config - Configurações a serem salvas
     */
    async saveConfig(config) {
        try {
            // Valida as configurações
            this.validateConfig(config);

            // Atualiza o cache
            this.config = config;

            // Salva no arquivo
            await fs.writeFile(
                this.configFile,
                JSON.stringify(config, null, 2)
            );

            logger.info('Configurações salvas com sucesso');
        } catch (error) {
            logger.error('Erro ao salvar configurações', {
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Obtém uma configuração específica
     * @param {string} key - Chave da configuração
     * @param {*} defaultValue - Valor padrão caso a configuração não exista
     * @returns {*} Valor da configuração
     */
    get(key, defaultValue = null) {
        const keys = key.split('.');
        let value = this.config;

        for (const k of keys) {
            if (value === undefined || value === null) {
                return defaultValue;
            }
            value = value[k];
        }

        return value === undefined ? defaultValue : value;
    }

    /**
     * Define uma configuração específica
     * @param {string} key - Chave da configuração
     * @param {*} value - Valor da configuração
     */
    async set(key, value) {
        try {
            const keys = key.split('.');
            const config = { ...this.config };
            let current = config;

            // Navega até o último nível
            for (let i = 0; i < keys.length - 1; i++) {
                const k = keys[i];
                if (current[k] === undefined) {
                    current[k] = {};
                }
                current = current[k];
            }

            // Define o valor
            current[keys[keys.length - 1]] = value;

            // Salva as configurações
            await this.saveConfig(config);
        } catch (error) {
            logger.error('Erro ao definir configuração', {
                key,
                error: error.message
            });
            throw error;
        }
    }

    /**
     * Retorna todas as configurações
     * @returns {Object} Configurações
     */
    getAll() {
        return { ...this.config };
    }

    /**
     * Retorna as configurações padrão
     * @private
     */
    getDefaultConfig() {
        return {
            server: {
                port: 3000,
                host: 'localhost'
            },
            whatsapp: {
                sessionPath: './sessions',
                puppeteer: {
                    headless: true,
                    args: ['--no-sandbox']
                }
            },
            logging: {
                level: 'info',
                file: './logs/app.log'
            },
            database: {
                type: 'sqlite',
                path: './data/database.sqlite'
            },
            security: {
                jwtSecret: 'your-secret-key',
                tokenExpiration: '24h'
            }
        };
    }

    /**
     * Valida as configurações
     * @private
     */
    validateConfig(config) {
        // Validações básicas
        if (!config.server || typeof config.server.port !== 'number') {
            throw new Error('Porta do servidor inválida');
        }

        if (!config.whatsapp || !config.whatsapp.sessionPath) {
            throw new Error('Caminho da sessão do WhatsApp inválido');
        }

        if (!config.logging || !config.logging.level) {
            throw new Error('Nível de log inválido');
        }

        if (!config.security || !config.security.jwtSecret) {
            throw new Error('Chave secreta JWT inválida');
        }
    }
}

module.exports = new ConfigManager(); 