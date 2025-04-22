import React, { useState, useEffect } from 'react'
import { getEvaluationMetrics } from '../services/evaluationService'
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'

interface EvaluationMetrics {
  period: string
  totalEvaluations: number
  averageScore: number
  scoresByCategory: {
    name: string
    value: number
  }[]
  scoresByAttendant: {
    name: string
    value: number
  }[]
  scoresByPeriod: {
    date: string
    score: number
  }[]
  complaints: {
    total: number
    byCategory: {
      name: string
      value: number
    }[]
  }
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

const EvaluationMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState('7d') // 7d, 30d, 90d

  useEffect(() => {
    loadMetrics()
  }, [period])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      const data = await getEvaluationMetrics(period)
      setMetrics(data)
      setError(null)
    } catch (err) {
      setError('Erro ao carregar métricas')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="text-center text-red-500">
        {error || 'Erro ao carregar métricas'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="flex justify-end space-x-4">
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        >
          <option value="7d">Últimos 7 dias</option>
          <option value="30d">Últimos 30 dias</option>
          <option value="90d">Últimos 90 dias</option>
        </select>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ChartBarIcon className="h-6 w-6 text-blue-500 mr-2" />
            <h3 className="text-lg font-semibold">Total de Avaliações</h3>
          </div>
          <p className="text-3xl font-bold mt-2">{metrics.totalEvaluations}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-green-500 mr-2" />
            <h3 className="text-lg font-semibold">Média Geral</h3>
          </div>
          <p className="text-3xl font-bold mt-2">{metrics.averageScore.toFixed(1)}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <UserGroupIcon className="h-6 w-6 text-purple-500 mr-2" />
            <h3 className="text-lg font-semibold">Atendentes Avaliados</h3>
          </div>
          <p className="text-3xl font-bold mt-2">{metrics.scoresByAttendant.length}</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center">
            <ClockIcon className="h-6 w-6 text-yellow-500 mr-2" />
            <h3 className="text-lg font-semibold">Reclamações</h3>
          </div>
          <p className="text-3xl font-bold mt-2">{metrics.complaints.total}</p>
        </div>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolução das Notas */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Evolução das Notas</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.scoresByPeriod}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#8884d8"
                  name="Nota Média"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Notas por Categoria */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Notas por Categoria</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.scoresByCategory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#8884d8" name="Nota Média" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Notas por Atendente */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Notas por Atendente</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.scoresByAttendant}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#82ca9d" name="Nota Média" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Reclamações por Categoria */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Reclamações por Categoria</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={metrics.complaints.byCategory}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  nameKey="name"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {metrics.complaints.byCategory.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EvaluationMetrics 