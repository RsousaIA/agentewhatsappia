const EventEmitter = require('events');

class QueueManagerMock extends EventEmitter {
    constructor() {
        super();
        this.queues = new Map();
    }

    async initialize() {
        return Promise.resolve();
    }

    async enqueue(queueName, message) {
        if (!this.queues.has(queueName)) {
            this.queues.set(queueName, []);
        }
        this.queues.get(queueName).push(message);
        return { success: true, queueName, messageId: message.id };
    }

    async dequeue(queueName) {
        if (!this.queues.has(queueName) || this.queues.get(queueName).length === 0) {
            return null;
        }
        return this.queues.get(queueName).shift();
    }

    getQueueSize(queueName) {
        if (!this.queues.has(queueName)) {
            return 0;
        }
        return this.queues.get(queueName).length;
    }
}

module.exports = new QueueManagerMock(); 