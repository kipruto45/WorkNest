export const NOTIFICATION_CREATED_EVENT = 'notification.created'
export const NOTIFICATION_UPDATED_EVENT = 'notification.updated'
export const NOTIFICATION_DELETED_EVENT = 'notification.deleted'
export const NOTIFICATION_UNREAD_COUNT_EVENT = 'notification.unread_count'

export function buildRealtimeUrl({ apiUrl, accessToken, path }) {
  const rawApiUrl = apiUrl || '/api/v1'
  const resolvedApiUrl = rawApiUrl.startsWith('http')
    ? rawApiUrl
    : `${window.location.origin}${rawApiUrl.startsWith('/') ? rawApiUrl : `/${rawApiUrl}`}`
  const baseApiUrl = resolvedApiUrl.replace(/\/$/, '')
  const websocketBase = baseApiUrl.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:').replace(/\/api\/v1$/i, '')

  const url = new URL(`${websocketBase}${path}`)
  if (accessToken) {
    url.searchParams.set('token', accessToken)
  }
  return url.toString()
}
