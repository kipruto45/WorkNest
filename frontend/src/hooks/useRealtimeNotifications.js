import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchUnreadCount, removeNotification, setUnreadCount, upsertNotification } from '../features/notificationsSlice'
import {
  buildRealtimeUrl,
  NOTIFICATION_CREATED_EVENT,
  NOTIFICATION_DELETED_EVENT,
  NOTIFICATION_UNREAD_COUNT_EVENT,
  NOTIFICATION_UPDATED_EVENT,
} from '../utils/realtime'
import { playNotificationSound } from '../utils/notificationSound'
import { API_BASE_URL, CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'

export function useRealtimeNotifications() {
  const dispatch = useDispatch()
  const token = useSelector((state) => state.auth.token)

  useEffect(() => {
    if (!token) {
      return undefined
    }

    let socket
    let reconnectTimer

    const resolveAccessToken = () => localStorage.getItem(CLIENT_STORAGE_KEYS.sessionAccess) || token

    const connect = () => {
      const accessToken = resolveAccessToken()
      if (!accessToken) {
        return
      }

      const socketUrl = buildRealtimeUrl({
        apiUrl: API_BASE_URL,
        accessToken,
        path: '/ws/notifications/',
      })

      socket = new WebSocket(socketUrl)

      socket.onopen = () => {
        dispatch(fetchUnreadCount())
      }

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === NOTIFICATION_CREATED_EVENT || payload.event === NOTIFICATION_UPDATED_EVENT) {
            dispatch(upsertNotification(payload.data))
            if (payload.event === NOTIFICATION_CREATED_EVENT) {
              playNotificationSound()
            }
            dispatch(fetchUnreadCount())
            return
          }
          if (payload.event === NOTIFICATION_DELETED_EVENT) {
            dispatch(removeNotification(payload.data.id))
            dispatch(fetchUnreadCount())
            return
          }
          if (payload.event === NOTIFICATION_UNREAD_COUNT_EVENT) {
            dispatch(setUnreadCount(payload.data.unread_count))
          }
        } catch (error) {
          // Ignore malformed socket payloads and recover on the next event.
        }
      }

      socket.onclose = (event) => {
        if (event.code === 4403) {
          return
        }
        if (event.code === 4401) {
          dispatch(fetchUnreadCount()).finally(() => {
            reconnectTimer = window.setTimeout(connect, 1500)
          })
          return
        }
        reconnectTimer = window.setTimeout(connect, 3000)
      }
    }

    connect()
    dispatch(fetchUnreadCount())

    return () => {
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
      if (socket && socket.readyState < WebSocket.CLOSING) {
        socket.close()
      }
    }
  }, [dispatch, token])
}
