import os
import json
import logging
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import wraps
from flask import request, jsonify
from firebase_admin import auth as firebase_auth
from .firebase_db import init_firebase

# Configuração de logging
logger = logging.getLogger(__name__)

# Inicializa o Firebase
init_firebase()

class AuthManager:
    def __init__(self):
        """Inicializa o gerenciador de autenticação"""
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY não configurada")
    
    def create_token(self, user_id: str, roles: list = None) -> str:
        """
        Cria um token JWT para um usuário
        
        Args:
            user_id: ID do usuário
            roles: Lista de papéis do usuário
            
        Returns:
            Token JWT
        """
        try:
            payload = {
                'user_id': user_id,
                'roles': roles or [],
                'exp': datetime.utcnow() + timedelta(days=1)
            }
            return jwt.encode(payload, self.secret_key, algorithm='HS256')
        except Exception as e:
            logger.error(f"Erro ao criar token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verifica um token JWT
        
        Args:
            token: Token JWT
            
        Returns:
            Payload do token ou None se inválido
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Token inválido")
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            return None
    
    def verify_firebase_token(self, token: str) -> Optional[Dict]:
        """
        Verifica um token do Firebase
        
        Args:
            token: Token do Firebase
            
        Returns:
            Dados do usuário ou None se inválido
        """
        try:
            decoded_token = firebase_auth.verify_id_token(token)
            return decoded_token
        except Exception as e:
            logger.error(f"Erro ao verificar token do Firebase: {e}")
            return None
    
    def has_role(self, token: str, required_role: str) -> bool:
        """
        Verifica se um usuário tem um papel específico
        
        Args:
            token: Token JWT
            required_role: Papel requerido
            
        Returns:
            True se o usuário tem o papel, False caso contrário
        """
        payload = self.verify_token(token)
        if not payload:
            return False
            
        return required_role in payload.get('roles', [])
    
    def require_auth(self, roles: list = None):
        """
        Decorador para requerer autenticação
        
        Args:
            roles: Lista de papéis requeridos
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Obtém o token do cabeçalho
                token = request.headers.get('Authorization')
                if not token:
                    return jsonify({'error': 'Token não fornecido'}), 401
                
                # Remove o prefixo 'Bearer ' se presente
                if token.startswith('Bearer '):
                    token = token[7:]
                
                # Verifica o token
                payload = self.verify_token(token)
                if not payload:
                    return jsonify({'error': 'Token inválido'}), 401
                
                # Verifica os papéis
                if roles:
                    user_roles = payload.get('roles', [])
                    if not any(role in user_roles for role in roles):
                        return jsonify({'error': 'Acesso negado'}), 403
                
                # Adiciona o payload ao contexto da requisição
                request.user = payload
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

# Instância global do gerenciador de autenticação
auth_manager = AuthManager()

def require_auth(roles: list = None):
    """
    Decorador para requerer autenticação
    
    Args:
        roles: Lista de papéis requeridos
    """
    return auth_manager.require_auth(roles)

def create_token(user_id: str, roles: list = None) -> str:
    """
    Cria um token JWT para um usuário
    
    Args:
        user_id: ID do usuário
        roles: Lista de papéis do usuário
        
    Returns:
        Token JWT
    """
    return auth_manager.create_token(user_id, roles)

def verify_token(token: str) -> Optional[Dict]:
    """
    Verifica um token JWT
    
    Args:
        token: Token JWT
        
    Returns:
        Payload do token ou None se inválido
    """
    return auth_manager.verify_token(token)

def verify_firebase_token(token: str) -> Optional[Dict]:
    """
    Verifica um token do Firebase
    
    Args:
        token: Token do Firebase
        
    Returns:
        Dados do usuário ou None se inválido
    """
    return auth_manager.verify_firebase_token(token) 