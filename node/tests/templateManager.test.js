const templateManager = require('../utils/templateManager');
const fs = require('fs').promises;
const path = require('path');

// Mock do sistema de arquivos
jest.mock('fs', () => ({
    promises: {
        mkdir: jest.fn(),
        readdir: jest.fn(),
        readFile: jest.fn(),
        writeFile: jest.fn(),
        unlink: jest.fn()
    }
}));

describe('TemplateManager', () => {
    beforeEach(() => {
        // Limpa o cache de templates
        templateManager.templates.clear();
        templateManager.categories.clear();
        templateManager.renderedCache.clear();
        
        // Reseta os mocks
        jest.clearAllMocks();
    });

    describe('Inicialização', () => {
        it('deve criar diretórios necessários', async () => {
            await templateManager.initialize();
            
            expect(fs.mkdir).toHaveBeenCalledWith(templateManager.templatePath, { recursive: true });
            expect(fs.mkdir).toHaveBeenCalledWith(templateManager.backupPath, { recursive: true });
        });

        it('deve ignorar templates com tamanho excedido', async () => {
            const largeContent = 'a'.repeat(templateManager.maxTemplateSize + 1);
            fs.readFile.mockResolvedValueOnce(largeContent);
            
            await templateManager.loadTemplates();
            
            expect(templateManager.templates.size).toBe(0);
        });

        it('deve ignorar templates com estrutura inválida', async () => {
            const invalidTemplate = JSON.stringify({ id: '1' }); // Faltando campos obrigatórios
            fs.readFile.mockResolvedValueOnce(invalidTemplate);
            
            await templateManager.loadTemplates();
            
            expect(templateManager.templates.size).toBe(0);
        });
    });

    describe('Validação de Templates', () => {
        it('deve rejeitar template duplicado', async () => {
            const template = {
                name: 'Template Duplicado',
                content: 'Conteúdo duplicado',
                variables: []
            };
            
            await templateManager.createTemplate(template);
            
            await expect(templateManager.createTemplate(template))
                .rejects
                .toThrow('Template com conteúdo similar já existe');
        });

        it('deve validar estrutura do template', () => {
            const validTemplate = {
                id: '1',
                name: 'Teste',
                content: 'Conteúdo',
                version: 1,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            
            expect(templateManager.isValidTemplateStructure(validTemplate)).toBe(true);
            
            const invalidTemplate = { id: '1' };
            expect(templateManager.isValidTemplateStructure(invalidTemplate)).toBe(false);
        });
    });

    describe('Backup e Restauração', () => {
        it('deve criar backup ao salvar template', async () => {
            const template = {
                name: 'Template com Backup',
                content: 'Conteúdo',
                variables: []
            };
            
            await templateManager.createTemplate(template);
            
            expect(fs.writeFile).toHaveBeenCalledTimes(2); // Uma vez para o template, outra para o backup
        });

        it('deve restaurar template do backup em caso de erro', async () => {
            const template = {
                id: '1',
                name: 'Template para Restaurar',
                content: 'Conteúdo',
                variables: []
            };
            
            // Simula erro ao carregar template
            fs.readFile.mockRejectedValueOnce(new Error('Erro de leitura'));
            
            // Configura backup disponível
            fs.readdir.mockResolvedValueOnce(['1_1234567890.json']);
            fs.readFile.mockResolvedValueOnce(JSON.stringify(template));
            
            await templateManager.loadTemplates();
            
            expect(templateManager.templates.size).toBe(1);
            expect(templateManager.templates.get('1')).toEqual(template);
        });
    });

    describe('Cache de Renderização', () => {
        it('deve usar cache para templates renderizados', async () => {
            const template = {
                name: 'Template com Cache',
                content: 'Olá {{nome}}',
                variables: ['nome']
            };
            
            const createdTemplate = await templateManager.createTemplate(template);
            
            // Primeira renderização
            const firstRender = templateManager.renderTemplate(createdTemplate.id, { nome: 'João' });
            
            // Segunda renderização deve usar cache
            const secondRender = templateManager.renderTemplate(createdTemplate.id, { nome: 'João' });
            
            expect(firstRender).toBe(secondRender);
            expect(templateManager.renderedCache.size).toBe(1);
        });

        it('deve limpar cache expirado', async () => {
            const template = {
                name: 'Template com Cache Expirado',
                content: 'Teste',
                variables: []
            };
            
            const createdTemplate = await templateManager.createTemplate(template);
            
            // Renderiza e força expiração do cache
            templateManager.renderTemplate(createdTemplate.id, {});
            const cacheKey = templateManager.generateCacheKey(createdTemplate.id, {});
            templateManager.renderedCache.get(cacheKey).timestamp = Date.now() - templateManager.cacheTTL - 1;
            
            templateManager.clearExpiredCache();
            
            expect(templateManager.renderedCache.size).toBe(0);
        });
    });

    describe('Operações Básicas', () => {
        it('deve criar um novo template com sucesso', async () => {
            const template = {
                name: 'Template de Boas-vindas',
                content: 'Olá {{nome}}, bem-vindo!',
                variables: ['nome'],
                category: 'boas-vindas'
            };

            await templateManager.createTemplate(template);

            expect(templateManager.templates.size).toBe(1);
            const savedTemplate = Array.from(templateManager.templates.values())[0];
            expect(savedTemplate.name).toBe(template.name);
            expect(savedTemplate.content).toBe(template.content);
            expect(savedTemplate.variables).toEqual(template.variables);
            expect(savedTemplate.category).toBe(template.category);
            expect(savedTemplate.version).toBe(1);
            expect(savedTemplate.id).toBeDefined();
            expect(savedTemplate.createdAt).toBeDefined();
            expect(savedTemplate.updatedAt).toBeDefined();
        });

        it('deve atualizar um template existente', async () => {
            const template = {
                name: 'Template Original',
                content: 'Olá {{nome}}',
                variables: ['nome']
            };
            const createdTemplate = await templateManager.createTemplate(template);

            const updates = {
                name: 'Template Atualizado',
                content: 'Olá {{nome}}, tudo bem?'
            };
            const updatedTemplate = await templateManager.updateTemplate(
                createdTemplate.id,
                updates
            );

            expect(updatedTemplate.name).toBe(updates.name);
            expect(updatedTemplate.content).toBe(updates.content);
            expect(updatedTemplate.version).toBe(2);
        });

        it('deve remover um template existente', async () => {
            const template = {
                name: 'Template para Remover',
                content: 'Conteúdo',
                variables: []
            };
            const createdTemplate = await templateManager.createTemplate(template);

            await templateManager.deleteTemplate(createdTemplate.id);

            expect(templateManager.templates.size).toBe(0);
        });
    });

    describe('getTemplate', () => {
        it('deve retornar um template existente', async () => {
            // Cria um template
            const template = {
                name: 'Template para Buscar',
                content: 'Conteúdo',
                variables: []
            };
            const createdTemplate = await templateManager.createTemplate(template);

            // Busca o template
            const foundTemplate = templateManager.getTemplate(createdTemplate.id);

            expect(foundTemplate).toEqual(createdTemplate);
        });

        it('deve lançar erro ao buscar template inexistente', () => {
            expect(() => templateManager.getTemplate('id-inexistente'))
                .toThrow('Template não encontrado');
        });
    });

    describe('listTemplates', () => {
        beforeEach(async () => {
            // Cria alguns templates para teste
            await templateManager.createTemplate({
                name: 'Template 1',
                content: 'Conteúdo 1',
                variables: [],
                category: 'categoria1'
            });

            await templateManager.createTemplate({
                name: 'Template 2',
                content: 'Conteúdo 2',
                variables: [],
                category: 'categoria2'
            });

            await templateManager.createTemplate({
                name: 'Outro Template',
                content: 'Conteúdo 3',
                variables: [],
                category: 'categoria1'
            });
        });

        it('deve listar todos os templates sem filtros', () => {
            const templates = templateManager.listTemplates();
            expect(templates.length).toBe(3);
        });

        it('deve filtrar templates por categoria', () => {
            const templates = templateManager.listTemplates({ category: 'categoria1' });
            expect(templates.length).toBe(2);
            expect(templates.every(t => t.category === 'categoria1')).toBe(true);
        });

        it('deve filtrar templates por busca', () => {
            const templates = templateManager.listTemplates({ search: 'Template' });
            expect(templates.length).toBe(2);
            expect(templates.every(t => t.name.includes('Template'))).toBe(true);
        });
    });

    describe('renderTemplate', () => {
        it('deve renderizar um template com variáveis', async () => {
            // Cria um template
            const template = {
                name: 'Template de Renderização',
                content: 'Olá {{nome}}, sua idade é {{idade}}',
                variables: ['nome', 'idade']
            };
            const createdTemplate = await templateManager.createTemplate(template);

            // Renderiza o template
            const rendered = templateManager.renderTemplate(createdTemplate.id, {
                nome: 'João',
                idade: '25'
            });

            expect(rendered).toBe('Olá João, sua idade é 25');
        });

        it('deve lançar erro se faltar variáveis', async () => {
            // Cria um template
            const template = {
                name: 'Template Incompleto',
                content: 'Olá {{nome}}',
                variables: ['nome']
            };
            const createdTemplate = await templateManager.createTemplate(template);

            // Tenta renderizar sem fornecer todas as variáveis
            expect(() => templateManager.renderTemplate(createdTemplate.id, {}))
                .toThrow('Variáveis não fornecidas: {{nome}}');
        });
    });
}); 