import { z } from 'zod'

export const invitationFormSchema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  role: z.enum(['admin', 'manager', 'member']),
  custom_message: z.string().trim().max(1000, 'Message must be 1000 characters or fewer').optional().default(''),
})

export function buildInvitationPath(token = '') {
  return `/invitations/${token}`
}

export function buildInvitationAuthHref({ token = '', mode = 'login' }) {
  const next = encodeURIComponent(buildInvitationPath(token))
  return mode === 'register' ? `/register?next=${next}` : `/login?next=${next}`
}

export function canManageInvitePolicy(role) {
  return role === 'admin'
}

export function canEditInvitation(invitation) {
  return invitation?.status !== 'accepted'
}

export function canRevokeOrResendInvitation(invitation) {
  return !['accepted', 'revoked'].includes(invitation?.status)
}
