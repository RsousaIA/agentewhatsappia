import { getFirestore, doc, getDoc, setDoc } from 'firebase/firestore'
import { app } from '../firebase'

const db = getFirestore(app)

export interface AgentConfig {
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

const DEFAULT_CONFIG: AgentConfig = {
  collector: {
    inactivityTimeout: 30, // 30 minutos
    evaluationInterval: 5, // 5 minutos
    consolidationInterval: 1440, // 24 horas
    reopenCheckInterval: 5 // 5 minutos
  },
  evaluator: {
    weights: {
      comunicacao: 0.2,
      conhecimento: 0.2,
      empatia: 0.15,
      profissionalismo: 0.15,
      resultados: 0.15,
      inteligenciaEmocional: 0.1,
      prazos: 0.05
    },
    minMessagesForEvaluation: 3,
    complaintDetection: {
      enabled: true,
      sensitivity: 70
    }
  }
}

export const getAgentConfig = async (): Promise<AgentConfig> => {
  try {
    const configRef = doc(db, 'config', 'agents')
    const configDoc = await getDoc(configRef)

    if (configDoc.exists()) {
      return configDoc.data() as AgentConfig
    }

    // Se não existir, cria com valores padrão
    await setDoc(configRef, DEFAULT_CONFIG)
    return DEFAULT_CONFIG
  } catch (error) {
    console.error('Erro ao obter configurações dos agentes:', error)
    throw new Error('Falha ao carregar configurações')
  }
}

export const updateAgentConfig = async (config: AgentConfig): Promise<void> => {
  try {
    const configRef = doc(db, 'config', 'agents')
    await setDoc(configRef, config)
  } catch (error) {
    console.error('Erro ao atualizar configurações dos agentes:', error)
    throw new Error('Falha ao salvar configurações')
  }
} 