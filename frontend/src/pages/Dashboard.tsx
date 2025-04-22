import { useState, useEffect } from 'react'
import { getDashboardMetrics, DashboardMetrics } from '../services/dashboardService'
import {
  ChatBubbleLeftRightIcon,
  ChatBubbleLeftIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import StatsCard from '../components/StatsCard'
import Chart from '../components/Chart'
import WhatsAppStatus from '../components/WhatsAppStatus'
import { getFirestore, collection, query, where, getDocs, orderBy, limit, Timestamp } from 'firebase/firestore'
import { db } from '../services/firebase'

interface DashboardData {
  totalConversations: number
  activeConversations: number
  closedConversations: number
  averageEvaluation: number
  recentConversations: {
    id: string
    client: {
      name: string
    }
    lastMessageAt: Date
    status: string
  }[]
  evaluationsByDay: {
    date: string
    average: number
  }[]
}

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DashboardData>({
    totalConversations: 0,
    activeConversations: 0,
    closedConversations: 0,
    averageEvaluation: 0,
    recentConversations: [],
    evaluationsByDay: []
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        
        // Consultas ao Firestore
        const conversationsRef = collection(db, 'conversations')
        const activeQuery = query(
          conversationsRef,
          where('status', '==', 'active')
        )
        const closedQuery = query(
          conversationsRef,
          where('status', '==', 'closed')
        )
        const recentQuery = query(
          conversationsRef,
          orderBy('lastMessageAt', 'desc'),
          limit(5)
        )
        
        // Execução das consultas
        const [activeSnapshot, closedSnapshot, recentSnapshot] = await Promise.all([
          getDocs(activeQuery),
          getDocs(closedQuery),
          getDocs(recentQuery)
        ])
        
        // Dados das conversas
        const activeCount = activeSnapshot.size
        const closedCount = closedSnapshot.size
        const totalCount = activeCount + closedCount
        
        // Processamento das conversas recentes
        const recentConversations = recentSnapshot.docs.map(doc => {
          const data = doc.data()
          return {
            id: doc.id,
            client: data.client,
            lastMessageAt: (data.lastMessageAt as Timestamp).toDate(),
            status: data.status
          }
        })
        
        // Dados fictícios para o gráfico (para ser substituído por dados reais)
        const evaluationsByDay = [
          { date: '2023-01-01', average: 4.2 },
          { date: '2023-01-02', average: 4.5 },
          { date: '2023-01-03', average: 4.1 },
          { date: '2023-01-04', average: 4.7 },
          { date: '2023-01-05', average: 4.3 },
          { date: '2023-01-06', average: 4.6 },
          { date: '2023-01-07', average: 4.8 }
        ]
        
        setData({
          totalConversations: totalCount,
          activeConversations: activeCount,
          closedConversations: closedCount,
          averageEvaluation: 4.5, // Valor fictício para exemplo
          recentConversations,
          evaluationsByDay
        })
      } catch (error) {
        console.error("Erro ao buscar dados do dashboard:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        <StatsCard 
          title="Total de Conversas" 
          value={data.totalConversations} 
          icon="chat" 
          className="bg-blue-50"
        />
        <StatsCard 
          title="Conversas Ativas" 
          value={data.activeConversations} 
          icon="active" 
          className="bg-green-50"
        />
        <StatsCard 
          title="Conversas Encerradas" 
          value={data.closedConversations} 
          icon="closed" 
          className="bg-orange-50"
        />
        <StatsCard 
          title="Avaliação Média" 
          value={data.averageEvaluation.toFixed(1)} 
          icon="star" 
          className="bg-purple-50"
        />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <WhatsAppStatus className="lg:col-span-1" />
        
        <div className="bg-white rounded-lg shadow-md p-4 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Avaliações por Dia</h2>
          <Chart 
            data={data.evaluationsByDay.map(item => ({ 
              name: item.date, 
              value: item.average 
            }))} 
            xKey="name" 
            yKey="value"
            height={300}
          />
        </div>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-lg font-semibold mb-4">Conversas Recentes</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cliente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Última Mensagem
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.recentConversations.map((conversation) => (
                <tr key={conversation.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {conversation.client?.name || 'Cliente'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">
                      {conversation.lastMessageAt?.toLocaleString() || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      conversation.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {conversation.status === 'active' ? 'Ativa' : 'Encerrada'}
                    </span>
                  </td>
                </tr>
              ))}
              {data.recentConversations.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-4 text-center text-sm text-gray-500">
                    Nenhuma conversa recente
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Dashboard 

if (import.meta.hot && !inWebWorker) {
  // ... rest of the code ...
} 