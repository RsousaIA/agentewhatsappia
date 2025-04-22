import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getEvaluationDetails } from '../services/evaluationService'
import {
  ChartBarIcon,
  UserGroupIcon,
  ClockIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'

interface EvaluationDetails {
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

const EvaluationDetails = () => {
  const { id } = useParams()
  const [evaluation, setEvaluation] = useState<EvaluationDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchEvaluation = async () => {
      try {
        setLoading(true)
        if (id) {
          const data = await getEvaluationDetails(id)
          setEvaluation(data)
        }
      } catch (err) {
        setError('Erro ao carregar detalhes da avaliação')
        console.error('Erro ao carregar avaliação:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchEvaluation()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500 text-center">
          <p className="text-xl font-semibold">{error}</p>
          <p className="mt-2">Por favor, tente novamente mais tarde.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Detalhes da Avaliação</h1>
        <p className="mt-1 text-sm text-gray-500">
          Avaliação realizada em {evaluation?.data}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Notas */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Notas</h2>
          <div className="space-y-4">
            {evaluation?.notas && Object.entries(evaluation.notas).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600 capitalize">
                  {key.replace(/([A-Z])/g, ' $1').trim()}
                </span>
                <span className="text-lg font-semibold text-gray-900">
                  {value.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Informações Gerais */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Informações Gerais</h2>
          <div className="space-y-4">
            <div className="flex items-center">
              <UserGroupIcon className="h-5 w-5 text-gray-400 mr-2" />
              <span className="text-sm text-gray-600">Atendente:</span>
              <span className="ml-2 text-sm font-medium text-gray-900">
                {evaluation?.atendente}
              </span>
            </div>
            <div className="flex items-center">
              <ClockIcon className="h-5 w-5 text-gray-400 mr-2" />
              <span className="text-sm text-gray-600">Tempo Médio de Resposta:</span>
              <span className="ml-2 text-sm font-medium text-gray-900">
                {evaluation?.tempoMedioResposta.toFixed(1)} min
              </span>
            </div>
            <div className="flex items-center">
              <ChatBubbleLeftRightIcon className="h-5 w-5 text-gray-400 mr-2" />
              <span className="text-sm text-gray-600">Nota Geral:</span>
              <span className="ml-2 text-sm font-medium text-gray-900">
                {evaluation?.notaGeral.toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        {/* Solicitações */}
        <div className="bg-white rounded-lg shadow-sm p-6 col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Solicitações</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Descrição
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Prazo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {evaluation?.solicitacoes.map((solicitacao, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {solicitacao.descricao}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {solicitacao.prazo}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        solicitacao.status === 'atendida' ? 'bg-green-100 text-green-800' :
                        solicitacao.status === 'pendente' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {solicitacao.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Comentários */}
        <div className="bg-white rounded-lg shadow-sm p-6 col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Comentários</h2>
          <p className="text-sm text-gray-600">{evaluation?.comentarios}</p>
        </div>
      </div>
    </div>
  )
}

export default EvaluationDetails 