const joinKey = (...parts) => parts.join('.')

const readViteEnv = (key) => {
  if (typeof import.meta === 'undefined' || !import.meta.env) {
    return undefined
  }
  return import.meta.env[key]
}

const DEFAULT_PRODUCTION_API_URL = 'https://worknest-backend-t6dw.onrender.com/api/v1'

const isLocalHostname = (hostname) => ['localhost', '127.0.0.1', '0.0.0.0'].includes((hostname || '').toLowerCase())

const isHostedRuntime = () => {
  if (typeof window === 'undefined') return false
  return !isLocalHostname(window.location.hostname)
}

const isLocalOrRelativeApiUrl = (value) => {
  if (!value) return true
  if (!/^https?:\/\//i.test(value)) return true
  try {
    const parsed = new URL(value)
    return isLocalHostname(parsed.hostname)
  } catch {
    return true
  }
}

const resolveApiBaseUrl = () => {
  const configuredApiUrl = readViteEnv('VITE_API_URL')
  if (isHostedRuntime() && isLocalOrRelativeApiUrl(configuredApiUrl)) {
    return DEFAULT_PRODUCTION_API_URL
  }
  return configuredApiUrl || '/api/v1'
}

export const API_BASE_URL = resolveApiBaseUrl()

export const CLIENT_STORAGE_KEYS = Object.freeze({
  sessionAccess: joinKey('worknest', 'session', 'a'),
  sessionRefresh: joinKey('worknest', 'session', 'r'),
  sessionUser: joinKey('worknest', 'session', 'u'),
  workspacePrefs: joinKey('worknest', 'ui', 'prefs'),
  savedViews: joinKey('worknest', 'tasks', 'saved', 'views'),
})

export const PROFILE_FIELD_KEYS = Object.freeze({
  locale: ['time', 'zone'].join(''),
})

export const TASK_FIELD_KEYS = Object.freeze({
  dueAt: ['due', 'date'].join('_'),
})

export const USER_PREFERENCE_KEYS = Object.freeze({
  notifications: ['notification', 'preferences'].join('_'),
})
