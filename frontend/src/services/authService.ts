import { 
  getAuth, 
  signInWithEmailAndPassword, 
  signOut, 
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
  User
} from 'firebase/auth'
import { auth } from './firebase'

export interface AuthError {
  code: string
  message: string
}

export const register = async (email: string, password: string): Promise<User> => {
  try {
    const result = await createUserWithEmailAndPassword(auth, email, password)
    return result.user
  } catch (error: any) {
    console.error('Erro no registro:', error)
    throw {
      code: error.code,
      message: getErrorMessage(error.code)
    }
  }
}

export const login = async (email: string, password: string): Promise<User> => {
  try {
    const result = await signInWithEmailAndPassword(auth, email, password)
    return result.user
  } catch (error: any) {
    console.error('Erro no login:', error)
    throw {
      code: error.code,
      message: getErrorMessage(error.code)
    }
  }
}

export const logout = async (): Promise<void> => {
  try {
    await signOut(auth)
  } catch (error: any) {
    console.error('Erro no logout:', error)
    throw {
      code: error.code,
      message: 'Erro ao fazer logout'
    }
  }
}

export const subscribeToAuthChanges = (callback: (user: User | null) => void) => {
  return onAuthStateChanged(auth, callback)
}

export const loginWithGoogle = async (): Promise<User> => {
  try {
    const provider = new GoogleAuthProvider()
    const result = await signInWithPopup(auth, provider)
    return result.user
  } catch (error: any) {
    console.error('Erro no login com Google:', error)
    throw {
      code: error.code,
      message: getErrorMessage(error.code)
    }
  }
}

// Função auxiliar para traduzir mensagens de erro do Firebase
const getErrorMessage = (errorCode: string): string => {
  switch (errorCode) {
    case 'auth/invalid-email':
      return 'E-mail inválido'
    case 'auth/user-disabled':
      return 'Usuário desativado'
    case 'auth/user-not-found':
      return 'Usuário não encontrado'
    case 'auth/wrong-password':
      return 'Senha incorreta'
    case 'auth/email-already-in-use':
      return 'Este e-mail já está cadastrado'
    case 'auth/weak-password':
      return 'A senha deve ter pelo menos 6 caracteres'
    case 'auth/operation-not-allowed':
      return 'Operação não permitida'
    case 'auth/too-many-requests':
      return 'Muitas tentativas. Tente novamente mais tarde'
    case 'auth/invalid-password':
      return 'A senha deve ter pelo menos 6 caracteres'
    case 'auth/popup-closed-by-user':
      return 'Login cancelado. A janela foi fechada.'
    case 'auth/popup-blocked':
      return 'O popup de login foi bloqueado pelo navegador.'
    case 'auth/account-exists-with-different-credential':
      return 'Já existe uma conta com este e-mail usando outro método de login.'
    case 'auth/cancelled-popup-request':
      return 'A operação foi cancelada.'
    case 'auth/unauthorized-domain':
      return 'Este domínio não está autorizado para operações OAuth.'
    default:
      return 'Erro na autenticação'
  }
} 