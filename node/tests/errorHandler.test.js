const {
    WhatsAppError,
    InvalidNumberError,
    ConnectionError,
    SendMessageError,
    createError
} = require('../utils/errorHandler');

describe('Error Handling', () => {
    describe('WhatsAppError', () => {
        it('should create a WhatsAppError with message and code', () => {
            const error = new WhatsAppError('Test error', 'TEST_ERROR');
            expect(error).toBeInstanceOf(Error);
            expect(error).toBeInstanceOf(WhatsAppError);
            expect(error.message).toBe('Test error');
            expect(error.code).toBe('TEST_ERROR');
            expect(error.details).toEqual({});
        });

        it('should create a WhatsAppError with details', () => {
            const details = { foo: 'bar' };
            const error = new WhatsAppError('Test error', 'TEST_ERROR', details);
            expect(error.details).toEqual(details);
        });
    });

    describe('InvalidNumberError', () => {
        it('should create an InvalidNumberError', () => {
            const number = '123';
            const error = new InvalidNumberError(number);
            expect(error).toBeInstanceOf(WhatsAppError);
            expect(error.message).toBe('Número de telefone inválido');
            expect(error.code).toBe('INVALID_NUMBER');
            expect(error.details.number).toBe(number);
        });
    });

    describe('ConnectionError', () => {
        it('should create a ConnectionError', () => {
            const reason = 'timeout';
            const error = new ConnectionError(reason);
            expect(error).toBeInstanceOf(WhatsAppError);
            expect(error.message).toBe('Erro de conexão com WhatsApp');
            expect(error.code).toBe('CONNECTION_ERROR');
            expect(error.details.reason).toBe(reason);
        });
    });

    describe('SendMessageError', () => {
        it('should create a SendMessageError', () => {
            const to = '5511999999999@c.us';
            const reason = 'invalid number';
            const error = new SendMessageError(to, reason);
            expect(error).toBeInstanceOf(WhatsAppError);
            expect(error.message).toBe('Erro ao enviar mensagem');
            expect(error.code).toBe('SEND_MESSAGE_ERROR');
            expect(error.details.to).toBe(to);
            expect(error.details.reason).toBe(reason);
        });
    });

    describe('createError', () => {
        it('should create a custom error based on type', () => {
            const error = createError('INVALID_NUMBER', 'Custom message', {
                foo: 'bar'
            });
            expect(error).toBeInstanceOf(InvalidNumberError);
            expect(error.message).toBe('Custom message');
            expect(error.details.foo).toBe('bar');
        });

        it('should create a WhatsAppError for unknown types', () => {
            const error = createError('UNKNOWN_TYPE', 'Custom message');
            expect(error).toBeInstanceOf(WhatsAppError);
            expect(error.message).toBe('Custom message');
        });
    });
}); 