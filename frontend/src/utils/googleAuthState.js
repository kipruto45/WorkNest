import { CLIENT_STORAGE_KEYS } from './clientConfig.js'

const safeSessionStorage = () => {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return window.sessionStorage
  } catch (_error) {
    return null
  }
}

export const beginGoogleAuth = ({ flow, accountType = '', nextPath = '' }) => {
  const storage = safeSessionStorage()
  if (!storage) return

  storage.setItem(
    CLIENT_STORAGE_KEYS.googleAuthState,
    JSON.stringify({
      flow: flow === 'register' ? 'register' : 'login',
      accountType: String(accountType || '').trim(),
      nextPath: String(nextPath || '').trim(),
      startedAt: Date.now(),
    })
  )
}

export const readGoogleAuthState = () => {
  const storage = safeSessionStorage()
  if (!storage) {
    return null
  }

  const rawValue = storage.getItem(CLIENT_STORAGE_KEYS.googleAuthState)
  if (!rawValue) {
    return null
  }

  try {
    const parsed = JSON.parse(rawValue)
    if (!parsed || typeof parsed !== 'object') {
      return null
    }
    return {
      flow: parsed.flow === 'register' ? 'register' : 'login',
      accountType: typeof parsed.accountType === 'string' ? parsed.accountType : '',
      nextPath: typeof parsed.nextPath === 'string' ? parsed.nextPath : '',
      startedAt: Number(parsed.startedAt) || Date.now(),
    }
  } catch (_error) {
    return null
  }
}

export const clearGoogleAuthState = () => {
  const storage = safeSessionStorage()
  if (!storage) return
  storage.removeItem(CLIENT_STORAGE_KEYS.googleAuthState)
}
