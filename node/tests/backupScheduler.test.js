const backupScheduler = require('../utils/backupScheduler');
const backupManager = require('../utils/backupManager');
const cron = require('node-cron');

// Mock do backupManager
jest.mock('../utils/backupManager', () => ({
    createBackup: jest.fn().mockResolvedValue('backup-path'),
    createDirectoryBackup: jest.fn().mockResolvedValue('backup-dir-path')
}));

// Mock do node-cron
jest.mock('node-cron', () => ({
    schedule: jest.fn().mockReturnValue({
        stop: jest.fn(),
        start: jest.fn()
    }),
    validate: jest.fn().mockReturnValue(true)
}));

// Mock do logManager
jest.mock('../utils/logManager', () => ({
    getLogger: jest.fn().mockReturnValue({
        info: jest.fn(),
        error: jest.fn()
    })
}));

describe('BackupScheduler', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        backupScheduler.stopAll();
    });

    describe('Agendamento de Backup', () => {
        it('deve agendar backup de arquivo com configurações padrão', async () => {
            const name = 'test-backup';
            const sourcePath = 'test.log';

            const result = backupScheduler.scheduleBackup(name, sourcePath);

            expect(result).toBe(true);
            expect(cron.schedule).toHaveBeenCalledWith(
                '0 0 * * *',
                expect.any(Function)
            );
        });

        it('deve agendar backup de diretório', async () => {
            const name = 'test-dir-backup';
            const sourcePath = 'logs';
            const options = {
                isDirectory: true,
                schedule: '0 12 * * *'
            };

            const result = backupScheduler.scheduleBackup(name, sourcePath, options);

            expect(result).toBe(true);
            expect(cron.schedule).toHaveBeenCalledWith(
                '0 12 * * *',
                expect.any(Function)
            );
        });

        it('deve validar expressão cron inválida', () => {
            const name = 'invalid-schedule';
            const sourcePath = 'test.log';
            cron.validate.mockReturnValueOnce(false);

            expect(() => {
                backupScheduler.scheduleBackup(name, sourcePath, {
                    schedule: 'invalid'
                });
            }).toThrow('Expressão cron inválida');
        });

        it('deve substituir agendamento existente', () => {
            const name = 'test-backup';
            const sourcePath = 'test.log';

            backupScheduler.scheduleBackup(name, sourcePath);
            backupScheduler.scheduleBackup(name, sourcePath);

            const schedules = backupScheduler.listSchedules();
            expect(schedules.length).toBe(1);
        });
    });

    describe('Gerenciamento de Agendamentos', () => {
        it('deve listar agendamentos', () => {
            backupScheduler.scheduleBackup('backup1', 'test1.log');
            backupScheduler.scheduleBackup('backup2', 'test2.log');

            const schedules = backupScheduler.listSchedules();
            expect(schedules.length).toBe(2);
            expect(schedules[0].name).toBe('backup1');
            expect(schedules[1].name).toBe('backup2');
        });

        it('deve cancelar agendamento', () => {
            const name = 'test-backup';
            backupScheduler.scheduleBackup(name, 'test.log');

            const result = backupScheduler.cancelSchedule(name);
            expect(result).toBe(true);

            const schedules = backupScheduler.listSchedules();
            expect(schedules.length).toBe(0);
        });

        it('deve pausar e retomar agendamento', () => {
            const name = 'test-backup';
            backupScheduler.scheduleBackup(name, 'test.log');

            const pauseResult = backupScheduler.pauseSchedule(name);
            expect(pauseResult).toBe(true);

            const resumeResult = backupScheduler.resumeSchedule(name);
            expect(resumeResult).toBe(true);
        });

        it('deve parar todos os agendamentos', () => {
            backupScheduler.scheduleBackup('backup1', 'test1.log');
            backupScheduler.scheduleBackup('backup2', 'test2.log');

            backupScheduler.stopAll();

            const schedules = backupScheduler.listSchedules();
            expect(schedules.length).toBe(0);
        });
    });

    describe('Execução de Backup', () => {
        it('deve executar backup de arquivo quando agendado', async () => {
            const name = 'test-backup';
            const sourcePath = 'test.log';

            backupScheduler.scheduleBackup(name, sourcePath);

            // Simula a execução do backup agendado
            const scheduleCallback = cron.schedule.mock.calls[0][1];
            await scheduleCallback();

            expect(backupManager.createBackup).toHaveBeenCalledWith(
                sourcePath,
                expect.objectContaining({
                    compression: true,
                    maxBackups: 5
                })
            );
        });

        it('deve executar backup de diretório quando agendado', async () => {
            const name = 'test-dir-backup';
            const sourcePath = 'logs';

            backupScheduler.scheduleBackup(name, sourcePath, { isDirectory: true });

            // Simula a execução do backup agendado
            const scheduleCallback = cron.schedule.mock.calls[0][1];
            await scheduleCallback();

            expect(backupManager.createDirectoryBackup).toHaveBeenCalledWith(
                sourcePath,
                expect.objectContaining({
                    compression: true,
                    maxBackups: 5
                })
            );
        });
    });
}); 