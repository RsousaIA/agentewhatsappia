const jwt = require('jsonwebtoken');
const { authenticate, authorize } = require('../middleware/auth');

// Mock do jwt
jest.mock('jsonwebtoken');

describe('Middleware de Autenticação', () => {
    let req;
    let res;
    let next;

    beforeEach(() => {
        req = {
            headers: {}
        };
        res = {
            status: jest.fn().mockReturnThis(),
            json: jest.fn()
        };
        next = jest.fn();
    });

    describe('authenticate', () => {
        it('deve retornar erro 401 se não houver token', () => {
            authenticate(req, res, next);

            expect(res.status).toHaveBeenCalledWith(401);
            expect(res.json).toHaveBeenCalledWith({
                error: 'Token de autenticação não fornecido'
            });
            expect(next).not.toHaveBeenCalled();
        });

        it('deve retornar erro 401 se o formato do token for inválido', () => {
            req.headers.authorization = 'InvalidToken';

            authenticate(req, res, next);

            expect(res.status).toHaveBeenCalledWith(401);
            expect(res.json).toHaveBeenCalledWith({
                error: 'Formato de token inválido'
            });
            expect(next).not.toHaveBeenCalled();
        });

        it('deve retornar erro 401 se o token for inválido', () => {
            req.headers.authorization = 'Bearer invalid-token';
            jwt.verify.mockImplementation((token, secret, callback) => {
                callback(new Error('Token inválido'));
            });

            authenticate(req, res, next);

            expect(res.status).toHaveBeenCalledWith(401);
            expect(res.json).toHaveBeenCalledWith({
                error: 'Token inválido'
            });
            expect(next).not.toHaveBeenCalled();
        });

        it('deve adicionar as informações do usuário à requisição se o token for válido', () => {
            const user = {
                id: '123',
                roles: ['admin']
            };
            req.headers.authorization = 'Bearer valid-token';
            jwt.verify.mockImplementation((token, secret, callback) => {
                callback(null, user);
            });

            authenticate(req, res, next);

            expect(req.user).toEqual(user);
            expect(next).toHaveBeenCalled();
        });
    });

    describe('authorize', () => {
        beforeEach(() => {
            req.user = {
                roles: ['admin']
            };
        });

        it('deve permitir acesso se não houver roles definidas', () => {
            const middleware = authorize([]);
            middleware(req, res, next);

            expect(next).toHaveBeenCalled();
        });

        it('deve permitir acesso se o usuário tiver a role necessária', () => {
            const middleware = authorize(['admin']);
            middleware(req, res, next);

            expect(next).toHaveBeenCalled();
        });

        it('deve negar acesso se o usuário não tiver a role necessária', () => {
            const middleware = authorize(['user']);
            middleware(req, res, next);

            expect(res.status).toHaveBeenCalledWith(403);
            expect(res.json).toHaveBeenCalledWith({
                error: 'Acesso negado'
            });
            expect(next).not.toHaveBeenCalled();
        });

        it('deve negar acesso se o usuário não tiver roles definidas', () => {
            delete req.user.roles;
            const middleware = authorize(['admin']);
            middleware(req, res, next);

            expect(res.status).toHaveBeenCalledWith(403);
            expect(res.json).toHaveBeenCalledWith({
                error: 'Acesso negado'
            });
            expect(next).not.toHaveBeenCalled();
        });
    });
}); 