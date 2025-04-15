const logger = require('../logger');
const metricsManager = require('./metricsManager');
const fs = require('fs').promises;
const path = require('path');

class MetricsDashboard {
    constructor() {
        this.dashboardPath = path.join(__dirname, '../data/dashboard');
        this.metricsHistory = new Map();
        this.historySize = 100; // Número de pontos de histórico por métrica
        this.initialize();
    }

    async initialize() {
        try {
            // Cria diretório do dashboard
            await fs.mkdir(this.dashboardPath, { recursive: true });
            
            // Carrega histórico de métricas
            await this.loadMetricsHistory();
            
            // Agenda atualização do dashboard
            setInterval(() => this.updateDashboard(), 60000); // Atualiza a cada minuto
            
            logger.info('Dashboard de métricas inicializado');
        } catch (error) {
            logger.error('Erro ao inicializar dashboard de métricas', {
                error: error.message
            });
            throw error;
        }
    }

    async loadMetricsHistory() {
        try {
            const files = await fs.readdir(this.dashboardPath);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    const metricName = file.replace('.json', '');
                    const content = await fs.readFile(
                        path.join(this.dashboardPath, file),
                        'utf8'
                    );
                    this.metricsHistory.set(metricName, JSON.parse(content));
                }
            }
        } catch (error) {
            logger.error('Erro ao carregar histórico de métricas', {
                error: error.message
            });
        }
    }

    async updateDashboard() {
        try {
            const metrics = await metricsManager.getAllMetrics();
            
            for (const [name, metric] of metrics) {
                await this.updateMetricHistory(name, metric);
            }
            
            // Gera relatório
            await this.generateReport();
        } catch (error) {
            logger.error('Erro ao atualizar dashboard', {
                error: error.message
            });
        }
    }

    async updateMetricHistory(name, metric) {
        let history = this.metricsHistory.get(name) || [];
        
        // Adiciona novo ponto
        history.push({
            timestamp: new Date().toISOString(),
            value: metric.value
        });
        
        // Mantém apenas os últimos pontos
        if (history.length > this.historySize) {
            history = history.slice(-this.historySize);
        }
        
        this.metricsHistory.set(name, history);
        
        // Salva no arquivo
        await fs.writeFile(
            path.join(this.dashboardPath, `${name}.json`),
            JSON.stringify(history, null, 2)
        );
    }

    async generateReport() {
        try {
            const report = {
                timestamp: new Date().toISOString(),
                metrics: {}
            };
            
            for (const [name, history] of this.metricsHistory.entries()) {
                const metric = await metricsManager.getMetric(name);
                
                report.metrics[name] = {
                    current: metric.value,
                    history: history,
                    stats: this.calculateStats(history)
                };
            }
            
            // Salva relatório
            await fs.writeFile(
                path.join(this.dashboardPath, 'report.json'),
                JSON.stringify(report, null, 2)
            );
            
            logger.info('Relatório de métricas gerado');
        } catch (error) {
            logger.error('Erro ao gerar relatório', {
                error: error.message
            });
        }
    }

    calculateStats(history) {
        if (history.length === 0) return null;
        
        const values = history.map(h => h.value);
        
        return {
            min: Math.min(...values),
            max: Math.max(...values),
            avg: values.reduce((a, b) => a + b, 0) / values.length,
            last: values[values.length - 1]
        };
    }

    async getMetricHistory(name) {
        return this.metricsHistory.get(name) || [];
    }

    async getMetricStats(name) {
        const history = await this.getMetricHistory(name);
        return this.calculateStats(history);
    }

    async getReport() {
        try {
            const content = await fs.readFile(
                path.join(this.dashboardPath, 'report.json'),
                'utf8'
            );
            return JSON.parse(content);
        } catch (error) {
            logger.error('Erro ao ler relatório', {
                error: error.message
            });
            return null;
        }
    }
}

module.exports = new MetricsDashboard(); 