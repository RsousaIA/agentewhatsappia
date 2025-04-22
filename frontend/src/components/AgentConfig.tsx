import React, { useState, useEffect } from 'react'
import { getAgentConfig, updateAgentConfig, AgentConfig } from '../services/agentService'
import { 
  CogIcon, 
  ClockIcon, 
  ChartBarIcon, 
  BellIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'

const AgentConfig: React.FC = () => {
  const [config, setConfig] = useState<AgentConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const data = await getAgentConfig()
      setConfig(data)
      setError(null)
    } catch (err) {
      setError('Erro ao carregar configurações')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!config) return

    setSaving(true)
    setSaveSuccess(false)
    setError(null)

    try {
      await updateAgentConfig(config)
      setSaveSuccess(true)
    } catch (err) {
      setError('Erro ao salvar configurações')
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (section: 'collector' | 'evaluator', field: string, value: any) => {
    if (!config) return

    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [field]: value
      }
    })
  }

  const handleWeightChange = (weight: string, value: number) => {
    if (!config) return

    setConfig({
      ...config,
      evaluator: {
        ...config.evaluator,
        weights: {
          ...config.evaluator.weights,
          [weight]: value
        }
      }
    })
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="text-center text-red-500">
        Erro ao carregar configurações
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Configurações dos Agentes
        </h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:opacity-50"
        >
          {saving ? 'Salvando...' : 'Salvar Configurações'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-md flex items-center">
          <XCircleIcon className="h-5 w-5 mr-2" />
          {error}
        </div>
      )}

      {saveSuccess && (
        <div className="mb-4 p-4 bg-green-100 text-green-700 rounded-md flex items-center">
          <CheckCircleIcon className="h-5 w-5 mr-2" />
          Configurações salvas com sucesso!
        </div>
      )}

      <div className="space-y-8">
        {/* Configurações do Collector Agent */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center mb-4">
            <CogIcon className="h-6 w-6 text-blue-500 mr-2" />
            <h2 className="text-xl font-semibold">Collector Agent</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tempo de Inatividade (minutos)
              </label>
              <div className="relative">
                <ClockIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="number"
                  value={config.collector.inactivityTimeout}
                  onChange={(e) => handleChange('collector', 'inactivityTimeout', parseInt(e.target.value))}
                  className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo de Avaliação (minutos)
              </label>
              <div className="relative">
                <ChartBarIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="number"
                  value={config.collector.evaluationInterval}
                  onChange={(e) => handleChange('collector', 'evaluationInterval', parseInt(e.target.value))}
                  className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo de Consolidação (minutos)
              </label>
              <div className="relative">
                <ChartBarIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="number"
                  value={config.collector.consolidationInterval}
                  onChange={(e) => handleChange('collector', 'consolidationInterval', parseInt(e.target.value))}
                  className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo de Verificação de Reabertura (minutos)
              </label>
              <div className="relative">
                <BellIcon className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <input
                  type="number"
                  value={config.collector.reopenCheckInterval}
                  onChange={(e) => handleChange('collector', 'reopenCheckInterval', parseInt(e.target.value))}
                  className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Configurações do Evaluator Agent */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center mb-4">
            <CogIcon className="h-6 w-6 text-blue-500 mr-2" />
            <h2 className="text-xl font-semibold">Evaluator Agent</h2>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Pesos de Avaliação</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(config.evaluator.weights).map(([key, value]) => (
                  <div key={key}>
                    <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      value={value}
                      onChange={(e) => handleWeightChange(key, parseFloat(e.target.value))}
                      className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mínimo de Mensagens para Avaliação
              </label>
              <input
                type="number"
                value={config.evaluator.minMessagesForEvaluation}
                onChange={(e) => handleChange('evaluator', 'minMessagesForEvaluation', parseInt(e.target.value))}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Detecção de Reclamações</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.evaluator.complaintDetection.enabled}
                    onChange={(e) => handleChange('evaluator', 'complaintDetection', {
                      ...config.evaluator.complaintDetection,
                      enabled: e.target.checked
                    })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-900">
                    Habilitar detecção de reclamações
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sensibilidade (%)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={config.evaluator.complaintDetection.sensitivity}
                    onChange={(e) => handleChange('evaluator', 'complaintDetection', {
                      ...config.evaluator.complaintDetection,
                      sensitivity: parseInt(e.target.value)
                    })}
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AgentConfig 