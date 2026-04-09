import { CLIENT_STORAGE_KEYS } from './clientConfig.js'

export const THEME_OPTIONS = Object.freeze({
  system: 'system',
  light: 'light',
  dark: 'dark',
})

export const readStoredThemePreference = () => {
  try {
    const value = localStorage.getItem(CLIENT_STORAGE_KEYS.themePreference)
    if (!value) return THEME_OPTIONS.system
    return Object.values(THEME_OPTIONS).includes(value) ? value : THEME_OPTIONS.system
  } catch (_error) {
    return THEME_OPTIONS.system
  }
}

export const persistThemePreference = (value) => {
  try {
    localStorage.setItem(CLIENT_STORAGE_KEYS.themePreference, value)
    return true
  } catch (_error) {
    return false
  }
}

export const resolveThemeMode = (preference) => {
  if (preference === THEME_OPTIONS.light) return THEME_OPTIONS.light
  if (preference === THEME_OPTIONS.dark) return THEME_OPTIONS.dark
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return THEME_OPTIONS.dark
  }
  return THEME_OPTIONS.light
}

export const applyThemePreference = (preference) => {
  const nextPreference = Object.values(THEME_OPTIONS).includes(preference) ? preference : THEME_OPTIONS.system
  const resolvedMode = resolveThemeMode(nextPreference)

  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolvedMode
    document.documentElement.dataset.themePreference = nextPreference
    document.body.dataset.theme = resolvedMode
  }

  persistThemePreference(nextPreference)
  return resolvedMode
}
