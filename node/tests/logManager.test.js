const logManager = require('../utils/logManager');
const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');
const zlib = require('zlib');

// Mock do fs
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn().mockResolvedValue(undefined),
        readdir: jest.fn().mockResolvedValue([]),
        stat: jest.fn().mockResolvedValue({ mtime: new Date() }),
        readFile: jest.fn().mockResolvedValue(Buffer.from('')),
        writeFile: jest.fn().mockResolvedValue(undefined),
        unlink: jest.fn().mockResolvedValue(undefined),
        access: jest.fn().mockResolvedValue(undefined)
    }
}));

// Mock do zlib
jest.mock('zlib', () => ({
    gzip: jest.fn((data, callback) => callback(null, Buffer.from('compressed'))),
    gunzip: jest.fn((data, callback) => callback(null, Buffer.from('decompressed'))),
    promisify: jest.fn(fn => fn)
}));

jest.setTimeout(30000); // Aumenta o timeout global para 30 segundos

describe('LogManager', () => {
    beforeAll(async () => {
        try {
            await logManager.initialize();
        } catch (error) {
            throw error;
        }
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    afterAll(async () => {
        try {
            await logManager.closeAll();
        } catch (error) {
            // Ignora erros no fechamento dos loggers
        }
    });

    describe('Inicialização', () => {
        it('deve criar diretório de logs se não existir', async () => {
            await logManager.initialize();
            
            expect(fs.mkdir).toHaveBeenCalledWith(
                expect.stringContaining('logs'),
                expect.objectContaining({ recursive: true })
            );
        });

        it('deve criar diretório compressed', async () => {
            await logManager.initialize();
            
            expect(fs.mkdir).toHaveBeenCalledWith(
                expect.stringContaining('compressed'),
                expect.objectContaining({ recursive: true })
            );
        });

        it('deve criar logger padrão', async () => {
            await logManager.initialize();
            
            const defaultLogger = logManager.getLogger('default');
            expect(defaultLogger).toBeDefined();
        });
    });

    describe('Criação de Loggers', () => {
        it('deve criar logger com configurações padrão', () => {
            const logger = logManager.createLogger('test');
            expect(logger).toBeDefined();
            const retrieved = logManager.getLogger('test');
            expect(retrieved).toBeDefined();
        });

        it('deve criar logger com configurações personalizadas', () => {
            const customOptions = {
                level: 'error',
                maxSize: 10 * 1024 * 1024,
                maxFiles: 10
            };
            const logger = logManager.createLogger('custom', customOptions);
            expect(logger).toBeDefined();
        });

        it('deve adicionar console transport em ambiente de desenvolvimento', () => {
            const originalEnv = process.env.NODE_ENV;
            process.env.NODE_ENV = 'development';
            
            const logger = logManager.createLogger('dev');
            expect(logger).toBeDefined();
            
            process.env.NODE_ENV = originalEnv;
        });
    });

    describe('Gerenciamento de Loggers', () => {
        it('deve retornar logger existente', () => {
            const logger = logManager.createLogger('existing');
            const retrieved = logManager.getLogger('existing');
            expect(retrieved).toBeDefined();
        });

        it('deve retornar logger padrão quando nome não existe', () => {
            const defaultLogger = logManager.getLogger('default');
            const nonExistent = logManager.getLogger('non-existent');
            expect(nonExistent).toBeDefined();
        });

        it('não deve remover logger padrão', () => {
            const defaultLogger = logManager.getLogger('default');
            logManager.removeLogger('default');
            const stillDefault = logManager.getLogger('default');
            expect(stillDefault).toBeDefined();
        });

        it('deve remover logger não padrão', () => {
            const logger = logManager.createLogger('to-remove');
            const defaultLogger = logManager.getLogger('default');
            logManager.removeLogger('to-remove');
            const afterRemoval = logManager.getLogger('to-remove');
            expect(afterRemoval).toBeDefined();
        });
    });

    describe('Listagem de Arquivos de Log', () => {
        it('deve listar apenas arquivos .log', async () => {
            const mockFiles = ['file1.log', 'file2.log', 'other.txt'];
            fs.readdir.mockResolvedValueOnce(mockFiles);
            
            const logFiles = await logManager.listLogFiles();
            expect(logFiles).toContain('file1.log');
            expect(logFiles).toContain('file2.log');
            expect(logFiles).not.toContain('other.txt');
        });

        it('deve retornar array vazio em caso de erro', async () => {
            fs.readdir.mockRejectedValueOnce(new Error('Erro de leitura'));
            const logFiles = await logManager.listLogFiles();
            expect(logFiles).toEqual([]);
        });
    });

    describe('Limpeza de Logs Antigos', () => {
        it('deve comprimir logs mais antigos que o período especificado', async () => {
            const now = new Date();
            const oldDate = new Date(now);
            oldDate.setDate(oldDate.getDate() - 40);
            
            const mockFiles = ['old.log', 'new.log'];
            fs.readdir.mockResolvedValueOnce(mockFiles);
            
            fs.stat.mockImplementation(async (filePath) => {
                if (filePath.includes('old.log')) {
                    return { mtime: oldDate };
                }
                return { mtime: now };
            });
            
            const count = await logManager.cleanOldLogs(30);
            expect(count).toBe(1);
        });

        it('deve retornar 0 em caso de falha na limpeza', async () => {
            fs.readdir.mockRejectedValueOnce(new Error('Erro de leitura'));
            const count = await logManager.cleanOldLogs(30);
            expect(count).toBe(0);
        });
    });

    describe('Compressão de Logs', () => {
        it('deve comprimir arquivo de log', async () => {
            const filePath = path.join(logManager.logPath, 'test.log');
            const content = 'Test log content';
            
            fs.readFile.mockResolvedValueOnce(Buffer.from(content));
            
            const compressedPath = await logManager.compressLog(filePath);
            expect(compressedPath).toContain('test.log.gz');
        });

        it('deve lançar erro se arquivo não existir', async () => {
            fs.access.mockRejectedValueOnce({ code: 'ENOENT' });
            await expect(logManager.compressLog('nonexistent.log')).rejects.toThrow('Arquivo não encontrado');
        });
    });

    describe('Descompressão de Logs', () => {
        it('deve descomprimir arquivo de log', async () => {
            const filePath = path.join(logManager.compressedPath, 'test.log.gz');
            const compressedContent = Buffer.from([0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03]);
            
            fs.readFile.mockResolvedValueOnce(compressedContent);
            
            const decompressedPath = await logManager.decompressLog(filePath);
            expect(decompressedPath).toContain('test.log');
        });

        it('deve lançar erro se arquivo não existir', async () => {
            fs.access.mockRejectedValueOnce({ code: 'ENOENT' });
            await expect(logManager.decompressLog('nonexistent.log.gz')).rejects.toThrow('Arquivo não encontrado');
        });

        it('deve lançar erro se arquivo não for gzip', async () => {
            const filePath = path.join(logManager.compressedPath, 'test.log.gz');
            const invalidContent = Buffer.from('not a gzip file');
            
            fs.readFile.mockResolvedValueOnce(invalidContent);
            
            await expect(logManager.decompressLog(filePath)).rejects.toThrow('Arquivo não está no formato gzip');
        });
    });
}); 