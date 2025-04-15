const os = require('os');
const EventEmitter = require('events');
const logManager = require('./logManager');

class MonitoringManager extends EventEmitter {
    constructor() {
        super();
        this.metrics = new Map();
        this.thresholds = new Map();
        this.monitors = new Map();
        this.logger = logManager.getLogger('monitoring');
        this.isMonitoring = false;
    }

    /**
     * Inicializa o sistema de monitoramento
     * @returns {boolean} - true se inicializado com sucesso
     */
    async initialize() {
        try {
            // Configura monitores padrão
            this.setupDefaultMonitors();
            
            // Configura thresholds padrão
            this.setupDefaultThresholds();
            
            this.logger.info('Sistema de monitoramento inicializado');
            return true;
        } catch (error) {
            this.logger.error('Erro ao inicializar sistema de monitoramento:', error);
            throw error;
        }
    }

    /**
     * Configura os monitores padrão do sistema
     */
    setupDefaultMonitors() {
        // Monitor de CPU
        this.addMonitor('cpu_usage', async () => {
            const cpus = os.cpus();
            const totalIdle = cpus.reduce((acc, cpu) => acc + cpu.times.idle, 0);
            const totalTick = cpus.reduce((acc, cpu) => 
                acc + Object.values(cpu.times).reduce((sum, time) => sum + time, 0), 0);
            return ((1 - totalIdle / totalTick) * 100).toFixed(2);
        });

        // Monitor de Memória
        this.addMonitor('memory_usage', async () => {
            const total = os.totalmem();
            const free = os.freemem();
            return ((1 - free / total) * 100).toFixed(2);
        });

        // Monitor de Espaço em Disco
        this.addMonitor('disk_usage', async () => {
            // Implementação básica - em produção usar fs.statfs ou similar
            return 0;
        });

        // Monitor de Carga do Sistema
        this.addMonitor('system_load', async () => {
            const load = os.loadavg();
            return load[0].toFixed(2); // Load médio de 1 minuto
        });
    }

    /**
     * Configura os thresholds padrão
     */
    setupDefaultThresholds() {
        this.setThreshold('cpu_usage', 80); // 80% de uso da CPU
        this.setThreshold('memory_usage', 85); // 85% de uso da memória
        this.setThreshold('disk_usage', 90); // 90% de uso do disco
        this.setThreshold('system_load', 5); // Load average de 5
    }

    /**
     * Adiciona um novo monitor
     * @param {string} name - Nome do monitor
     * @param {Function} callback - Função que retorna o valor monitorado
     */
    addMonitor(name, callback) {
        this.monitors.set(name, callback);
        this.metrics.set(name, null);
    }

    /**
     * Define um threshold para uma métrica
     * @param {string} metric - Nome da métrica
     * @param {number} value - Valor do threshold
     */
    setThreshold(metric, value) {
        this.thresholds.set(metric, value);
    }

    /**
     * Inicia o monitoramento
     * @param {number} interval - Intervalo em ms entre verificações
     */
    startMonitoring(interval = 60000) {
        if (this.isMonitoring) return;

        this.isMonitoring = true;
        this.monitoringInterval = setInterval(async () => {
            try {
                await this.checkMetrics();
            } catch (error) {
                this.logger.error('Erro ao verificar métricas:', error);
            }
        }, interval);

        this.logger.info('Monitoramento iniciado');
    }

    /**
     * Para o monitoramento
     */
    stopMonitoring() {
        if (!this.isMonitoring) return;

        clearInterval(this.monitoringInterval);
        this.isMonitoring = false;
        this.logger.info('Monitoramento parado');
    }

    /**
     * Verifica todas as métricas
     */
    async checkMetrics() {
        for (const [name, monitor] of this.monitors) {
            try {
                const value = await monitor();
                this.metrics.set(name, value);

                // Verifica threshold
                const threshold = this.thresholds.get(name);
                if (threshold && value > threshold) {
                    this.emit('threshold_exceeded', {
                        metric: name,
                        value,
                        threshold
                    });
                    
                    this.logger.warn(`Threshold excedido - ${name}: ${value} (limite: ${threshold})`);
                }

                this.emit('metric_updated', {
                    metric: name,
                    value
                });
            } catch (error) {
                this.logger.error(`Erro ao verificar métrica ${name}:`, error);
            }
        }
    }

    /**
     * Retorna o valor atual de uma métrica
     * @param {string} name - Nome da métrica
     * @returns {number|null} - Valor da métrica ou null se não existir
     */
    getMetric(name) {
        return this.metrics.get(name);
    }

    /**
     * Retorna todas as métricas atuais
     * @returns {Object} - Objeto com todas as métricas
     */
    getAllMetrics() {
        const metrics = {};
        for (const [name, value] of this.metrics) {
            metrics[name] = value;
        }
        return metrics;
    }

    /**
     * Retorna os thresholds configurados
     * @returns {Object} - Objeto com todos os thresholds
     */
    getThresholds() {
        const thresholds = {};
        for (const [name, value] of this.thresholds) {
            thresholds[name] = value;
        }
        return thresholds;
    }
}

module.exports = new MonitoringManager(); 