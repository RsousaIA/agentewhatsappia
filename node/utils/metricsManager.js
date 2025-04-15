const EventEmitter = require('events');
const logManager = require('./logManager');
const monitoringManager = require('./monitoringManager');

class MetricsManager extends EventEmitter {
    constructor() {
        super();
        this.metrics = new Map();
        this.histories = new Map();
        this.logger = logManager.getLogger('metrics');
    }

    async initialize() {
        try {
            // Métricas padrão
            this.addMetric('messages_processed', 'counter', 'Total de mensagens processadas');
            this.addMetric('messages_failed', 'counter', 'Total de mensagens com falha');
            this.addMetric('messages_queued', 'gauge', 'Mensagens na fila');
            this.addMetric('processing_time', 'histogram', 'Tempo de processamento');
            this.addMetric('queue_wait_time', 'histogram', 'Tempo de espera na fila');
            this.addMetric('error_count', 'counter', 'Total de erros');
            this.addMetric('error_rate', 'gauge', 'Taxa de erros');
            this.addMetric('memory_usage', 'gauge', 'Uso de memória');
            this.addMetric('active_connections', 'gauge', 'Conexões ativas');

            // Registra métricas no sistema de monitoramento
            this.registerMetricsWithMonitoring();

            this.logger.info('MetricsManager inicializado com sucesso');
        } catch (error) {
            this.logger.error('Erro ao inicializar MetricsManager:', error);
            throw error;
        }
    }

    registerMetricsWithMonitoring() {
        // Registra métricas importantes para monitoramento
        const metricsToMonitor = [
            'messages_processed',
            'messages_failed',
            'messages_queued',
            'processing_time',
            'queue_wait_time',
            'error_count',
            'error_rate',
            'memory_usage'
        ];

        metricsToMonitor.forEach(metric => {
            monitoringManager.addMonitor(metric, () => this.getMetric(metric).value);
        });

        // Define thresholds para alertas
        monitoringManager.setThreshold('error_rate', 0.1, 'high');
        monitoringManager.setThreshold('memory_usage', 90, 'high');
        monitoringManager.setThreshold('messages_queued', 1000, 'high');
    }

    addMetric(name, type, description) {
        if (this.metrics.has(name)) {
            throw new Error(`Métrica ${name} já existe`);
        }

        const metric = {
            type,
            value: type === 'histogram' ? { count: 0, sum: 0, min: Infinity, max: -Infinity, avg: 0 } : 0,
            description,
            lastUpdate: Date.now()
        };

        this.metrics.set(name, metric);
        if (type === 'histogram') {
            this.histories.set(name, []);
        }
    }

    getMetric(name) {
        const metric = this.metrics.get(name);
        if (!metric) {
            throw new Error(`Métrica ${name} não encontrada`);
        }
        return metric;
    }

    getAllMetrics() {
        return Object.fromEntries(this.metrics);
    }

    increment(name, value = 1) {
        const metric = this.getMetric(name);
        if (metric.type !== 'counter') {
            throw new Error(`Operação increment não permitida para métrica do tipo ${metric.type}`);
        }

        metric.value += value;
        metric.lastUpdate = Date.now();
        this.emit('metric_updated', { name, value: metric.value });
    }

    set(name, value) {
        const metric = this.getMetric(name);
        if (metric.type !== 'gauge') {
            throw new Error(`Operação set não permitida para métrica do tipo ${metric.type}`);
        }

        metric.value = value;
        metric.lastUpdate = Date.now();
        this.emit('metric_updated', { name, value });
    }

    observe(name, value) {
        const metric = this.getMetric(name);
        if (metric.type !== 'histogram') {
            throw new Error(`Operação observe não permitida para métrica do tipo ${metric.type}`);
        }

        // Atualiza estatísticas
        metric.value.count++;
        metric.value.sum += value;
        metric.value.min = Math.min(metric.value.min, value);
        metric.value.max = Math.max(metric.value.max, value);
        metric.value.avg = metric.value.sum / metric.value.count;

        // Adiciona ao histórico
        const history = this.histories.get(name);
        history.push({
            value,
            timestamp: Date.now()
        });

        // Mantém apenas os últimos 100 valores
        if (history.length > 100) {
            history.shift();
        }

        metric.lastUpdate = Date.now();
        this.emit('metric_updated', { name, value: metric.value });
    }

    getHistory(name) {
        if (!this.histories.has(name)) {
            throw new Error(`Histórico não disponível para métrica ${name}`);
        }
        return this.histories.get(name);
    }

    reset() {
        this.metrics.forEach((metric, name) => {
            if (metric.type === 'histogram') {
                metric.value = { count: 0, sum: 0, min: Infinity, max: -Infinity, avg: 0 };
                this.histories.set(name, []);
            } else {
                metric.value = 0;
            }
            metric.lastUpdate = Date.now();
        });
    }
}

module.exports = new MetricsManager(); 