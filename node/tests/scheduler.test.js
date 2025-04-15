const scheduler = require('../utils/scheduler');
const fs = require('fs').promises;
const path = require('path');
const schedule = require('node-schedule');
const metricsManager = require('../utils/metricsManager');

// Mock do sistema de arquivos
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn(),
        readdir: jest.fn(),
        readFile: jest.fn(),
        writeFile: jest.fn(),
        unlink: jest.fn()
    }
}));

// Mock do node-schedule
jest.mock('node-schedule', () => ({
    scheduleJob: jest.fn().mockReturnValue({
        cancel: jest.fn()
    })
}));

describe('Scheduler', () => {
    let scheduler;
    const testMessage = {
        content: 'Test message',
        scheduledTime: new Date(Date.now() + 1000).toISOString(),
        recipient: 'test@example.com'
    };

    beforeEach(async () => {
        scheduler = new scheduler();
        await scheduler.initialize();
        
        // Limpa o cache de mensagens e jobs
        scheduler.scheduledMessages.clear();
        scheduler.jobs.clear();
        
        // Reseta os mocks
        jest.clearAllMocks();
    });

    afterEach(async () => {
        // Limpa mensagens de teste
        const files = await fs.readdir(scheduler.schedulerPath);
        for (const file of files) {
            if (file.endsWith('.json')) {
                await fs.unlink(path.join(scheduler.schedulerPath, file));
            }
        }
    });

    describe('Limite de Mensagens', () => {
        it('deve lançar erro ao exceder limite de mensagens', async () => {
            // Preenche o scheduler com mensagens até o limite
            for (let i = 0; i < scheduler.maxMessages; i++) {
                await scheduler.scheduleMessage({
                    ...testMessage,
                    scheduledTime: new Date(Date.now() + (i * 1000)).toISOString()
                });
            }

            // Tenta adicionar mais uma mensagem
            await expect(scheduler.scheduleMessage(testMessage))
                .rejects
                .toThrow('Limite máximo de mensagens agendadas atingido');
        });
    });

    describe('Timeout de Processamento', () => {
        it('deve lançar erro ao exceder timeout de processamento', async () => {
            // Mock do sendMessage para simular timeout
            scheduler.sendMessage = jest.fn(() => new Promise(resolve => setTimeout(resolve, scheduler.processingTimeout + 1000)));

            const message = await scheduler.scheduleMessage(testMessage);
            
            // Aguarda processamento
            await new Promise(resolve => setTimeout(resolve, scheduler.processingTimeout + 2000));

            const updatedMessage = scheduler.scheduledMessages.get(message.id);
            expect(updatedMessage.status).toBe('failed');
        });
    });

    describe('Retry de Mensagens', () => {
        it('deve tentar reenviar mensagem após falha', async () => {
            let sendAttempts = 0;
            
            // Mock do sendMessage para falhar duas vezes e depois ter sucesso
            scheduler.sendMessage = jest.fn(() => {
                sendAttempts++;
                if (sendAttempts <= 2) {
                    throw new Error('Falha temporária');
                }
                return Promise.resolve();
            });

            const message = await scheduler.scheduleMessage(testMessage);
            
            // Aguarda processamento com retries
            await new Promise(resolve => setTimeout(resolve, (scheduler.retryDelay * 3) + 1000));

            const updatedMessage = scheduler.scheduledMessages.get(message.id);
            expect(updatedMessage.status).toBe('sent');
            expect(sendAttempts).toBe(3);
        });

        it('deve marcar como falha após máximo de tentativas', async () => {
            // Mock do sendMessage para sempre falhar
            scheduler.sendMessage = jest.fn(() => {
                throw new Error('Falha persistente');
            });

            const message = await scheduler.scheduleMessage(testMessage);
            
            // Aguarda processamento com todas as tentativas
            await new Promise(resolve => setTimeout(resolve, (scheduler.retryDelay * (scheduler.maxRetries + 1)) + 1000));

            const updatedMessage = scheduler.scheduledMessages.get(message.id);
            expect(updatedMessage.status).toBe('failed');
            expect(scheduler.sendMessage).toHaveBeenCalledTimes(scheduler.maxRetries + 1);
        });
    });

    describe('Limpeza de Mensagens Antigas', () => {
        it('deve remover mensagens antigas automaticamente', async () => {
            // Cria mensagem antiga
            const oldMessage = {
                ...testMessage,
                createdAt: new Date(Date.now() - (31 * 24 * 60 * 60 * 1000)).toISOString()
            };
            await scheduler.scheduleMessage(oldMessage);

            // Executa limpeza
            await scheduler.cleanOldMessages();

            expect(scheduler.scheduledMessages.size).toBe(0);
        });

        it('não deve remover mensagens recentes', async () => {
            // Cria mensagem recente
            const recentMessage = {
                ...testMessage,
                createdAt: new Date().toISOString()
            };
            await scheduler.scheduleMessage(recentMessage);

            // Executa limpeza
            await scheduler.cleanOldMessages();

            expect(scheduler.scheduledMessages.size).toBe(1);
        });
    });

    describe('Backup e Restauração', () => {
        it('deve criar backup de mensagens', async () => {
            // Cria mensagem
            await scheduler.scheduleMessage(testMessage);

            // Cria backup
            await scheduler.createBackup();

            // Verifica se arquivo de backup foi criado
            const backups = await fs.readdir(scheduler.backupPath);
            expect(backups.length).toBeGreaterThan(0);
        });

        it('deve restaurar mensagem do backup', async () => {
            // Cria mensagem
            const message = await scheduler.scheduleMessage(testMessage);

            // Cria backup
            await scheduler.createBackup();

            // Remove mensagem original
            await fs.unlink(path.join(scheduler.schedulerPath, `${message.id}.json`));
            scheduler.scheduledMessages.delete(message.id);

            // Restaura do backup
            await scheduler.restoreFromBackup(`${message.id}.json`);

            expect(scheduler.scheduledMessages.has(message.id)).toBe(true);
        });
    });

    describe('scheduleMessage', () => {
        it('deve agendar uma nova mensagem com sucesso', async () => {
            const message = {
                to: '5511999999999',
                content: 'Mensagem de teste',
                scheduledTime: new Date(Date.now() + 3600000).toISOString() // 1 hora no futuro
            };

            await scheduler.scheduleMessage(message);

            expect(scheduler.scheduledMessages.size).toBe(1);
            const scheduledMessage = Array.from(scheduler.scheduledMessages.values())[0];
            expect(scheduledMessage.to).toBe(message.to);
            expect(scheduledMessage.content).toBe(message.content);
            expect(scheduledMessage.scheduledTime).toBe(message.scheduledTime);
            expect(scheduledMessage.status).toBe('scheduled');
            expect(scheduledMessage.id).toBeDefined();
            expect(scheduledMessage.createdAt).toBeDefined();
            expect(scheduledMessage.updatedAt).toBeDefined();
        });

        it('deve lançar erro se a mensagem for inválida', async () => {
            const message = {
                // to não definido
                content: 'Mensagem de teste',
                scheduledTime: new Date(Date.now() + 3600000).toISOString()
            };

            await expect(scheduler.scheduleMessage(message))
                .rejects
                .toThrow('Destinatário é obrigatório');
        });

        it('deve lançar erro se a data de agendamento for no passado', async () => {
            const message = {
                to: '5511999999999',
                content: 'Mensagem de teste',
                scheduledTime: new Date(Date.now() - 3600000).toISOString() // 1 hora no passado
            };

            await expect(scheduler.scheduleMessage(message))
                .rejects
                .toThrow('Data de agendamento deve ser futura');
        });
    });

    describe('updateMessageStatus', () => {
        it('deve atualizar o status de uma mensagem existente', async () => {
            // Cria uma mensagem
            const message = {
                to: '5511999999999',
                content: 'Mensagem de teste',
                scheduledTime: new Date(Date.now() + 3600000).toISOString()
            };
            const scheduledMessage = await scheduler.scheduleMessage(message);

            // Atualiza o status
            await scheduler.updateMessageStatus(scheduledMessage.id, 'sent');

            const updatedMessage = scheduler.scheduledMessages.get(scheduledMessage.id);
            expect(updatedMessage.status).toBe('sent');
        });

        it('deve lançar erro ao tentar atualizar mensagem inexistente', async () => {
            await expect(scheduler.updateMessageStatus('id-inexistente', 'sent'))
                .rejects
                .toThrow('Mensagem não encontrada');
        });
    });

    describe('cancelMessage', () => {
        it('deve cancelar uma mensagem agendada', async () => {
            // Cria uma mensagem
            const message = {
                to: '5511999999999',
                content: 'Mensagem de teste',
                scheduledTime: new Date(Date.now() + 3600000).toISOString()
            };
            const scheduledMessage = await scheduler.scheduleMessage(message);

            // Cancela a mensagem
            await scheduler.cancelMessage(scheduledMessage.id);

            const cancelledMessage = scheduler.scheduledMessages.get(scheduledMessage.id);
            expect(cancelledMessage.status).toBe('cancelled');
            expect(scheduler.jobs.size).toBe(0);
        });

        it('deve lançar erro ao tentar cancelar mensagem inexistente', async () => {
            await expect(scheduler.cancelMessage('id-inexistente'))
                .rejects
                .toThrow('Mensagem não encontrada');
        });
    });

    describe('listMessages', () => {
        beforeEach(async () => {
            // Cria algumas mensagens para teste
            await scheduler.scheduleMessage({
                to: '5511999999999',
                content: 'Mensagem 1',
                scheduledTime: new Date(Date.now() + 3600000).toISOString(),
                status: 'scheduled'
            });

            await scheduler.scheduleMessage({
                to: '5511999999999',
                content: 'Mensagem 2',
                scheduledTime: new Date(Date.now() + 7200000).toISOString(),
                status: 'sent'
            });

            await scheduler.scheduleMessage({
                to: '5511999999999',
                content: 'Mensagem 3',
                scheduledTime: new Date(Date.now() + 10800000).toISOString(),
                status: 'scheduled'
            });
        });

        it('deve listar todas as mensagens sem filtros', () => {
            const messages = scheduler.listMessages();
            expect(messages.length).toBe(3);
        });

        it('deve filtrar mensagens por status', () => {
            const messages = scheduler.listMessages({ status: 'scheduled' });
            expect(messages.length).toBe(2);
            expect(messages.every(m => m.status === 'scheduled')).toBe(true);
        });

        it('deve filtrar mensagens por data', () => {
            const startDate = new Date(Date.now() + 3600000).toISOString();
            const endDate = new Date(Date.now() + 7200000).toISOString();
            
            const messages = scheduler.listMessages({
                startDate,
                endDate
            });
            
            expect(messages.length).toBe(1);
            expect(new Date(messages[0].scheduledTime).getTime())
                .toBeGreaterThanOrEqual(new Date(startDate).getTime());
            expect(new Date(messages[0].scheduledTime).getTime())
                .toBeLessThanOrEqual(new Date(endDate).getTime());
        });
    });

    describe('Cache e Métricas', () => {
        it('deve armazenar mensagem no cache', async () => {
            const message = await scheduler.scheduleMessage(testMessage);
            const cached = scheduler.messageCache.get(message.id);
            
            expect(cached).toBeDefined();
            expect(cached.message).toEqual(message);
            expect(cached.timestamp).toBeLessThanOrEqual(Date.now());
        });

        it('deve retornar mensagem do cache quando disponível', async () => {
            const message = await scheduler.scheduleMessage(testMessage);
            const cachedMessage = await scheduler.getMessage(message.id);
            
            expect(cachedMessage).toEqual(message);
        });

        it('deve limpar cache após TTL', async () => {
            const message = await scheduler.scheduleMessage(testMessage);
            
            // Simula passagem do tempo
            scheduler.cacheTTL = 1000;
            await new Promise(resolve => setTimeout(resolve, 1100));
            
            await scheduler.cleanCache();
            
            expect(scheduler.messageCache.has(message.id)).toBe(false);
        });

        it('deve registrar métricas corretamente', async () => {
            // Agenda mensagem
            await scheduler.scheduleMessage(testMessage);
            
            // Verifica métricas
            const totalMessages = await metricsManager.getMetric('scheduler_messages_total');
            expect(totalMessages.value).toBe(1);

            // Simula processamento
            scheduler.sendMessage = jest.fn().mockResolvedValue();
            await scheduler.processMessage(testMessage);
            
            const processedMessages = await metricsManager.getMetric('scheduler_messages_processed');
            expect(processedMessages.value).toBe(1);

            const processingTime = await metricsManager.getMetric('scheduler_processing_time');
            expect(processingTime.value).toBeGreaterThan(0);
        });

        it('deve registrar hits e misses do cache', async () => {
            const message = await scheduler.scheduleMessage(testMessage);
            
            // Primeira busca (miss)
            await scheduler.getMessage(message.id);
            const misses = await metricsManager.getMetric('scheduler_cache_misses');
            expect(misses.value).toBe(1);
            
            // Segunda busca (hit)
            await scheduler.getMessage(message.id);
            const hits = await metricsManager.getMetric('scheduler_cache_hits');
            expect(hits.value).toBe(1);
        });
    });
}); 