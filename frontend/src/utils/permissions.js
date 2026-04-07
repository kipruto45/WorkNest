export function resolveMembershipRole(source) {
  return source?.my_membership?.role || source?.my_role || source?.role || null
}

export function canManageInvitations({ role, allowManagerInvites = false }) {
  if (role === 'admin') return true
  return role === 'manager' && allowManagerInvites
}

export function canManageInvitePolicy(role) {
  return role === 'admin'
}

export function canCreateTask(role) {
  return role === 'admin' || role === 'manager' || role === 'member'
}

export function canManageTask(role) {
  return role === 'admin' || role === 'manager'
}

export function canDeleteTask(role) {
  return role === 'admin'
}

export function canAssignTask(role) {
  return canManageTask(role)
}

export function canChangeTaskStatus({ role, currentUserId, assignedToId }) {
  if (canManageTask(role)) return true
  return role === 'member' && Boolean(currentUserId && assignedToId && String(currentUserId) === String(assignedToId))
}

export function canManageMembers(role) {
  return role === 'admin'
}

export function canModerateComments(role) {
  return role === 'admin' || role === 'manager'
}

export function canDeleteComment({ role, currentUserId, authorId }) {
  if (currentUserId && authorId && String(currentUserId) === String(authorId)) {
    return true
  }
  return canModerateComments(role)
}
