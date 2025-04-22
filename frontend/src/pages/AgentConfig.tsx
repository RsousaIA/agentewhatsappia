import { useState, useEffect } from 'react'
import { getAgentConfig, updateAgentConfig } from '../services/agentService'
import {
  Cog6ToothIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

interface AgentConfig {
  collector: {
    inactivityTimeout: number
    evaluationInterval: number
    consolidationInterval: number
    reopenCheckInterval: number
  }
  evaluator: {
    weights: {
      comunicacao: number
      conhecimento: number
      empatia: number
      profissionalismo: number
      resultados: number
      inteligenciaEmocional: number
      prazos: number
    }
    minMessagesForEvaluation: number
    complaintDetection: {
      enabled: boolean
      sensitivity: number
    }
  }
}

const AgentConfig = () => {
  const [config, setConfig] = useState<AgentConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true)
        const data = await getAgentConfig()
        setConfig(data)
      } catch (err) {
        setError('Erro ao carregar configurações')
        console.error('Erro ao carregar configurações:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      await updateAgentConfig(config!)
      // Mostrar mensagem de sucesso
    } catch (err) {
      setError('Erro ao salvar configurações')
      console.error('Erro ao salvar configurações:', err)
    } finally {
      setSaving(false)
    }
  }

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
        <h1 className="text-2xl font-bold text-gray-900">Configuração dos Agentes</h1>
        <p className="mt-1 text-sm text-gray-500">
          Ajuste as configurações dos agentes de acordo com suas necessidades
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Agente Coletor */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center mb-4">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-blue-600 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">Agente Coletor</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Tempo de Inatividade (minutos)
              </label>
              <input
                type="number"
                value={config?.collector.inactivityTimeout}
                onChange={(e) => setConfig({
                  ...config!,
                  collector: {
                    ...config!.collector,
                    inactivityTimeout: parseInt(e.target.value)
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Intervalo de Avaliação (minutos)
              </label>
              <input
                type="number"
                value={config?.collector.evaluationInterval}
                onChange={(e) => setConfig({
                  ...config!,
                  collector: {
                    ...config!.collector,
                    evaluationInterval: parseInt(e.target.value)
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Intervalo de Consolidação (minutos)
              </label>
              <input
                type="number"
                value={config?.collector.consolidationInterval}
                onChange={(e) => setConfig({
                  ...config!,
                  collector: {
                    ...config!.collector,
                    consolidationInterval: parseInt(e.target.value)
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Intervalo de Verificação de Reabertura (minutos)
              </label>
              <input
                type="number"
                value={config?.collector.reopenCheckInterval}
                onChange={(e) => setConfig({
                  ...config!,
                  collector: {
                    ...config!.collector,
                    reopenCheckInterval: parseInt(e.target.value)
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>
          </div>
        </div>

        {/* Agente Avaliador */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center mb-4">
            <ChartBarIcon className="h-6 w-6 text-purple-600 mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">Agente Avaliador</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Peso - Comunicação
              </label>
              <input
                type="number"
                value={config?.evaluator.weights.comunicacao}
                onChange={(e) => setConfig({
                  ...config!,
                  evaluator: {
                    ...config!.evaluator,
                    weights: {
                      ...config!.evaluator.weights,
                      comunicacao: parseFloat(e.target.value)
                    }
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Peso - Empatia
              </label>
              <input
                type="number"
                value={config?.evaluator.weights.empatia}
                onChange={(e) => setConfig({
                  ...config!,
                  evaluator: {
                    ...config!.evaluator,
                    weights: {
                      ...config!.evaluator.weights,
                      empatia: parseFloat(e.target.value)
                    }
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Mínimo de Mensagens para Avaliação
              </label>
              <input
                type="number"
                value={config?.evaluator.minMessagesForEvaluation}
                onChange={(e) => setConfig({
                  ...config!,
                  evaluator: {
                    ...config!.evaluator,
                    minMessagesForEvaluation: parseInt(e.target.value)
                  }
                })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm"
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                checked={config?.evaluator.complaintDetection.enabled}
                onChange={(e) => setConfig({
                  ...config!,
                  evaluator: {
                    ...config!.evaluator,
                    complaintDetection: {
                      ...config!.evaluator.complaintDetection,
                      enabled: e.target.checked
                    }
                  }
                })}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              />
              <label className="ml-2 block text-sm text-gray-900">
                Detecção de Reclamações
              </label>
            </div>

            {config?.evaluator.complaintDetection.enabled && (
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Sensibilidade da Detecção
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={config.evaluator.complaintDetection.sensitivity}
                  onChange={(e) => setConfig({
                    ...config,
                    evaluator: {
                      ...config.evaluator,
                      complaintDetection: {
                        ...config.evaluator.complaintDetection,
                        sensitivity: parseInt(e.target.value)
                      }
                    }
                  })}
                  className="mt-1 block w-full"
                />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          {saving ? 'Salvando...' : 'Salvar Configurações'}
        </button>
      </div>
    </div>
  )
}

export default AgentConfig 