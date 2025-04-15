module.exports = {
    initialize: jest.fn().mockResolvedValue(undefined),
    createTemplate: jest.fn().mockImplementation(async (template) => {
        if (!template.content) {
            throw new Error('Template content is required');
        }
        return { id: '123', ...template };
    }),
    getTemplate: jest.fn().mockReturnValue({ 
        id: '123',
        name: 'test-template',
        content: 'Test content',
        category: 'test'
    }),
    listTemplates: jest.fn().mockReturnValue([
        { id: '123', name: 'test-template', content: 'Test content', category: 'test' }
    ])
}; 