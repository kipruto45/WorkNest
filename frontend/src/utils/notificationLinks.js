export function buildNotificationLink(notification) {
  const metadata = notification?.metadata || {}

  if (metadata.task_id) {
    if (metadata.comment_id) {
      return `/tasks/${metadata.task_id}?comment=${metadata.comment_id}`
    }
    return `/tasks/${metadata.task_id}`
  }

  if (metadata.team_id && notification?.type === 'team_invite') {
    return `/teams/${metadata.team_id}/invitations`
  }

  if (metadata.team_id && ['invitation_accepted', 'invitation_declined'].includes(notification?.type)) {
    return `/teams/${metadata.team_id}/members`
  }

  if (metadata.team_id) {
    return `/teams/${metadata.team_id}/overview`
  }

  return '/notifications'
}
