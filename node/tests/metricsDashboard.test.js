const metricsDashboard = require('../utils/metricsDashboard');
const metricsManager = require('../utils/metricsManager');
const fs = require('fs').promises;
const path = require('path');

describe('MetricsDashboard', () => {
    const testMetric = {
        name: 'test_metric',
        type: 'counter',
        value: 10
    };

    beforeEach(async () => {
        // Limpa diretório do dashboard
        try {
            await fs.rm(metricsDashboard.dashboardPath, { recursive: true });
        } catch (error) {
            // Ignora erro se diretório não existir
        }
        
        // Limpa métricas
        await metricsManager.reset();
        
        // Adiciona métrica de teste
        await metricsManager.addMetric(testMetric.name, testMetric.type, 'Test metric');
        await metricsManager.increment(testMetric.name, testMetric.value);
    });

    describe('Histórico de Métricas', () => {
        it('deve atualizar histórico de métrica', async () => {
            await metricsDashboard.updateMetricHistory(testMetric.name, testMetric);
            
            const history = await metricsDashboard.getMetricHistory(testMetric.name);
            expect(history.length).toBe(1);
            expect(history[0].value).toBe(testMetric.value);
        });

        it('deve limitar tamanho do histórico', async () => {
            // Adiciona mais pontos que o limite
            for (let i = 0; i < metricsDashboard.historySize + 10; i++) {
                await metricsDashboard.updateMetricHistory(testMetric.name, {
                    ...testMetric,
                    value: i
                });
            }
            
            const history = await metricsDashboard.getMetricHistory(testMetric.name);
            expect(history.length).toBe(metricsDashboard.historySize);
        });
    });

    describe('Estatísticas', () => {
        it('deve calcular estatísticas corretamente', async () => {
            // Adiciona pontos de teste
            const points = [5, 10, 15, 20, 25];
            for (const value of points) {
                await metricsDashboard.updateMetricHistory(testMetric.name, {
                    ...testMetric,
                    value
                });
            }
            
            const stats = await metricsDashboard.getMetricStats(testMetric.name);
            
            expect(stats.min).toBe(5);
            expect(stats.max).toBe(25);
            expect(stats.avg).toBe(15);
            expect(stats.last).toBe(25);
        });

        it('deve retornar null para histórico vazio', async () => {
            const stats = await metricsDashboard.getMetricStats('non_existent_metric');
            expect(stats).toBeNull();
        });
    });

    describe('Relatório', () => {
        it('deve gerar relatório completo', async () => {
            // Adiciona pontos de teste
            await metricsDashboard.updateMetricHistory(testMetric.name, testMetric);
            
            // Gera relatório
            await metricsDashboard.generateReport();
            
            const report = await metricsDashboard.getReport();
            
            expect(report).toBeDefined();
            expect(report.metrics[testMetric.name]).toBeDefined();
            expect(report.metrics[testMetric.name].current).toBe(testMetric.value);
            expect(report.metrics[testMetric.name].history.length).toBe(1);
            expect(report.metrics[testMetric.name].stats).toBeDefined();
        });

        it('deve lidar com erro ao gerar relatório', async () => {
            // Simula erro ao gerar relatório
            jest.spyOn(fs, 'writeFile').mockRejectedValueOnce(new Error('Write failed'));
            
            await metricsDashboard.generateReport();
            
            // Verifica se o erro foi registrado
            expect(console.error).toHaveBeenCalled();
        });
    });
}); 