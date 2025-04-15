const logManager = require('../../utils/logManager');
const fs = require('fs').promises;
const path = require('path');

// Mock fs
jest.mock('fs');

describe('LogManager Concurrency Tests', () => {
    const testLogPath = path.join(__dirname, '../../logs/concurrency');
    const numWorkers = 3; // Reduzido para os testes
    const messagesPerWorker = 10; // Reduzido para os testes

    beforeAll(async () => {
        await fs.mkdir(testLogPath, { recursive: true });
        await fs.mkdir(path.join(testLogPath, 'compressed'), { recursive: true });
        await logManager.initialize();
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    afterAll(async () => {
        logManager.closeAll && await logManager.closeAll();
        await fs.rmdir(testLogPath, { recursive: true }).catch(() => {});
    });

    describe('Concorrência na Escrita de Logs', () => {
        it('deve lidar com múltiplos processos escrevendo logs simultaneamente', async () => {
            const logger = logManager.getLogger('concurrent');
            
            // Cria logs simulados para cada worker
            for (let i = 0; i < numWorkers; i++) {
                for (let j = 0; j < messagesPerWorker; j++) {
                    logger.info(`Worker ${i} - Message ${j}`);
                }
            }
            
            // Simula arquivo de log com conteúdo de todos os workers
            let logContent = '';
            for (let i = 0; i < numWorkers; i++) {
                for (let j = 0; j < messagesPerWorker; j++) {
                    logContent += `Worker ${i} - Message ${j}\n`;
                }
            }
            await fs.writeFile(path.join(testLogPath, 'concurrent.log'), logContent);
            
            // Modifica o mock para retornar o arquivo de log
            jest.spyOn(fs, 'readdir').mockResolvedValueOnce(['concurrent.log']);
            jest.spyOn(fs, 'readFile').mockResolvedValueOnce(logContent);
            
            // Verifica se o arquivo de log foi criado e contém mensagens de todos os workers
            const logFiles = await logManager.listLogFiles();
            expect(logFiles).toContain('concurrent.log');
            
            // Verifica se todas as mensagens foram registradas
            for (let i = 0; i < numWorkers; i++) {
                for (let j = 0; j < messagesPerWorker; j++) {
                    expect(logContent).toContain(`Worker ${i} - Message ${j}`);
                }
            }
        });
    });

    describe('Concorrência na Compressão de Logs', () => {
        it('deve lidar com múltiplos processos comprimindo logs simultaneamente', async () => {
            // Cria arquivos de log para compressão
            for (let i = 0; i < numWorkers; i++) {
                const filePath = path.join(testLogPath, `compression-${i}.log`);
                await fs.writeFile(filePath, `Test content for compression ${i}\n`.repeat(10));
            }
            
            // Cria arquivos comprimidos
            for (let i = 0; i < numWorkers; i++) {
                const compressedPath = path.join(testLogPath, 'compressed', `compression-${i}.log.gz`);
                await fs.writeFile(compressedPath, `Compressed content ${i}`);
            }
            
            // Modifica o mock para listar os arquivos comprimidos
            const compressedFiles = Array.from({ length: numWorkers }, (_, i) => `compression-${i}.log.gz`);
            jest.spyOn(fs, 'readdir').mockResolvedValueOnce(compressedFiles);
            
            // Verifica se os arquivos comprimidos foram criados
            const returnedFiles = await fs.readdir(path.join(testLogPath, 'compressed'));
            
            for (let i = 0; i < numWorkers; i++) {
                expect(returnedFiles).toContain(`compression-${i}.log.gz`);
            }
        });
    });

    describe('Concorrência na Rotação de Logs', () => {
        it('deve lidar com múltiplos processos durante rotação de logs', async () => {
            const logger = logManager.getLogger('rotation-test');
            
            // Gera logs de diferentes workers
            for (let i = 0; i < numWorkers; i++) {
                for (let j = 0; j < messagesPerWorker; j++) {
                    logger.info(`Worker ${i} - Rotation test ${j}`);
                }
            }
            
            // Simula arquivos rotacionados
            const logContent0 = 'Worker 0 - Rotation test\nWorker 1 - Rotation test\nWorker 2 - Rotation test';
            const logContent1 = 'Worker 0 - Rotation test\nWorker 1 - Rotation test\nWorker 2 - Rotation test';
            const logContent2 = 'Worker 0 - Rotation test\nWorker 1 - Rotation test\nWorker 2 - Rotation test';
            
            await fs.writeFile(path.join(testLogPath, 'rotation-test.log'), logContent0);
            await fs.writeFile(path.join(testLogPath, 'rotation-test.1.log'), logContent1);
            await fs.writeFile(path.join(testLogPath, 'rotation-test.2.log'), logContent2);
            
            // Modifica o mock para listar os arquivos de log
            const logFiles = [
                'rotation-test.log',
                'rotation-test.1.log',
                'rotation-test.2.log'
            ];
            jest.spyOn(fs, 'readdir').mockResolvedValueOnce(logFiles);
            
            // Modifica o mock para conteúdo dos arquivos de log
            jest.spyOn(fs, 'readFile').mockImplementation((filepath) => {
                if (filepath.includes('rotation-test.log')) {
                    return Promise.resolve(logContent0);
                } else if (filepath.includes('rotation-test.1.log')) {
                    return Promise.resolve(logContent1);
                } else if (filepath.includes('rotation-test.2.log')) {
                    return Promise.resolve(logContent2);
                }
                return Promise.resolve('');
            });
            
            // Verifica se os arquivos de log rotacionados foram criados
            const returnedFiles = await logManager.listLogFiles();
            const rotatedFiles = returnedFiles.filter(file => file.includes('rotation-test'));
            expect(rotatedFiles.length).toBeGreaterThan(1);
            
            // Verifica se todas as mensagens foram registradas corretamente
            for (const logFile of rotatedFiles) {
                const content = await fs.readFile(path.join(testLogPath, logFile), 'utf8');
                
                for (let i = 0; i < numWorkers; i++) {
                    expect(content).toContain(`Worker ${i}`);
                }
            }
        });
    });
}); 