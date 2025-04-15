const cron = require('node-cron');
const path = require('path');
const backupManager = require('./backupManager');
const logManager = require('./logManager');

class BackupScheduler {
    constructor() {
        this.schedules = new Map();
        this.logger = logManager.getLogger('backup-scheduler');
    }

    /**
     * Agenda um backup para ser executado periodicamente
     * @param {string} name - Nome único para identificar o agendamento
     * @param {string} sourcePath - Caminho do arquivo/diretório para backup
     * @param {Object} options - Opções de agendamento
     * @param {string} options.schedule - Expressão cron para agendamento (ex: '0 0 * * *' para diário à meia-noite)
     * @param {boolean} options.compression - Se deve usar compressão (padrão: true)
     * @param {number} options.maxBackups - Número máximo de backups a manter (padrão: 5)
     * @param {boolean} options.isDirectory - Se o sourcePath é um diretório (padrão: false)
     * @returns {boolean} - true se agendado com sucesso
     */
    scheduleBackup(name, sourcePath, options = {}) {
        try {
            const {
                schedule = '0 0 * * *', // Padrão: diariamente à meia-noite
                compression = true,
                maxBackups = 5,
                isDirectory = false
            } = options;

            // Valida a expressão cron
            if (!cron.validate(schedule)) {
                throw new Error(`Expressão cron inválida: ${schedule}`);
            }

            // Cancela agendamento existente com mesmo nome
            this.cancelSchedule(name);

            // Cria novo agendamento
            const task = cron.schedule(schedule, async () => {
                try {
                    this.logger.info(`Iniciando backup agendado: ${name}`);
                    
                    if (isDirectory) {
                        await backupManager.createDirectoryBackup(sourcePath, { compression, maxBackups });
                    } else {
                        await backupManager.createBackup(sourcePath, { compression, maxBackups });
                    }
                    
                    this.logger.info(`Backup agendado concluído: ${name}`);
                } catch (error) {
                    this.logger.error(`Erro no backup agendado ${name}:`, error);
                }
            });

            // Armazena informações do agendamento
            this.schedules.set(name, {
                task,
                config: {
                    sourcePath,
                    schedule,
                    compression,
                    maxBackups,
                    isDirectory
                }
            });

            this.logger.info(`Backup agendado com sucesso: ${name} (${schedule})`);
            return true;
        } catch (error) {
            this.logger.error(`Erro ao agendar backup ${name}:`, error);
            throw error;
        }
    }

    /**
     * Cancela um agendamento de backup
     * @param {string} name - Nome do agendamento
     * @returns {boolean} - true se cancelado com sucesso
     */
    cancelSchedule(name) {
        const schedule = this.schedules.get(name);
        if (schedule) {
            schedule.task.stop();
            this.schedules.delete(name);
            this.logger.info(`Agendamento cancelado: ${name}`);
            return true;
        }
        return false;
    }

    /**
     * Lista todos os agendamentos ativos
     * @returns {Array<Object>} - Lista de agendamentos
     */
    listSchedules() {
        const schedules = [];
        for (const [name, { config }] of this.schedules) {
            schedules.push({
                name,
                ...config
            });
        }
        return schedules;
    }

    /**
     * Pausa um agendamento
     * @param {string} name - Nome do agendamento
     * @returns {boolean} - true se pausado com sucesso
     */
    pauseSchedule(name) {
        const schedule = this.schedules.get(name);
        if (schedule) {
            schedule.task.stop();
            this.logger.info(`Agendamento pausado: ${name}`);
            return true;
        }
        return false;
    }

    /**
     * Retoma um agendamento pausado
     * @param {string} name - Nome do agendamento
     * @returns {boolean} - true se retomado com sucesso
     */
    resumeSchedule(name) {
        const schedule = this.schedules.get(name);
        if (schedule) {
            schedule.task.start();
            this.logger.info(`Agendamento retomado: ${name}`);
            return true;
        }
        return false;
    }

    /**
     * Para todos os agendamentos
     */
    stopAll() {
        for (const [name, schedule] of this.schedules) {
            schedule.task.stop();
            this.logger.info(`Agendamento parado: ${name}`);
        }
        this.schedules.clear();
    }
}

module.exports = new BackupScheduler(); 