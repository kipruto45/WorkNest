const joinKey = (...parts) => parts.join('.')

const readViteEnv = (key) => {
  if (typeof import.meta === 'undefined' || !import.meta.env) {
    return undefined
  }
  return import.meta.env[key]
}

const isLocalHostname = (hostname) => ['localhost', '127.0.0.1', '0.0.0.0'].includes((hostname || '').toLowerCase())

const isHostedRuntime = () => {
  if (typeof window === 'undefined') return false
  return !isLocalHostname(window.location.hostname)
}

export const resolveApiBaseUrl = ({ configuredApiUrl = readViteEnv('VITE_API_URL'), hostedRuntime = isHostedRuntime() } = {}) => {
  const normalizedApiUrl = typeof configuredApiUrl === 'string' ? configuredApiUrl.trim() : ''

  if (normalizedApiUrl) {
    return normalizedApiUrl
  }

  if (hostedRuntime) {
    return '/api/v1'
  }

  return '/api/v1'
}

export const API_BASE_URL = resolveApiBaseUrl()

export const CLIENT_STORAGE_KEYS = Object.freeze({
  sessionAccess: joinKey('worknest', 'session', 'a'),
  sessionRefresh: joinKey('worknest', 'session', 'r'),
  sessionUser: joinKey('worknest', 'session', 'u'),
  googleAuthState: joinKey('worknest', 'auth', 'google'),
  workspacePrefs: joinKey('worknest', 'ui', 'prefs'),
  memberOnboardingTeams: joinKey('worknest', 'teams', 'member', 'onboarding'),
  themePreference: joinKey('worknest', 'ui', 'theme'),
  savedViews: joinKey('worknest', 'tasks', 'saved', 'views'),
})

export const PROFILE_FIELD_KEYS = Object.freeze({
  locale: ['time', 'zone'].join(''),
})

export const TASK_FIELD_KEYS = Object.freeze({
  dueAt: ['due', 'date'].join('_'),
  startAt: ['start', 'at'].join('_'),
})

export const USER_PREFERENCE_KEYS = Object.freeze({
  notifications: ['notification', 'preferences'].join('_'),
})
