import { db } from '../config/firebase'
import { collection, query, where, onSnapshot, Timestamp } from 'firebase/firestore'

export interface Notification {
  id: string
  type: 'new_evaluation' | 'new_complaint' | 'request_update' | 'system'
  title: string
  message: string
  timestamp: Date
  read: boolean
  data?: any
}

export const subscribeToNotifications = (
  callback: (notifications: Notification[]) => void
) => {
  // Buscar notificações dos últimos 7 dias
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 7)

  const q = query(
    collection(db, 'notifications'),
    where('timestamp', '>=', Timestamp.fromDate(startDate))
  )

  return onSnapshot(q, (snapshot) => {
    const notifications = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      timestamp: doc.data().timestamp.toDate()
    })) as Notification[]

    callback(notifications)
  })
}

export const markNotificationAsRead = async (notificationId: string) => {
  try {
    const notificationRef = doc(db, 'notifications', notificationId)
    await updateDoc(notificationRef, { read: true })
  } catch (error) {
    console.error('Erro ao marcar notificação como lida:', error)
    throw error
  }
}

export const createNotification = async (
  type: Notification['type'],
  title: string,
  message: string,
  data?: any
) => {
  try {
    const notificationsRef = collection(db, 'notifications')
    await addDoc(notificationsRef, {
      type,
      title,
      message,
      timestamp: Timestamp.now(),
      read: false,
      data
    })
  } catch (error) {
    console.error('Erro ao criar notificação:', error)
    throw error
  }
} 