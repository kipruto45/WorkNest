import { z } from 'zod'

export const invitationFormSchema = z.object({
  email: z.string().trim().email('Enter a valid email address'),
  role: z.enum(['admin', 'manager', 'member']),
  custom_message: z.string().trim().max(1000, 'Message must be 1000 characters or fewer').optional().default(''),
})

export const inviteLinkFormSchema = z.object({
  role: z.enum(['admin', 'manager', 'member']).optional().default('member'),
  label: z.string().trim().max(255).optional().default(''),
  expires_at: z.string().optional().nullable(),
  max_uses: z.number().int().positive().optional().nullable(),
})

export function buildInvitationPath(token = '') {
  return `/invitations/${token}`
}

export function buildInvitationAuthHref({ token = '', mode = 'login' }) {
  const next = encodeURIComponent(buildInvitationPath(token))
  return mode === 'register' ? `/register?next=${next}` : `/login?next=${next}`
}

export function buildInviteLinkPath(token = '') {
  return `/invite-links/${token}`
}

export function buildInviteLinkAuthHref({ token = '', mode = 'login' }) {
  const next = encodeURIComponent(buildInviteLinkPath(token))
  return mode === 'register' ? `/register?next=${next}` : `/login?next=${next}`
}

export function buildInviteLinkUrl(token) {
  const origin = window.location.origin
  return `${origin}${buildInviteLinkPath(token)}`
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

export function canManageInviteLinks(role) {
  return role === 'admin'
}

export function canCreateInviteLink(role) {
  return role === 'admin'
}
