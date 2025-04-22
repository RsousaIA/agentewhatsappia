import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, signOut, createUserWithEmailAndPassword } from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  doc, 
  getDoc, 
  getDocs, 
  setDoc, 
  updateDoc, 
  query, 
  where, 
  orderBy, 
  limit, 
  onSnapshot,
  Timestamp,
  serverTimestamp
} from 'firebase/firestore';
import { getStorage } from 'firebase/storage';

// Configuração do Firebase
const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID
};

// Inicializar o Firebase
const app = initializeApp(firebaseConfig);

// Exportar serviços do Firebase
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Funções de Autenticação
export const loginWithEmail = (email, password) => {
  return signInWithEmailAndPassword(auth, email, password);
};

export const logoutUser = () => {
  return signOut(auth);
};

export const registerUser = (email, password) => {
  return createUserWithEmailAndPassword(auth, email, password);
};

// Funções para Conversas
export const getConversations = async (status = null, limit = 50) => {
  try {
    let conversationsQuery;
    
    if (status) {
      conversationsQuery = query(
        collection(db, 'conversas'),
        where('status', '==', status),
        orderBy('ultimaMensagem', 'desc'),
        limit(limit)
      );
    } else {
      conversationsQuery = query(
        collection(db, 'conversas'),
        orderBy('ultimaMensagem', 'desc'),
        limit(limit)
      );
    }
    
    const snapshot = await getDocs(conversationsQuery);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error('Erro ao buscar conversas:', error);
    throw error;
  }
};

export const getConversationById = async (conversationId) => {
  try {
    const docRef = doc(db, 'conversas', conversationId);
    const docSnap = await getDoc(docRef);
    
    if (docSnap.exists()) {
      return {
        id: docSnap.id,
        ...docSnap.data()
      };
    } else {
      throw new Error('Conversa não encontrada');
    }
  } catch (error) {
    console.error('Erro ao buscar conversa:', error);
    throw error;
  }
};

export const getMessagesForConversation = async (conversationId, messageLimit = 100) => {
  try {
    const messagesQuery = query(
      collection(db, 'conversas', conversationId, 'mensagens'),
      orderBy('timestamp', 'asc'),
      limit(messageLimit)
    );
    
    const snapshot = await getDocs(messagesQuery);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error('Erro ao buscar mensagens:', error);
    throw error;
  }
};

export const listenToConversation = (conversationId, callback) => {
  const conversationRef = doc(db, 'conversas', conversationId);
  return onSnapshot(conversationRef, (doc) => {
    if (doc.exists()) {
      callback({
        id: doc.id,
        ...doc.data()
      });
    }
  });
};

export const listenToMessages = (conversationId, callback) => {
  const messagesQuery = query(
    collection(db, 'conversas', conversationId, 'mensagens'),
    orderBy('timestamp', 'asc')
  );
  
  return onSnapshot(messagesQuery, (snapshot) => {
    const messages = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    callback(messages);
  });
};

export const sendMessage = async (conversationId, messageData) => {
  try {
    const messagesRef = collection(db, 'conversas', conversationId, 'mensagens');
    const messageWithTimestamp = {
      ...messageData,
      timestamp: serverTimestamp()
    };
    
    await setDoc(doc(messagesRef), messageWithTimestamp);
    
    // Atualizar última mensagem da conversa
    const conversationRef = doc(db, 'conversas', conversationId);
    await updateDoc(conversationRef, {
      ultimaMensagem: serverTimestamp()
    });
    
    return true;
  } catch (error) {
    console.error('Erro ao enviar mensagem:', error);
    throw error;
  }
};

export const updateConversation = async (conversationId, data) => {
  try {
    const conversationRef = doc(db, 'conversas', conversationId);
    await updateDoc(conversationRef, data);
    return true;
  } catch (error) {
    console.error('Erro ao atualizar conversa:', error);
    throw error;
  }
};

// Funções para Avaliações
export const getEvaluationsForConversation = async (conversationId) => {
  try {
    const evaluationsQuery = query(
      collection(db, 'conversas', conversationId, 'avaliacoes'),
      orderBy('data_avaliacao', 'desc')
    );
    
    const snapshot = await getDocs(evaluationsQuery);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error('Erro ao buscar avaliações:', error);
    throw error;
  }
};

export const getCriticalConversations = async (limit = 50) => {
  try {
    // Busca conversas avaliadas com nota geral baixa (menor que 5)
    const evaluatedConversationsQuery = query(
      collection(db, 'conversas'),
      where('avaliada', '==', true),
      where('notaGeral', '<', 5),
      orderBy('notaGeral', 'asc'),
      limit(limit)
    );
    
    const snapshot = await getDocs(evaluatedConversationsQuery);
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error('Erro ao buscar conversas críticas:', error);
    throw error;
  }
};

// Funções para Dashboard
export const getDashboardData = async () => {
  try {
    // Contagem de conversas por status
    const activeConversations = await getConversations('ACTIVE', 1000);
    const closedConversations = await getConversations('CLOSED', 1000);
    
    // Estatísticas simples
    return {
      totalActive: activeConversations.length,
      totalClosed: closedConversations.length,
      totalConversations: activeConversations.length + closedConversations.length,
      recentConversations: [...activeConversations].slice(0, 5)
    };
  } catch (error) {
    console.error('Erro ao buscar dados do dashboard:', error);
    throw error;
  }
};

// Configurações de tempo real
export const listenToActiveConversations = (callback) => {
  const activeConversationsQuery = query(
    collection(db, 'conversas'),
    where('status', '==', 'ACTIVE'),
    orderBy('ultimaMensagem', 'desc'),
    limit(50)
  );
  
  return onSnapshot(activeConversationsQuery, (snapshot) => {
    const conversations = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    callback(conversations);
  });
};

export default app; 