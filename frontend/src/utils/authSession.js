import { CLIENT_STORAGE_KEYS } from './clientConfig.js'

const CURRENT_USER_REQUIRED_KEYS = ['auth_provider', 'email_verified', 'notification_preferences', 'profile_completion']

export function extractAuthSession(payload) {
  const tokens = payload?.tokens
  const user = payload?.user ?? null
  const accessToken = tokens?.access ?? null
  const refreshToken = tokens?.refresh ?? null

  return {
    user,
    accessToken,
    refreshToken,
    isValid: Boolean(accessToken),
  }
}

export function hasCompleteCurrentUser(user) {
  if (!user || typeof user !== 'object') {
    return false
  }

  return CURRENT_USER_REQUIRED_KEYS.every((key) => Object.prototype.hasOwnProperty.call(user, key))
}

export function persistAuthSession(session) {
  if (!session?.accessToken) {
    return false
  }

  localStorage.setItem(CLIENT_STORAGE_KEYS.sessionAccess, session.accessToken)

  if (session.refreshToken) {
    localStorage.setItem(CLIENT_STORAGE_KEYS.sessionRefresh, session.refreshToken)
  }

  if (session.user) {
    localStorage.setItem(CLIENT_STORAGE_KEYS.sessionUser, JSON.stringify(session.user))
  }

  return true
}

export function persistCurrentUser(user) {
  if (!user) {
    localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
    return false
  }

  localStorage.setItem(CLIENT_STORAGE_KEYS.sessionUser, JSON.stringify(user))
  return true
}

export function clearAuthSession() {
  localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionAccess)
  localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionRefresh)
  localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
}
