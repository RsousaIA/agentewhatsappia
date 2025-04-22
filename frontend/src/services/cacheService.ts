import { db } from '../config/firebase'
import { collection, query, where, getDocs, Timestamp } from 'firebase/firestore'

interface CacheItem<T> {
  data: T
  timestamp: number
  expiresIn: number
}

class CacheService {
  private static instance: CacheService
  private cache: Map<string, CacheItem<any>>

  private constructor() {
    this.cache = new Map()
  }

  public static getInstance(): CacheService {
    if (!CacheService.instance) {
      CacheService.instance = new CacheService()
    }
    return CacheService.instance
  }

  public async get<T>(
    key: string,
    fetchFn: () => Promise<T>,
    expiresIn: number = 5 * 60 * 1000 // 5 minutos por padrão
  ): Promise<T> {
    const cached = this.cache.get(key)
    const now = Date.now()

    if (cached && now - cached.timestamp < cached.expiresIn) {
      return cached.data as T
    }

    const data = await fetchFn()
    this.cache.set(key, {
      data,
      timestamp: now,
      expiresIn
    })

    return data
  }

  public clear(key?: string) {
    if (key) {
      this.cache.delete(key)
    } else {
      this.cache.clear()
    }
  }
}

export const cacheService = CacheService.getInstance()

// Funções auxiliares para cache de dados específicos
export const getCachedEvaluations = async (period: '7d' | '30d' | '90d') => {
  const key = `evaluations_${period}`
  return cacheService.get(key, async () => {
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - (period === '7d' ? 7 : period === '30d' ? 30 : 90))
    
    const q = query(
      collection(db, 'evaluations'),
      where('timestamp', '>=', Timestamp.fromDate(startDate))
    )
    
    const snapshot = await getDocs(q)
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }))
  })
}

export const getCachedAttendances = async (period: '7d' | '30d' | '90d') => {
  const key = `attendances_${period}`
  return cacheService.get(key, async () => {
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - (period === '7d' ? 7 : period === '30d' ? 30 : 90))
    
    const q = query(
      collection(db, 'attendances'),
      where('timestamp', '>=', Timestamp.fromDate(startDate))
    )
    
    const snapshot = await getDocs(q)
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }))
  })
} 