const util = require('util');

module.exports = {
    gzip: jest.fn((data, callback) => callback(null, Buffer.from('compressed'))),
    gunzip: jest.fn((data, callback) => callback(null, Buffer.from('decompressed'))),
    // Versões promisificadas para facilitar testes
    gzipPromise: util.promisify((data, callback) => callback(null, Buffer.from('compressed'))),
    gunzipPromise: util.promisify((data, callback) => callback(null, Buffer.from('decompressed')))
}; 