import { db } from './firebase'
import { 
  collection, 
  query, 
  orderBy, 
  getDocs,
  Timestamp,
  where,
  collectionGroup
} from 'firebase/firestore'

export interface Message {
  id: string
  conversationId: string
  text: string
  sender: 'user' | 'system'
  timestamp: Timestamp
  status: 'received' | 'processed' | 'error'
  metadata?: {
    priority?: 'alta' | 'média' | 'baixa'
    category?: string
    sentiment?: 'positive' | 'neutral' | 'negative'
  }
}

export const getAllMessages = async (): Promise<Message[]> => {
  try {
    console.log('Iniciando busca de todas as mensagens...')
    const messagesRef = collectionGroup(db, 'mensagens')
    const q = query(
      messagesRef,
      orderBy('timestamp', 'desc')
    )

    console.log('Executando query...')
    const snapshot = await getDocs(q)
    console.log(`Encontradas ${snapshot.docs.length} mensagens`)

    return snapshot.docs.map(doc => {
      const data = doc.data()
      console.log('Dados da mensagem:', data)
      
      return {
        id: doc.id,
        conversationId: doc.ref.parent.parent?.id || '',
        text: data.text || data.body || '',
        sender: data.fromMe ? 'system' : 'user',
        timestamp: data.timestamp || Timestamp.now(),
        status: data.status || 'received',
        metadata: {
          priority: data.priority || data.metadata?.priority,
          category: data.category || data.metadata?.category,
          sentiment: data.sentiment || data.metadata?.sentiment
        }
      }
    }) as Message[]
  } catch (error) {
    console.error('Erro ao buscar mensagens:', error)
    throw new Error(`Erro ao buscar mensagens: ${error instanceof Error ? error.message : 'Erro desconhecido'}`)
  }
}

export const getMessagesByStatus = async (status: Message['status']): Promise<Message[]> => {
  try {
    console.log(`Buscando mensagens com status: ${status}`)
    const messagesRef = collectionGroup(db, 'mensagens')
    const q = query(
      messagesRef,
      where('status', '==', status),
      orderBy('timestamp', 'desc')
    )

    console.log('Executando query de status...')
    const snapshot = await getDocs(q)
    console.log(`Encontradas ${snapshot.docs.length} mensagens com status ${status}`)

    return snapshot.docs.map(doc => {
      const data = doc.data()
      console.log('Dados da mensagem:', data)
      
      return {
        id: doc.id,
        conversationId: doc.ref.parent.parent?.id || '',
        text: data.text || data.body || '',
        sender: data.fromMe ? 'system' : 'user',
        timestamp: data.timestamp || Timestamp.now(),
        status: data.status || 'received',
        metadata: {
          priority: data.priority || data.metadata?.priority,
          category: data.category || data.metadata?.category,
          sentiment: data.sentiment || data.metadata?.sentiment
        }
      }
    }) as Message[]
  } catch (error) {
    console.error('Erro ao buscar mensagens por status:', error)
    throw new Error(`Erro ao buscar mensagens por status: ${error instanceof Error ? error.message : 'Erro desconhecido'}`)
  }
}

export const formatTimestamp = (timestamp: Timestamp): string => {
  try {
    const date = timestamp.toDate()
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (error) {
    console.error('Erro ao formatar timestamp:', error)
    return 'Data inválida'
  }
} 