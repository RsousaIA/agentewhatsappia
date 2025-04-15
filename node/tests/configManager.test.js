const configManager = require('../utils/configManager');
const fs = require('fs').promises;
const path = require('path');

// Mock do sistema de arquivos
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn(),
        access: jest.fn(),
        readFile: jest.fn(),
        writeFile: jest.fn()
    }
}));

describe('ConfigManager', () => {
    beforeEach(() => {
        // Limpa o cache de configurações
        configManager.config = {};
        
        // Reseta os mocks
        jest.clearAllMocks();
    });

    describe('initialize', () => {
        it('deve criar diretório de configurações se não existir', async () => {
            fs.access.mockRejectedValue(new Error('Arquivo não encontrado'));

            await configManager.initialize();

            expect(fs.mkdir).toHaveBeenCalledWith(configManager.configPath, {
                recursive: true
            });
        });

        it('deve carregar configurações existentes', async () => {
            const existingConfig = {
                server: {
                    port: 3000
                }
            };
            fs.access.mockResolvedValue();
            fs.readFile.mockResolvedValue(JSON.stringify(existingConfig));

            await configManager.initialize();

            expect(configManager.config).toEqual(existingConfig);
        });
    });

    describe('get', () => {
        beforeEach(async () => {
            configManager.config = {
                server: {
                    port: 3000,
                    host: 'localhost'
                },
                database: {
                    type: 'sqlite'
                }
            };
        });

        it('deve retornar valor de configuração existente', () => {
            const port = configManager.get('server.port');
            expect(port).toBe(3000);
        });

        it('deve retornar valor padrão para configuração inexistente', () => {
            const value = configManager.get('server.timeout', 5000);
            expect(value).toBe(5000);
        });

        it('deve retornar null para configuração inexistente sem valor padrão', () => {
            const value = configManager.get('server.timeout');
            expect(value).toBeNull();
        });
    });

    describe('set', () => {
        beforeEach(async () => {
            configManager.config = {
                server: {
                    port: 3000
                }
            };
        });

        it('deve definir nova configuração', async () => {
            await configManager.set('server.host', 'localhost');

            expect(configManager.config.server.host).toBe('localhost');
            expect(fs.writeFile).toHaveBeenCalled();
        });

        it('deve atualizar configuração existente', async () => {
            await configManager.set('server.port', 4000);

            expect(configManager.config.server.port).toBe(4000);
            expect(fs.writeFile).toHaveBeenCalled();
        });

        it('deve lançar erro ao tentar definir configuração inválida', async () => {
            await expect(configManager.set('server.port', 'invalid'))
                .rejects
                .toThrow('Porta do servidor inválida');
        });
    });

    describe('getAll', () => {
        it('deve retornar todas as configurações', () => {
            const config = {
                server: {
                    port: 3000
                }
            };
            configManager.config = config;

            const allConfig = configManager.getAll();
            expect(allConfig).toEqual(config);
            expect(allConfig).not.toBe(config); // Deve ser uma cópia
        });
    });

    describe('validateConfig', () => {
        it('deve validar configurações corretas', () => {
            const config = {
                server: {
                    port: 3000
                },
                whatsapp: {
                    sessionPath: './sessions'
                },
                logging: {
                    level: 'info'
                },
                security: {
                    jwtSecret: 'secret'
                }
            };

            expect(() => configManager.validateConfig(config)).not.toThrow();
        });

        it('deve lançar erro para porta do servidor inválida', () => {
            const config = {
                server: {
                    port: '3000' // Deve ser número
                }
            };

            expect(() => configManager.validateConfig(config))
                .toThrow('Porta do servidor inválida');
        });

        it('deve lançar erro para caminho de sessão inválido', () => {
            const config = {
                server: {
                    port: 3000
                },
                whatsapp: {
                    // sessionPath não definido
                }
            };

            expect(() => configManager.validateConfig(config))
                .toThrow('Caminho da sessão do WhatsApp inválido');
        });
    });
}); 