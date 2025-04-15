const queueManager = require('../utils/queueManager');

describe('QueueManager', () => {
    beforeEach(() => {
        // Limpa todas as filas antes de cada teste
        queueManager.clearQueue('testQueue');
    });

    describe('Validação de Mensagens', () => {
        it('deve rejeitar mensagem inválida', async () => {
            await expect(queueManager.enqueue('testQueue', null))
                .rejects.toThrow('Mensagem inválida: deve ser um objeto');
            
            await expect(queueManager.enqueue('testQueue', {}))
                .rejects.toThrow('Mensagem inválida: ID é obrigatório');
        });

        it('deve rejeitar mensagem duplicada', async () => {
            const message = { id: '1', content: 'test' };
            await queueManager.enqueue('testQueue', message);
            
            await expect(queueManager.enqueue('testQueue', message))
                .rejects.toThrow('Mensagem duplicada: ID já existe');
        });
    });

    describe('Limite de Fila', () => {
        it('deve rejeitar mensagem quando a fila está cheia', async () => {
            // Preenche a fila até o limite
            for (let i = 0; i < queueManager.maxQueueSize; i++) {
                await queueManager.enqueue('testQueue', { id: `msg-${i}`, content: 'test' });
            }

            await expect(queueManager.enqueue('testQueue', { id: 'overflow', content: 'test' }))
                .rejects.toThrow(`Fila testQueue está cheia. Limite: ${queueManager.maxQueueSize} mensagens`);
        });
    });

    describe('Enfileiramento', () => {
        it('deve adicionar mensagem à fila', async () => {
            const message = { id: '1', content: 'test' };
            await queueManager.enqueue('testQueue', message);
            
            const stats = queueManager.getQueueStats('testQueue');
            expect(stats.size).toBe(1);
            expect(stats.uniqueMessages).toBe(1);
        });

        it('deve respeitar prioridade das mensagens', async () => {
            const messages = [
                { id: '1', content: 'normal' },
                { id: '2', content: 'high', priority: 1 },
                { id: '3', content: 'normal2' }
            ];

            await queueManager.enqueue('testQueue', messages[0]);
            await queueManager.enqueue('testQueue', messages[1], 1);
            await queueManager.enqueue('testQueue', messages[2]);

            const stats = queueManager.getQueueStats('testQueue');
            expect(stats.size).toBe(3);
        });
    });

    describe('Processamento', () => {
        it('deve processar mensagens em ordem', async () => {
            const messages = [];
            const message = { id: '1', content: 'test' };

            queueManager.on('process', (data) => {
                messages.push(data.message);
                queueManager.notifyProcessed('testQueue', data.message.id);
            });

            await queueManager.enqueue('testQueue', message);
            
            await new Promise(resolve => setTimeout(resolve, 100));

            expect(messages.length).toBe(1);
            expect(messages[0].id).toBe('1');
        });

        it('deve retentar mensagens com falha', async () => {
            const message = { id: '1', content: 'test' };
            let processCount = 0;

            queueManager.on('process', (data) => {
                processCount++;
                if (processCount < 2) {
                    queueManager.emit('processed', { error: new Error('Test error') });
                } else {
                    queueManager.notifyProcessed('testQueue', data.message.id);
                }
            });

            await queueManager.enqueue('testQueue', message);
            
            await new Promise(resolve => setTimeout(resolve, 1000));

            expect(processCount).toBe(2);
        });

        it('deve respeitar máximo de retentativas', async () => {
            const message = { id: '1', content: 'test' };
            let failed = false;

            queueManager.on('failed', () => {
                failed = true;
            });

            queueManager.on('process', () => {
                queueManager.emit('processed', { error: new Error('Test error') });
            });

            await queueManager.enqueue('testQueue', message);
            
            await new Promise(resolve => setTimeout(resolve, 2000));

            expect(failed).toBe(true);
        });

        it('deve lidar com timeout no processamento', async () => {
            const message = { id: '1', content: 'test' };
            let failed = false;

            queueManager.on('failed', () => {
                failed = true;
            });

            queueManager.on('process', () => {
                // Não emite evento de processado, causando timeout
            });

            await queueManager.enqueue('testQueue', message);
            
            await new Promise(resolve => setTimeout(resolve, queueManager.processingTimeout + 1000));

            expect(failed).toBe(true);
        });
    });

    describe('Estatísticas', () => {
        it('deve retornar estatísticas corretas da fila', async () => {
            const message = { id: '1', content: 'test' };
            await queueManager.enqueue('testQueue', message);

            const stats = queueManager.getQueueStats('testQueue');
            expect(stats).toEqual({
                queueName: 'testQueue',
                size: 1,
                processing: false,
                messagesInRetry: 0,
                nextRetryTimestamp: expect.any(Number),
                maxSize: queueManager.maxQueueSize,
                uniqueMessages: 1
            });
        });

        it('deve retornar null para fila inexistente', () => {
            const stats = queueManager.getQueueStats('nonExistentQueue');
            expect(stats).toBeNull();
        });
    });

    describe('Limpeza', () => {
        it('deve limpar todas as mensagens da fila', async () => {
            const message = { id: '1', content: 'test' };
            await queueManager.enqueue('testQueue', message);
            
            queueManager.clearQueue('testQueue');
            
            const stats = queueManager.getQueueStats('testQueue');
            expect(stats.size).toBe(0);
            expect(stats.uniqueMessages).toBe(0);
        });
    });
}); 