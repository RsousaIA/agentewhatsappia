const mockTransport = {
    log: jest.fn(),
    close: jest.fn(),
    _destroy: jest.fn()
};

const printf = jest.fn().mockImplementation(({ level, message, timestamp, ...metadata }) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    if (Object.keys(metadata).length > 0) {
        msg += ` ${JSON.stringify(metadata)}`;
    }
    return msg;
});

const createLogger = jest.fn().mockReturnValue({
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
    add: jest.fn(),
    transports: [mockTransport]
});

module.exports = {
    format: {
        combine: jest.fn(),
        timestamp: jest.fn(),
        json: jest.fn(),
        colorize: jest.fn(),
        simple: jest.fn(),
        printf
    },
    transports: {
        File: jest.fn().mockReturnValue(mockTransport),
        Console: jest.fn().mockReturnValue(mockTransport)
    },
    createLogger
}; 