import { db } from '../config/firebase'
import { 
  collection, 
  query, 
  where, 
  getDocs, 
  Timestamp,
  collectionGroup
} from 'firebase/firestore'

export interface DashboardMetrics {
  totalConversas: number
  conversasAtivas: number
  taxaResolucao: number
  tempoMedioResposta: number
}

export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  try {
    // Buscar todas as conversas
    const conversasRef = collection(db, 'conversas')
    const conversasSnapshot = await getDocs(conversasRef)
    const totalConversas = conversasSnapshot.size

    // Buscar conversas ativas (últimas 24 horas)
    const ontem = Timestamp.fromDate(new Date(Date.now() - 24 * 60 * 60 * 1000))
    const conversasAtivasQuery = query(
      conversasRef,
      where('lastMessageTime', '>=', ontem)
    )
    const conversasAtivasSnapshot = await getDocs(conversasAtivasQuery)
    const conversasAtivas = conversasAtivasSnapshot.size

    // Calcular taxa de resolução
    const conversasResolvidasQuery = query(
      conversasRef,
      where('status', '==', 'resolvido')
    )
    const conversasResolvidasSnapshot = await getDocs(conversasResolvidasQuery)
    const taxaResolucao = totalConversas > 0 
      ? (conversasResolvidasSnapshot.size / totalConversas) * 100 
      : 0

    // Calcular tempo médio de resposta
    const mensagensRef = collectionGroup(db, 'mensagens')
    const mensagensSnapshot = await getDocs(mensagensRef)
    let somaTempos = 0
    let totalInteracoes = 0

    const mensagens = mensagensSnapshot.docs.map(doc => ({
      timestamp: doc.data().timestamp,
      fromMe: doc.data().fromMe
    }))

    // Ordenar mensagens por timestamp
    mensagens.sort((a, b) => a.timestamp.seconds - b.timestamp.seconds)

    // Calcular tempo entre pergunta e resposta
    for (let i = 0; i < mensagens.length - 1; i++) {
      if (!mensagens[i].fromMe && mensagens[i + 1].fromMe) {
        const tempoResposta = mensagens[i + 1].timestamp.seconds - mensagens[i].timestamp.seconds
        somaTempos += tempoResposta
        totalInteracoes++
      }
    }

    const tempoMedioResposta = totalInteracoes > 0 
      ? somaTempos / totalInteracoes / 60 // Converter para minutos
      : 0

    return {
      totalConversas,
      conversasAtivas,
      taxaResolucao,
      tempoMedioResposta
    }
  } catch (error) {
    console.error('Erro ao buscar métricas:', error)
    throw new Error('Erro ao carregar métricas do dashboard')
  }
} 