const winston = require('winston');
const path = require('path');
const fs = require('fs').promises;
const zlib = require('zlib');
const { promisify } = require('util');

const gzip = promisify(zlib.gzip);
const gunzip = promisify(zlib.gunzip);

class LogManager {
    constructor() {
        this.loggers = new Map();
        this.logPath = path.join(__dirname, '..', 'logs');
        this.compressedPath = path.join(this.logPath, 'compressed');
        this.defaultLoggerName = 'default';
        this.isDevelopment = process.env.NODE_ENV === 'development';
    }

    async initialize() {
        try {
            await fs.mkdir(this.logPath, { recursive: true });
            await fs.mkdir(this.compressedPath, { recursive: true });

            // Só cria o logger padrão se ele não existir
            if (!this.loggers.has(this.defaultLoggerName)) {
                await this.createLogger(this.defaultLoggerName, {
                    level: 'info',
                    maxSize: 5 * 1024 * 1024, // 5MB
                    maxFiles: 5
                });
            }

            return true;
        } catch (error) {
            console.error('Erro ao inicializar LogManager:', error);
            throw error;
        }
    }

    async createLogger(name, options = {}) {
        if (this.loggers.has(name)) {
            return this.loggers.get(name);
        }

        const transports = [
            new winston.transports.File({
                filename: path.join(this.logPath, `${name}.log`),
                maxsize: options.maxSize || 5 * 1024 * 1024,
                maxFiles: options.maxFiles || 5,
                tailable: true
            })
        ];

        // Adiciona console transport em ambiente de desenvolvimento
        if (this.isDevelopment) {
            transports.push(new winston.transports.Console({
                format: winston.format.simple()
            }));
        }

        const logger = winston.createLogger({
            level: options.level || 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.json()
            ),
            transports: transports
        });

        this.loggers.set(name, logger);
        return logger;
    }

    getLogger(name) {
        return this.loggers.get(name) || this.loggers.get(this.defaultLoggerName);
    }

    async removeLogger(name) {
        if (name === this.defaultLoggerName) {
            return false;
        }

        const logger = this.loggers.get(name);
        if (logger) {
            // Fecha todos os transports antes de remover
            await Promise.all(logger.transports.map(transport => 
                new Promise(resolve => {
                    try {
                        transport.close();
                    } catch (error) {
                        // Ignora erros ao fechar transports
                    }
                    resolve();
                })
            ));
            this.loggers.delete(name);
            return true;
        }
        return false;
    }

    async listLogFiles() {
        try {
            const files = await fs.readdir(this.logPath);
            return files.filter(file => file.endsWith('.log'));
        } catch (error) {
            console.error('Erro ao listar arquivos de log:', error);
            return [];
        }
    }

    async cleanOldLogs(maxAge = 30 * 24 * 60 * 60 * 1000) { // 30 dias por padrão
        try {
            const files = await this.listLogFiles();
            const now = Date.now();
            let count = 0;

            for (const file of files) {
                const filePath = path.join(this.logPath, file);
                const stats = await fs.stat(filePath);

                if (now - stats.mtime.getTime() > maxAge) {
                    await this.compressLog(filePath);
                    await fs.unlink(filePath);
                    count++;
                }
            }

            return count;
        } catch (error) {
            console.error('Erro ao limpar logs antigos:', error);
            return 0;
        }
    }

    async compressLog(filePath) {
        try {
            // Verifica se o arquivo existe
            await fs.access(filePath);

            const content = await fs.readFile(filePath);
            const compressed = await gzip(content);
            
            const fileName = path.basename(filePath);
            const compressedPath = path.join(this.compressedPath, `${fileName}.gz`);
            
            await fs.writeFile(compressedPath, compressed);
            return compressedPath;
        } catch (error) {
            if (error.code === 'ENOENT') {
                throw new Error(`Arquivo não encontrado: ${filePath}`);
            }
            throw new Error(`Erro ao comprimir log ${filePath}: ${error.message}`);
        }
    }

    async decompressLog(filePath) {
        try {
            // Verifica se o arquivo existe
            await fs.access(filePath);

            const content = await fs.readFile(filePath);
            
            // Verifica se o arquivo é realmente um arquivo gzip
            const isGzip = content[0] === 0x1f && content[1] === 0x8b;
            if (!isGzip) {
                throw new Error('Arquivo não está no formato gzip');
            }
            
            const decompressed = await gunzip(content);
            
            const fileName = path.basename(filePath, '.gz');
            const decompressedPath = path.join(this.logPath, fileName);
            
            await fs.writeFile(decompressedPath, decompressed);
            return decompressedPath;
        } catch (error) {
            if (error.code === 'ENOENT') {
                throw new Error(`Arquivo não encontrado: ${filePath}`);
            }
            throw new Error(`Erro ao descomprimir log ${filePath}: ${error.message}`);
        }
    }

    async closeAll() {
        try {
            const loggerNames = Array.from(this.loggers.keys());
            const promises = loggerNames.map(name => {
                const logger = this.loggers.get(name);
                if (logger) {
                    return Promise.all(logger.transports.map(transport => 
                        new Promise(resolve => {
                            try {
                                transport.close();
                            } catch (error) {
                                // Ignora erros ao fechar transports
                            }
                            resolve();
                        })
                    ));
                }
                return Promise.resolve();
            });

            await Promise.all(promises);
            this.loggers.clear();
            return true;
        } catch (error) {
            console.error('Erro ao fechar loggers:', error);
            return false;
        }
    }
}

module.exports = new LogManager(); 