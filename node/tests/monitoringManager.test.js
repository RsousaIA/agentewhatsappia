const monitoringManager = require('../utils/monitoringManager');
const os = require('os');

// Mock do os
jest.mock('os', () => ({
    cpus: jest.fn().mockReturnValue([
        { times: { user: 100, nice: 0, sys: 50, idle: 850, irq: 0 } }
    ]),
    totalmem: jest.fn().mockReturnValue(16000000000), // 16GB
    freemem: jest.fn().mockReturnValue(8000000000),   // 8GB
    loadavg: jest.fn().mockReturnValue([1.5, 1.0, 0.5])
}));

// Mock do logManager
jest.mock('../utils/logManager', () => ({
    getLogger: jest.fn().mockReturnValue({
        info: jest.fn(),
        error: jest.fn(),
        warn: jest.fn()
    })
}));

describe('MonitoringManager', () => {
    beforeEach(async () => {
        jest.clearAllMocks();
        monitoringManager.stopMonitoring();
        await monitoringManager.initialize();
    });

    describe('Inicialização', () => {
        it('deve inicializar com monitores padrão', async () => {
            const metrics = monitoringManager.getAllMetrics();
            expect(Object.keys(metrics)).toEqual([
                'cpu_usage',
                'memory_usage',
                'disk_usage',
                'system_load'
            ]);
        });

        it('deve configurar thresholds padrão', () => {
            const thresholds = monitoringManager.getThresholds();
            expect(thresholds).toEqual({
                cpu_usage: 80,
                memory_usage: 85,
                disk_usage: 90,
                system_load: 5
            });
        });
    });

    describe('Monitoramento', () => {
        it('deve iniciar e parar monitoramento', () => {
            monitoringManager.startMonitoring(1000);
            expect(monitoringManager.isMonitoring).toBe(true);

            monitoringManager.stopMonitoring();
            expect(monitoringManager.isMonitoring).toBe(false);
        });

        it('deve coletar métricas corretamente', async () => {
            await monitoringManager.checkMetrics();
            const metrics = monitoringManager.getAllMetrics();

            expect(parseFloat(metrics.cpu_usage)).toBeLessThanOrEqual(100);
            expect(parseFloat(metrics.memory_usage)).toBeLessThanOrEqual(100);
            expect(parseFloat(metrics.system_load)).toBe(1.5);
        });

        it('deve emitir evento quando threshold é excedido', async () => {
            expect.assertions(3);
            
            // Configura um monitor de teste que sempre retorna um valor alto
            monitoringManager.addMonitor('test_threshold', async () => 100);
            monitoringManager.setThreshold('test_threshold', 50);

            // Configura o listener antes de verificar as métricas
            const eventPromise = new Promise(resolve => {
                monitoringManager.once('threshold_exceeded', data => {
                    expect(data.metric).toBe('test_threshold');
                    expect(data.value).toBe(100);
                    expect(data.threshold).toBe(50);
                    resolve();
                });
            });

            // Executa a verificação e aguarda o evento
            await monitoringManager.checkMetrics();
            await eventPromise;
        });

        it('deve emitir evento quando métrica é atualizada', (done) => {
            monitoringManager.once('metric_updated', (data) => {
                expect(data.metric).toBe('cpu_usage');
                expect(parseFloat(data.value)).toBeLessThanOrEqual(100);
                done();
            });

            monitoringManager.checkMetrics();
        });
    });

    describe('Gerenciamento de Monitores', () => {
        it('deve adicionar novo monitor', () => {
            monitoringManager.addMonitor('test_metric', async () => 42);
            expect(monitoringManager.getMetric('test_metric')).toBeNull();
        });

        it('deve atualizar valor do monitor após verificação', async () => {
            monitoringManager.addMonitor('test_metric', async () => 42);
            await monitoringManager.checkMetrics();
            expect(monitoringManager.getMetric('test_metric')).toBe(42);
        });
    });

    describe('Gerenciamento de Thresholds', () => {
        it('deve definir novo threshold', () => {
            monitoringManager.setThreshold('test_metric', 50);
            const thresholds = monitoringManager.getThresholds();
            expect(thresholds.test_metric).toBe(50);
        });

        it('deve atualizar threshold existente', () => {
            monitoringManager.setThreshold('cpu_usage', 95);
            const thresholds = monitoringManager.getThresholds();
            expect(thresholds.cpu_usage).toBe(95);
        });
    });

    describe('Recuperação de Métricas', () => {
        it('deve retornar métrica específica', async () => {
            await monitoringManager.checkMetrics();
            const cpuUsage = monitoringManager.getMetric('cpu_usage');
            expect(parseFloat(cpuUsage)).toBeLessThanOrEqual(100);
        });

        it('deve retornar undefined para métrica inexistente', () => {
            const value = monitoringManager.getMetric('invalid_metric');
            expect(value).toBeUndefined();
        });

        it('deve retornar todas as métricas', async () => {
            await monitoringManager.checkMetrics();
            const metrics = monitoringManager.getAllMetrics();
            
            expect(metrics).toHaveProperty('cpu_usage');
            expect(metrics).toHaveProperty('memory_usage');
            expect(metrics).toHaveProperty('disk_usage');
            expect(metrics).toHaveProperty('system_load');
        });
    });
}); 