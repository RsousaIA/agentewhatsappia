import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth, loginWithEmail, logoutUser } from '../services/firebase';
import { onAuthStateChanged } from 'firebase/auth';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user);
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const login = async (email, password) => {
    try {
      setError('');
      await loginWithEmail(email, password);
    } catch (error) {
      console.error('Erro de login:', error);
      setError('Falha ao fazer login. Verifique suas credenciais.');
      throw error;
    }
  };

  const logout = async () => {
    try {
      setError('');
      await logoutUser();
    } catch (error) {
      console.error('Erro ao sair:', error);
      setError('Falha ao fazer logout.');
      throw error;
    }
  };

  const value = {
    currentUser,
    login,
    logout,
    error,
    setError
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
} 