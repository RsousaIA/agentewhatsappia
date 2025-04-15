module.exports = {
    initialize: jest.fn().mockResolvedValue(undefined),
    updateConfig: jest.fn().mockResolvedValue({ success: true }),
    getConfig: jest.fn().mockReturnValue({ 
        logLevel: 'debug', 
        maxLogSize: 1048576,
        maxLogFiles: 5
    })
}; 