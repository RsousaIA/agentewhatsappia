import { render, screen, waitFor } from '@testing-library/react'
import { act } from 'react-dom/test-utils'
import { getCachedEvaluations, getCachedAttendances } from '../services/cacheService'
import { db } from '../config/firebase'
import { collection, query, where, getDocs, Timestamp } from 'firebase/firestore'

// Mock do Firebase
jest.mock('../config/firebase', () => ({
  db: {
    collection: jest.fn(),
    doc: jest.fn()
  }
}))

// Mock do Firestore
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  query: jest.fn(),
  where: jest.fn(),
  getDocs: jest.fn(),
  Timestamp: {
    fromDate: jest.fn()
  }
}))

describe('Testes de Integração', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('deve carregar avaliações do cache corretamente', async () => {
    const mockData = [
      { id: '1', score: 9.5, timestamp: new Date() },
      { id: '2', score: 8.0, timestamp: new Date() }
    ]

    ;(getDocs as jest.Mock).mockResolvedValueOnce({
      docs: mockData.map(item => ({
        id: item.id,
        data: () => item
      }))
    })

    const result = await getCachedEvaluations('7d')
    
    expect(result).toHaveLength(2)
    expect(result[0].id).toBe('1')
    expect(result[1].id).toBe('2')
  })

  test('deve carregar atendimentos do cache corretamente', async () => {
    const mockData = [
      { id: '1', status: 'concluido', timestamp: new Date() },
      { id: '2', status: 'pendente', timestamp: new Date() }
    ]

    ;(getDocs as jest.Mock).mockResolvedValueOnce({
      docs: mockData.map(item => ({
        id: item.id,
        data: () => item
      }))
    })

    const result = await getCachedAttendances('7d')
    
    expect(result).toHaveLength(2)
    expect(result[0].id).toBe('1')
    expect(result[1].id).toBe('2')
  })

  test('deve lidar com erros de conexão', async () => {
    ;(getDocs as jest.Mock).mockRejectedValueOnce(new Error('Erro de conexão'))

    await expect(getCachedEvaluations('7d')).rejects.toThrow('Erro de conexão')
  })
}) 