import { CLIENT_STORAGE_KEYS } from './clientConfig.js'

export const THEME_OPTIONS = Object.freeze({
  light: 'light',
})

export const readStoredThemePreference = () => {
  try {
    const value = localStorage.getItem(CLIENT_STORAGE_KEYS.themePreference)
    return value === THEME_OPTIONS.light ? THEME_OPTIONS.light : THEME_OPTIONS.light
  } catch (_error) {
    return THEME_OPTIONS.light
  }
}

export const persistThemePreference = (value) => {
  try {
    localStorage.setItem(CLIENT_STORAGE_KEYS.themePreference, value === THEME_OPTIONS.light ? THEME_OPTIONS.light : THEME_OPTIONS.light)
    return true
  } catch (_error) {
    return false
  }
}

export const resolveThemeMode = () => THEME_OPTIONS.light

export const applyThemePreference = () => {
  const nextPreference = THEME_OPTIONS.light
  const resolvedMode = resolveThemeMode()

  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolvedMode
    document.documentElement.dataset.themePreference = nextPreference
    document.body.dataset.theme = resolvedMode
  }

  persistThemePreference(nextPreference)
  return resolvedMode
}
