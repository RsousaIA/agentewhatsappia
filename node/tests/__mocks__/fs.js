const mockStream = {
    write: jest.fn(),
    end: jest.fn(),
    on: jest.fn().mockImplementation(function(event, handler) {
        if (event === 'open') {
            handler();
        }
        return this;
    }),
    once: jest.fn().mockImplementation(function(event, handler) {
        if (event === 'open') {
            handler();
        }
        return this;
    }),
    emit: jest.fn(),
    removeListener: jest.fn(),
    close: jest.fn()
};

const mockFiles = new Map();
const mockDirs = new Set();

const normalizePath = (path) => {
    return path.replace(/\\/g, '/').replace(/\/+/g, '/');
};

module.exports = {
    promises: {
        mkdir: jest.fn().mockImplementation(async (path, options) => {
            const normalizedPath = normalizePath(path);
            mockDirs.add(normalizedPath);
            return undefined;
        }),
        readdir: jest.fn().mockImplementation(async (path) => {
            const normalizedPath = normalizePath(path);
            return Array.from(mockFiles.keys())
                .filter(file => file.startsWith(normalizedPath))
                .map(file => file.split('/').pop());
        }),
        stat: jest.fn().mockImplementation(async (path) => {
            const normalizedPath = normalizePath(path);
            if (mockFiles.has(normalizedPath)) {
                return { size: mockFiles.get(normalizedPath).length, mtime: new Date() };
            }
            if (mockDirs.has(normalizedPath)) {
                return { isDirectory: () => true, mtime: new Date() };
            }
            throw new Error('ENOENT');
        }),
        unlink: jest.fn().mockImplementation(async (path) => {
            const normalizedPath = normalizePath(path);
            mockFiles.delete(normalizedPath);
            return undefined;
        }),
        access: jest.fn().mockImplementation(async (path) => {
            const normalizedPath = normalizePath(path);
            if (!mockFiles.has(normalizedPath) && !mockDirs.has(normalizedPath)) {
                throw new Error('ENOENT');
            }
            return undefined;
        }),
        readFile: jest.fn().mockImplementation(async (path) => {
            const normalizedPath = normalizePath(path);
            if (mockFiles.has(normalizedPath)) {
                return mockFiles.get(normalizedPath);
            }
            throw new Error('ENOENT');
        }),
        writeFile: jest.fn().mockImplementation(async (path, data) => {
            const normalizedPath = normalizePath(path);
            mockFiles.set(normalizedPath, data);
            return undefined;
        }),
        copyFile: jest.fn().mockImplementation(async (src, dest) => {
            const normalizedSrc = normalizePath(src);
            const normalizedDest = normalizePath(dest);
            if (mockFiles.has(normalizedSrc)) {
                mockFiles.set(normalizedDest, mockFiles.get(normalizedSrc));
                return undefined;
            }
            throw new Error('ENOENT');
        }),
        chmod: jest.fn().mockResolvedValue(undefined),
        rmdir: jest.fn().mockImplementation(async (path, options) => {
            const normalizedPath = normalizePath(path);
            mockDirs.delete(normalizedPath);
            
            // Se recursivo, remove todos os arquivos e diretórios abaixo
            if (options && options.recursive) {
                Array.from(mockFiles.keys())
                    .filter(file => file.startsWith(normalizedPath))
                    .forEach(file => mockFiles.delete(file));
                
                Array.from(mockDirs)
                    .filter(dir => dir.startsWith(normalizedPath))
                    .forEach(dir => mockDirs.delete(dir));
            }
            
            return undefined;
        })
    },
    existsSync: jest.fn().mockImplementation((path) => {
        const normalizedPath = normalizePath(path);
        return mockFiles.has(normalizedPath) || mockDirs.has(normalizedPath);
    }),
    createWriteStream: jest.fn().mockReturnValue(mockStream),
    stat: jest.fn((path, callback) => {
        const normalizedPath = normalizePath(path);
        if (mockFiles.has(normalizedPath) || mockDirs.has(normalizedPath)) {
            callback(null, { size: 0 });
        } else {
            callback(new Error('ENOENT'));
        }
    })
}; 