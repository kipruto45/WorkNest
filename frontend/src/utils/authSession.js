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

export function persistAuthSession(session) {
  if (!session?.accessToken) {
    return false
  }

  localStorage.setItem('access_token', session.accessToken)

  if (session.refreshToken) {
    localStorage.setItem('refresh_token', session.refreshToken)
  }

  if (session.user) {
    localStorage.setItem('user', JSON.stringify(session.user))
  }

  return true
}

export function persistCurrentUser(user) {
  if (!user) {
    localStorage.removeItem('user')
    return false
  }

  localStorage.setItem('user', JSON.stringify(user))
  return true
}

export function clearAuthSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}
