import { db } from '../config/firebase'
import { doc, getDoc, collection, query, where, getDocs, Timestamp } from 'firebase/firestore'

export interface EvaluationDetails {
  id: string
  conversaId: string
  data: string
  notas: {
    comunicacao: number
    conhecimento: number
    empatia: number
    profissionalismo: number
    resultados: number
    inteligenciaEmocional: number
    prazos: number
  }
  notaGeral: number
  comentarios: string
  solicitacoes: Array<{
    descricao: string
    prazo: string
    status: string
  }>
  tempoMedioResposta: number
  atendente: string
}

export const getEvaluationDetails = async (id: string): Promise<EvaluationDetails> => {
  try {
    // Buscar avaliação
    const evaluationRef = doc(db, 'avaliacoes', id)
    const evaluationDoc = await getDoc(evaluationRef)

    if (!evaluationDoc.exists()) {
      throw new Error('Avaliação não encontrada')
    }

    const evaluationData = evaluationDoc.data()

    // Buscar conversa relacionada
    const conversaRef = doc(db, 'conversas', evaluationData.conversaId)
    const conversaDoc = await getDoc(conversaRef)

    if (!conversaDoc.exists()) {
      throw new Error('Conversa não encontrada')
    }

    const conversaData = conversaDoc.data()

    // Buscar solicitações da conversa
    const solicitacoesRef = collection(db, `conversas/${evaluationData.conversaId}/solicitacoes`)
    const solicitacoesSnapshot = await getDocs(solicitacoesRef)
    const solicitacoes = solicitacoesSnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }))

    // Calcular tempo médio de resposta
    const mensagensRef = collection(db, `conversas/${evaluationData.conversaId}/mensagens`)
    const mensagensSnapshot = await getDocs(mensagensRef)
    const mensagens = mensagensSnapshot.docs.map(doc => ({
      timestamp: doc.data().timestamp,
      remetente: doc.data().remetente
    }))

    let somaTempos = 0
    let totalInteracoes = 0

    for (let i = 1; i < mensagens.length; i++) {
      if (mensagens[i].remetente === 'atendente') {
        const tempoResposta = (mensagens[i].timestamp.toDate() - mensagens[i-1].timestamp.toDate()) / 1000 / 60 // em minutos
        somaTempos += tempoResposta
        totalInteracoes++
      }
    }

    const tempoMedioResposta = totalInteracoes > 0 ? somaTempos / totalInteracoes : 0

    return {
      id: evaluationDoc.id,
      conversaId: evaluationData.conversaId,
      data: evaluationData.data.toDate().toLocaleDateString('pt-BR'),
      notas: evaluationData.notas,
      notaGeral: evaluationData.notaGeral,
      comentarios: evaluationData.comentarios,
      solicitacoes: solicitacoes.map(s => ({
        descricao: s.descricao,
        prazo: s.prazo,
        status: s.status
      })),
      tempoMedioResposta,
      atendente: conversaData.atendente
    }
  } catch (error) {
    console.error('Erro ao buscar detalhes da avaliação:', error)
    throw error
  }
}

export interface EvaluationMetrics {
  period: string
  totalEvaluations: number
  averageScore: number
  scoresByCategory: Array<{ name: string; value: number }>
  scoresByAttendant: Array<{ name: string; value: number }>
  scoresByPeriod: Array<{ date: string; score: number }>
  complaints: {
    total: number
    byCategory: Array<{ name: string; value: number }>
  }
}

export const getEvaluationMetrics = async (period: string): Promise<EvaluationMetrics> => {
  try {
    // Calcular data de início baseado no período
    const now = new Date()
    let startDate = new Date()
    
    switch (period) {
      case '7d':
        startDate.setDate(now.getDate() - 7)
        break
      case '30d':
        startDate.setDate(now.getDate() - 30)
        break
      case '90d':
        startDate.setDate(now.getDate() - 90)
        break
      default:
        startDate.setDate(now.getDate() - 7)
    }

    // Buscar avaliações do período
    const evaluationsRef = collection(db, 'avaliacoes')
    const q = query(
      evaluationsRef,
      where('data', '>=', Timestamp.fromDate(startDate))
    )
    
    const snapshot = await getDocs(q)
    const evaluations = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }))

    // Calcular métricas
    const totalEvaluations = evaluations.length
    const averageScore = evaluations.reduce((acc, curr) => acc + curr.notaGeral, 0) / totalEvaluations

    // Agrupar por categoria
    const scoresByCategory = Object.entries(evaluations[0].notas).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value: evaluations.reduce((acc, curr) => acc + curr.notas[name], 0) / totalEvaluations
    }))

    // Agrupar por atendente
    const attendants = [...new Set(evaluations.map(e => e.atendente))]
    const scoresByAttendant = attendants.map(attendant => {
      const attendantEvaluations = evaluations.filter(e => e.atendente === attendant)
      return {
        name: attendant,
        value: attendantEvaluations.reduce((acc, curr) => acc + curr.notaGeral, 0) / attendantEvaluations.length
      }
    })

    // Agrupar por período
    const scoresByPeriod = evaluations.reduce((acc, curr) => {
      const date = curr.data.toDate().toLocaleDateString('pt-BR')
      const existing = acc.find(item => item.date === date)
      
      if (existing) {
        existing.score = (existing.score + curr.notaGeral) / 2
      } else {
        acc.push({ date, score: curr.notaGeral })
      }
      
      return acc
    }, [] as { date: string; score: number }[])

    // Contar reclamações
    const complaints = evaluations.filter(e => e.reclamacao)
    const complaintsByCategory = complaints.reduce((acc, curr) => {
      const category = curr.categoriaReclamacao || 'Outros'
      const existing = acc.find(item => item.name === category)
      
      if (existing) {
        existing.value++
      } else {
        acc.push({ name: category, value: 1 })
      }
      
      return acc
    }, [] as { name: string; value: number }[])

    return {
      period,
      totalEvaluations,
      averageScore,
      scoresByCategory,
      scoresByAttendant,
      scoresByPeriod,
      complaints: {
        total: complaints.length,
        byCategory: complaintsByCategory
      }
    }
  } catch (error) {
    console.error('Erro ao buscar métricas:', error)
    throw new Error('Falha ao carregar métricas')
  }
} 