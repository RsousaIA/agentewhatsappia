const metricsManager = require('../utils/metricsManager');
const fs = require('fs').promises;
const path = require('path');
const monitoringManager = require('../utils/monitoringManager');
const logManager = require('../utils/logManager');

// Mock do sistema de arquivos
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn(),
        readdir: jest.fn(),
        readFile: jest.fn(),
        writeFile: jest.fn()
    }
}));

// Mock do logManager
jest.mock('../utils/logManager', () => ({
    getLogger: jest.fn().mockReturnValue({
        info: jest.fn(),
        error: jest.fn()
    })
}));

// Mock do monitoringManager
jest.mock('../utils/monitoringManager', () => ({
    addMonitor: jest.fn(),
    setThreshold: jest.fn()
}));

describe('MetricsManager', () => {
    beforeEach(() => {
        // Limpa os mocks antes de cada teste
        jest.clearAllMocks();
        metricsManager.reset();
    });

    describe('Inicialização', () => {
        it('deve inicializar com métricas padrão', async () => {
            await metricsManager.initialize();
            
            const metrics = metricsManager.getAllMetrics();
            expect(Object.keys(metrics)).toEqual([
                'messages_processed',
                'messages_failed',
                'messages_queued',
                'processing_time',
                'queue_wait_time',
                'error_count',
                'error_rate',
                'memory_usage',
                'active_connections'
            ]);
        });

        it('deve registrar métricas no sistema de monitoramento', async () => {
            await metricsManager.initialize();
            
            expect(monitoringManager.addMonitor).toHaveBeenCalledTimes(8);
            expect(monitoringManager.setThreshold).toHaveBeenCalledTimes(3);
        });
    });

    describe('Gerenciamento de Métricas', () => {
        beforeEach(async () => {
            await metricsManager.initialize();
        });

        it('deve adicionar nova métrica', () => {
            metricsManager.addMetric('test_metric', 'counter', 'Métrica de teste');
            const metric = metricsManager.getMetric('test_metric');
            
            expect(metric.type).toBe('counter');
            expect(metric.value).toBe(0);
            expect(metric.description).toBe('Métrica de teste');
        });

        it('deve incrementar métrica do tipo counter', () => {
            metricsManager.addMetric('test_counter', 'counter', 'Teste');
            metricsManager.increment('test_counter', 5);
            
            const metric = metricsManager.getMetric('test_counter');
            expect(metric.value).toBe(5);
        });

        it('deve definir valor de métrica do tipo gauge', () => {
            metricsManager.addMetric('test_gauge', 'gauge', 'Teste');
            metricsManager.set('test_gauge', 42);
            
            const metric = metricsManager.getMetric('test_gauge');
            expect(metric.value).toBe(42);
        });

        it('deve observar valores em métrica do tipo histogram', () => {
            metricsManager.addMetric('test_histogram', 'histogram', 'Teste');
            
            metricsManager.observe('test_histogram', 10);
            metricsManager.observe('test_histogram', 20);
            metricsManager.observe('test_histogram', 30);
            
            const metric = metricsManager.getMetric('test_histogram');
            expect(metric.value).toEqual({
                count: 3,
                sum: 60,
                min: 10,
                max: 30,
                avg: 20
            });
        });

        it('deve manter histórico limitado para histogram', () => {
            metricsManager.addMetric('test_histogram', 'histogram', 'Teste');
            
            // Adiciona mais valores que o limite
            for (let i = 0; i < 150; i++) {
                metricsManager.observe('test_histogram', i);
            }
            
            const history = metricsManager.getHistory('test_histogram');
            expect(history.length).toBe(100);
        });
    });

    describe('Validação de Tipos', () => {
        beforeEach(async () => {
            await metricsManager.initialize();
        });

        it('deve lançar erro ao incrementar métrica não counter', () => {
            metricsManager.addMetric('test_gauge', 'gauge', 'Teste');
            expect(() => metricsManager.increment('test_gauge')).toThrow();
        });

        it('deve lançar erro ao definir valor em métrica não gauge', () => {
            metricsManager.addMetric('test_counter', 'counter', 'Teste');
            expect(() => metricsManager.set('test_counter', 42)).toThrow();
        });

        it('deve lançar erro ao observar valor em métrica não histogram', () => {
            metricsManager.addMetric('test_gauge', 'gauge', 'Teste');
            expect(() => metricsManager.observe('test_gauge', 42)).toThrow();
        });
    });

    describe('Eventos', () => {
        it('deve emitir evento ao atualizar métrica', () => {
            const callback = jest.fn();
            metricsManager.on('metric_updated', callback);
            
            metricsManager.addMetric('test_metric', 'counter', 'Teste');
            metricsManager.increment('test_metric');
            
            expect(callback).toHaveBeenCalledWith({
                name: 'test_metric',
                value: 1
            });
        });
    });

    describe('Reset', () => {
        it('deve resetar todas as métricas', async () => {
            await metricsManager.initialize();
            
            // Modifica algumas métricas
            metricsManager.increment('messages_processed', 10);
            metricsManager.set('messages_queued', 5);
            metricsManager.observe('processing_time', 100);
            
            metricsManager.reset();
            
            const metrics = metricsManager.getAllMetrics();
            expect(metrics.messages_processed.value).toBe(0);
            expect(metrics.messages_queued.value).toBe(0);
            expect(metrics.processing_time.value).toEqual({
                count: 0,
                sum: 0,
                min: Infinity,
                max: -Infinity,
                avg: 0
            });
        });
    });

    describe('recordMetric', () => {
        it('deve registrar uma nova métrica com sucesso', async () => {
            const metricData = {
                type: 'response_time',
                value: 150,
                tags: ['api', 'whatsapp']
            };

            await metricsManager.recordMetric(metricData);

            expect(metricsManager.metrics.size).toBe(1);
            const recordedMetric = Array.from(metricsManager.metrics.values())[0];
            expect(recordedMetric.type).toBe(metricData.type);
            expect(recordedMetric.value).toBe(metricData.value);
            expect(recordedMetric.tags).toEqual(metricData.tags);
            expect(recordedMetric.id).toBeDefined();
            expect(recordedMetric.timestamp).toBeDefined();
        });

        it('deve lançar erro se os dados da métrica forem inválidos', async () => {
            const metricData = {
                // type não definido
                value: 150
            };

            await expect(metricsManager.recordMetric(metricData))
                .rejects
                .toThrow('Tipo da métrica é obrigatório');
        });
    });

    describe('generateReport', () => {
        beforeEach(async () => {
            // Registra algumas métricas para teste
            await metricsManager.recordMetric({
                type: 'response_time',
                value: 150,
                tags: ['api']
            });

            await metricsManager.recordMetric({
                type: 'response_time',
                value: 200,
                tags: ['api']
            });

            await metricsManager.recordMetric({
                type: 'message_count',
                value: 1,
                tags: ['whatsapp']
            });
        });

        it('deve gerar relatório sem filtros', async () => {
            const report = await metricsManager.generateReport();

            expect(report.id).toBeDefined();
            expect(report.generatedAt).toBeDefined();
            expect(report.statistics).toBeDefined();
            expect(report.metrics).toBeDefined();

            // Verifica estatísticas
            expect(report.statistics.response_time).toBeDefined();
            expect(report.statistics.response_time.count).toBe(2);
            expect(report.statistics.response_time.average).toBe(175);
            expect(report.statistics.response_time.min).toBe(150);
            expect(report.statistics.response_time.max).toBe(200);

            expect(report.statistics.message_count).toBeDefined();
            expect(report.statistics.message_count.count).toBe(1);
        });

        it('deve gerar relatório com filtros', async () => {
            const startDate = new Date(Date.now() - 3600000).toISOString();
            const endDate = new Date().toISOString();

            const report = await metricsManager.generateReport({
                startDate,
                endDate,
                type: 'response_time'
            });

            expect(report.filters.startDate).toBe(startDate);
            expect(report.filters.endDate).toBe(endDate);
            expect(report.filters.type).toBe('response_time');
            expect(report.statistics.response_time).toBeDefined();
            expect(report.statistics.message_count).toBeUndefined();
        });
    });

    describe('exportReport', () => {
        it('deve exportar relatório para JSON', async () => {
            const report = await metricsManager.generateReport();
            const exportPath = await metricsManager.exportReport(report, 'json');

            expect(exportPath).toContain('.json');
        });

        it('deve exportar relatório para CSV', async () => {
            const report = await metricsManager.generateReport();
            const exportPath = await metricsManager.exportReport(report, 'csv');

            expect(exportPath).toContain('.csv');
        });

        it('deve lançar erro para formato não suportado', async () => {
            const report = await metricsManager.generateReport();

            await expect(metricsManager.exportReport(report, 'xml'))
                .rejects
                .toThrow('Formato de exportação não suportado');
        });
    });
}); 