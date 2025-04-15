const backupManager = require('../utils/backupManager');
const fs = require('fs').promises;
const path = require('path');
const zlib = require('zlib');
const { promisify } = require('util');

// Mock do fs
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn().mockResolvedValue(undefined),
        readdir: jest.fn().mockResolvedValue([]),
        access: jest.fn().mockResolvedValue(undefined),
        readFile: jest.fn().mockResolvedValue(Buffer.from('test content')),
        writeFile: jest.fn().mockResolvedValue(undefined),
        copyFile: jest.fn().mockResolvedValue(undefined),
        unlink: jest.fn().mockResolvedValue(undefined)
    }
}));

// Mock do zlib
jest.mock('zlib', () => ({
    gzip: jest.fn((data, callback) => callback(null, Buffer.from('compressed'))),
    gunzip: jest.fn((data, callback) => callback(null, Buffer.from('decompressed'))),
    promisify: jest.fn(fn => fn)
}));

// Mock do logManager
jest.mock('../utils/logManager', () => ({
    getLogger: jest.fn().mockReturnValue({
        info: jest.fn(),
        error: jest.fn()
    })
}));

jest.setTimeout(30000);

describe('BackupManager', () => {
    beforeAll(async () => {
        try {
            await backupManager.initialize();
        } catch (error) {
            throw error;
        }
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Inicialização', () => {
        it('deve criar diretório de backups se não existir', async () => {
            await backupManager.initialize();
            
            expect(fs.mkdir).toHaveBeenCalledWith(
                expect.stringContaining('backups'),
                expect.objectContaining({ recursive: true })
            );
        });
    });

    describe('Criação de Backup', () => {
        it('deve criar backup de arquivo com compressão', async () => {
            const sourcePath = 'test.log';
            const backupPath = await backupManager.createBackup(sourcePath);
            
            expect(backupPath).toContain('test.log_');
            expect(backupPath).toContain('.gz');
            expect(fs.readFile).toHaveBeenCalledWith(sourcePath);
            expect(zlib.gzip).toHaveBeenCalled();
        });

        it('deve criar backup de arquivo sem compressão', async () => {
            const sourcePath = 'test.log';
            const backupPath = await backupManager.createBackup(sourcePath, { compression: false });
            
            expect(backupPath).toContain('test.log_');
            expect(backupPath).not.toContain('.gz');
            expect(fs.copyFile).toHaveBeenCalled();
        });

        it('deve criar backup de diretório', async () => {
            const sourceDir = 'logs';
            const backupPath = await backupManager.createDirectoryBackup(sourceDir);
            
            expect(backupPath).toContain('logs_');
            expect(fs.readdir).toHaveBeenCalledWith(sourceDir);
        });
    });

    describe('Limpeza de Backups', () => {
        it('deve limpar backups antigos', async () => {
            const mockFiles = [
                'test_2024-01-01.gz',
                'test_2024-01-02.gz',
                'test_2024-01-03.gz',
                'test_2024-01-04.gz',
                'test_2024-01-05.gz',
                'test_2024-01-06.gz'
            ];
            
            fs.readdir.mockResolvedValueOnce(mockFiles);
            
            await backupManager.cleanOldBackups('test', 5);
            
            expect(fs.unlink).toHaveBeenCalledTimes(1);
            expect(fs.unlink).toHaveBeenCalledWith(
                expect.any(String)
            );
        });
    });

    describe('Listagem de Backups', () => {
        it('deve listar todos os backups', async () => {
            const mockFiles = ['backup1.gz', 'backup2.gz'];
            fs.readdir.mockResolvedValueOnce(mockFiles);
            
            const backups = await backupManager.listBackups();
            expect(backups).toEqual(mockFiles);
        });

        it('deve listar backups por nome', async () => {
            const mockFiles = ['test1.gz', 'test2.gz', 'other.gz'];
            fs.readdir.mockResolvedValueOnce(mockFiles);
            
            const backups = await backupManager.listBackups('test');
            expect(backups).toEqual(['test1.gz', 'test2.gz']);
        });
    });

    describe('Restauração de Backup', () => {
        it('deve restaurar backup comprimido', async () => {
            const backupPath = 'test.gz';
            const targetPath = 'restored.log';
            
            await backupManager.restoreBackup(backupPath, targetPath);
            
            expect(fs.access).toHaveBeenCalledWith(backupPath);
            expect(fs.readFile).toHaveBeenCalledWith(backupPath);
            expect(fs.writeFile).toHaveBeenCalledWith(targetPath, expect.any(Buffer));
        });

        it('deve restaurar backup não comprimido', async () => {
            const backupPath = 'test.log';
            const targetPath = 'restored.log';
            
            await backupManager.restoreBackup(backupPath, targetPath);
            
            expect(fs.access).toHaveBeenCalledWith(backupPath);
            expect(fs.copyFile).toHaveBeenCalled();
        });
    });
}); 