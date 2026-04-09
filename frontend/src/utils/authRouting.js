export const sanitizeNextPath = (value) => {
  const candidate = typeof value === 'string' ? value.trim() : ''
  if (!candidate.startsWith('/')) {
    return ''
  }
  if (candidate.startsWith('//')) {
    return ''
  }
  return candidate
}

export const resolvePostAuthPath = ({ nextPath, user }) => {
  const sanitizedNextPath = sanitizeNextPath(nextPath)

  if (sanitizedNextPath && !['/', '/dashboard'].includes(sanitizedNextPath)) {
    if (sanitizedNextPath.startsWith('/admin') && !user?.is_staff) {
      return '/403'
    }
    return sanitizedNextPath
  }

  if (user?.is_staff) {
    return '/admin'
  }

  if (user?.account_type === 'team') {
    return user?.default_team_id ? `/teams/${user.default_team_id}/overview` : '/team-setup'
  }

  return '/dashboard'
}
