import { db } from './firebase'
import { 
  collection, 
  query, 
  where, 
  getDocs, 
  orderBy, 
  limit,
  Timestamp
} from 'firebase/firestore'

export interface Conversation {
  id: string
  customer: string
  lastMessage: string
  status: 'resolvido' | 'em andamento' | 'pendente'
  priority: 'alta' | 'média' | 'baixa'
  lastUpdate: string
  createdAt: Timestamp
  messages: {
    text: string
    sender: 'user' | 'system'
    timestamp: Timestamp
  }[]
}

export interface DashboardStats {
  totalConversations: number
  activeConversations: number
  averageResponseTime: string
  satisfactionRate: number
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const conversationsRef = collection(db, 'conversations')
  
  // Buscar todas as conversas
  const allConversations = await getDocs(conversationsRef)
  const totalConversations = allConversations.size

  // Buscar conversas ativas
  const activeQuery = query(
    conversationsRef,
    where('status', '!=', 'resolvido')
  )
  const activeConversations = (await getDocs(activeQuery)).size

  // Calcular tempo médio de resposta
  let totalResponseTime = 0
  let responseCount = 0

  allConversations.forEach(doc => {
    const data = doc.data()
    if (data.messages && data.messages.length > 1) {
      const firstUserMessage = data.messages.find((m: any) => m.sender === 'user')
      const firstSystemResponse = data.messages.find((m: any) => m.sender === 'system')
      
      if (firstUserMessage && firstSystemResponse) {
        const responseTime = firstSystemResponse.timestamp.toDate().getTime() - 
                           firstUserMessage.timestamp.toDate().getTime()
        totalResponseTime += responseTime
        responseCount++
      }
    }
  })

  const averageResponseTime = responseCount > 0 
    ? Math.round(totalResponseTime / responseCount / 60000) // Converter para minutos
    : 0

  // Calcular taxa de satisfação (exemplo simplificado)
  const resolvedConversations = allConversations.docs.filter(
    doc => doc.data().status === 'resolvido'
  )
  const satisfactionRate = totalConversations > 0
    ? Math.round((resolvedConversations.length / totalConversations) * 100)
    : 0

  return {
    totalConversations,
    activeConversations,
    averageResponseTime: `${averageResponseTime}m`,
    satisfactionRate
  }
}

export const getRecentConversations = async (limitCount: number = 10): Promise<Conversation[]> => {
  const conversationsRef = collection(db, 'conversations')
  const q = query(
    conversationsRef,
    orderBy('lastUpdate', 'desc'),
    limit(limitCount)
  )

  const snapshot = await getDocs(q)
  return snapshot.docs.map(doc => ({
    id: doc.id,
    ...doc.data(),
    lastUpdate: formatTimestamp(doc.data().lastUpdate)
  })) as Conversation[]
}

const formatTimestamp = (timestamp: Timestamp): string => {
  const now = new Date()
  const date = timestamp.toDate()
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / 60000)

  if (diffInMinutes < 60) {
    return `há ${diffInMinutes} minutos`
  } else if (diffInMinutes < 1440) {
    const hours = Math.floor(diffInMinutes / 60)
    return `há ${hours} hora${hours > 1 ? 's' : ''}`
  } else {
    const days = Math.floor(diffInMinutes / 1440)
    return `há ${days} dia${days > 1 ? 's' : ''}`
  }
} 