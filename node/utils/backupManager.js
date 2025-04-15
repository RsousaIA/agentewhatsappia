const fs = require('fs').promises;
const path = require('path');
const zlib = require('zlib');
const { promisify } = require('util');
const logManager = require('./logManager');

const gzip = promisify(zlib.gzip);
const gunzip = promisify(zlib.gunzip);

class BackupManager {
    constructor() {
        this.backupPath = path.join(__dirname, '..', 'backups');
        this.logger = logManager.getLogger('backup');
    }

    async initialize() {
        try {
            await fs.mkdir(this.backupPath, { recursive: true });
            this.logger.info('BackupManager inicializado com sucesso');
            return true;
        } catch (error) {
            this.logger.error('Erro ao inicializar BackupManager:', error);
            throw error;
        }
    }

    async createBackup(sourcePath, options = {}) {
        try {
            const {
                compression = true,
                maxBackups = 5,
                backupName = path.basename(sourcePath),
                timestamp = new Date().toISOString().replace(/[:.]/g, '-')
            } = options;

            // Verifica se o arquivo/diretório existe
            await fs.access(sourcePath);

            const backupFileName = `${backupName}_${timestamp}${compression ? '.gz' : ''}`;
            const backupFilePath = path.join(this.backupPath, backupFileName);

            if (compression) {
                const content = await fs.readFile(sourcePath);
                const compressed = await gzip(content);
                await fs.writeFile(backupFilePath, compressed);
            } else {
                await fs.copyFile(sourcePath, backupFilePath);
            }

            // Limpa backups antigos se necessário
            if (maxBackups > 0) {
                await this.cleanOldBackups(backupName, maxBackups);
            }

            this.logger.info(`Backup criado com sucesso: ${backupFilePath}`);
            return backupFilePath;
        } catch (error) {
            this.logger.error(`Erro ao criar backup de ${sourcePath}:`, error);
            throw error;
        }
    }

    async createDirectoryBackup(sourceDir, options = {}) {
        try {
            const {
                compression = true,
                maxBackups = 5,
                backupName = path.basename(sourceDir),
                timestamp = new Date().toISOString().replace(/[:.]/g, '-')
            } = options;

            // Verifica se o diretório existe
            await fs.access(sourceDir);

            const backupDirName = `${backupName}_${timestamp}`;
            const backupDirPath = path.join(this.backupPath, backupDirName);
            await fs.mkdir(backupDirPath, { recursive: true });

            // Copia todos os arquivos do diretório
            const files = await fs.readdir(sourceDir);
            for (const file of files) {
                const sourcePath = path.join(sourceDir, file);
                const backupPath = path.join(backupDirPath, file);
                
                if (compression) {
                    const content = await fs.readFile(sourcePath);
                    const compressed = await gzip(content);
                    await fs.writeFile(`${backupPath}.gz`, compressed);
                } else {
                    await fs.copyFile(sourcePath, backupPath);
                }
            }

            // Limpa backups antigos se necessário
            if (maxBackups > 0) {
                await this.cleanOldBackups(backupName, maxBackups);
            }

            this.logger.info(`Backup de diretório criado com sucesso: ${backupDirPath}`);
            return backupDirPath;
        } catch (error) {
            this.logger.error(`Erro ao criar backup do diretório ${sourceDir}:`, error);
            throw error;
        }
    }

    async cleanOldBackups(backupName, maxBackups) {
        try {
            const files = await fs.readdir(this.backupPath);
            const backupFiles = files.filter(file => file.startsWith(backupName));
            
            if (backupFiles.length > maxBackups) {
                // Ordena por data (mais recente primeiro)
                backupFiles.sort((a, b) => {
                    const dateA = new Date(a.split('_')[1]);
                    const dateB = new Date(b.split('_')[1]);
                    return dateB - dateA;
                });

                // Remove os backups mais antigos
                const filesToDelete = backupFiles.slice(maxBackups);
                for (const file of filesToDelete) {
                    const filePath = path.join(this.backupPath, file);
                    await fs.unlink(filePath);
                    this.logger.info(`Backup antigo removido: ${filePath}`);
                }
            }
        } catch (error) {
            this.logger.error('Erro ao limpar backups antigos:', error);
            throw error;
        }
    }

    async listBackups(backupName = null) {
        try {
            const files = await fs.readdir(this.backupPath);
            if (backupName) {
                return files.filter(file => file.startsWith(backupName));
            }
            return files;
        } catch (error) {
            this.logger.error('Erro ao listar backups:', error);
            throw error;
        }
    }

    async restoreBackup(backupPath, targetPath) {
        try {
            // Verifica se o backup existe
            await fs.access(backupPath);

            if (backupPath.endsWith('.gz')) {
                const content = await fs.readFile(backupPath);
                const decompressed = await gunzip(content);
                await fs.writeFile(targetPath, decompressed);
            } else {
                await fs.copyFile(backupPath, targetPath);
            }

            this.logger.info(`Backup restaurado com sucesso: ${targetPath}`);
            return true;
        } catch (error) {
            this.logger.error(`Erro ao restaurar backup ${backupPath}:`, error);
            throw error;
        }
    }
}

module.exports = new BackupManager(); 