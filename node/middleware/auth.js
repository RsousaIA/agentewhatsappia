const jwt = require('jsonwebtoken');
const logger = require('../logger');

/**
 * Middleware de autenticação
 * Verifica se o token JWT é válido e extrai as informações do usuário
 */
const authenticate = (req, res, next) => {
    try {
        // Obtém o token do cabeçalho Authorization
        const authHeader = req.headers.authorization;
        if (!authHeader) {
            return res.status(401).json({
                error: 'Token de autenticação não fornecido'
            });
        }

        // Verifica se o formato do token está correto
        const parts = authHeader.split(' ');
        if (parts.length !== 2) {
            return res.status(401).json({
                error: 'Formato de token inválido'
            });
        }

        const [scheme, token] = parts;
        if (!/^Bearer$/i.test(scheme)) {
            return res.status(401).json({
                error: 'Formato de token inválido'
            });
        }

        // Verifica e decodifica o token
        jwt.verify(token, process.env.JWT_SECRET, (err, decoded) => {
            if (err) {
                logger.error('Erro ao verificar token', {
                    error: err.message
                });
                return res.status(401).json({
                    error: 'Token inválido'
                });
            }

            // Adiciona as informações do usuário à requisição
            req.user = decoded;
            return next();
        });
    } catch (error) {
        logger.error('Erro no middleware de autenticação', {
            error: error.message
        });
        return res.status(500).json({
            error: 'Erro interno do servidor'
        });
    }
};

/**
 * Middleware de autorização
 * Verifica se o usuário tem as permissões necessárias
 */
const authorize = (roles = []) => {
    return (req, res, next) => {
        try {
            // Se não houver roles definidas, permite o acesso
            if (roles.length === 0) {
                return next();
            }

            // Verifica se o usuário tem alguma das roles necessárias
            const hasRole = roles.some(role => req.user.roles.includes(role));
            if (!hasRole) {
                return res.status(403).json({
                    error: 'Acesso negado'
                });
            }

            return next();
        } catch (error) {
            logger.error('Erro no middleware de autorização', {
                error: error.message
            });
            return res.status(500).json({
                error: 'Erro interno do servidor'
            });
        }
    };
};

module.exports = {
    authenticate,
    authorize
}; 