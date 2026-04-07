const joinKey = (...parts) => parts.join('.')

const readViteEnv = (key) => {
  if (typeof import.meta === 'undefined' || !import.meta.env) {
    return undefined
  }
  return import.meta.env[key]
}

export const API_BASE_URL = readViteEnv('VITE_API_URL') || '/api/v1'

export const CLIENT_STORAGE_KEYS = Object.freeze({
  sessionAccess: joinKey('worknest', 'session', 'a'),
  sessionRefresh: joinKey('worknest', 'session', 'r'),
  sessionUser: joinKey('worknest', 'session', 'u'),
  workspacePrefs: joinKey('worknest', 'ui', 'prefs'),
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
