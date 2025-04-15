const { formatPhoneNumber, isValidWhatsAppNumber } = require('../utils/phone');

describe('Phone Number Validation', () => {
    describe('formatPhoneNumber', () => {
        it('should format valid phone numbers correctly', () => {
            const testCases = [
                { input: '11999999999', expected: '5511999999999@c.us' },
                { input: '5511999999999', expected: '5511999999999@c.us' },
                { input: '(11) 99999-9999', expected: '5511999999999@c.us' },
                { input: '+55 11 99999-9999', expected: '5511999999999@c.us' }
            ];

            testCases.forEach(({ input, expected }) => {
                expect(formatPhoneNumber(input)).toBe(expected);
            });
        });

        it('should return null for invalid phone numbers', () => {
            const testCases = [
                '123', // Muito curto
                '12345678901234', // Muito longo
                'abc', // Caracteres não numéricos
                '', // Vazio
                null, // Nulo
                undefined // Indefinido
            ];

            testCases.forEach(input => {
                expect(formatPhoneNumber(input)).toBeNull();
            });
        });
    });

    describe('isValidWhatsAppNumber', () => {
        it('should validate correct WhatsApp numbers', () => {
            const validNumbers = [
                '5511999999999@c.us',
                '5511988888888@c.us',
                '5511977777777@c.us'
            ];

            validNumbers.forEach(number => {
                expect(isValidWhatsAppNumber(number)).toBe(true);
            });
        });

        it('should reject invalid WhatsApp numbers', () => {
            const invalidNumbers = [
                '5511999999999', // Sem @c.us
                '5511999999999@c.br', // Sufixo errado
                '5511999999999@c.us@c.us', // Sufixo duplicado
                'abc@c.us', // Não numérico
                '5511999999999@c.us123', // Caracteres extras
                '', // Vazio
                null, // Nulo
                undefined // Indefinido
            ];

            invalidNumbers.forEach(number => {
                expect(isValidWhatsAppNumber(number)).toBe(false);
            });
        });
    });
}); 