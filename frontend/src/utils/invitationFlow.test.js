import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildInvitationAuthHref,
  buildInvitationPath,
  canEditInvitation,
  canManageInvitePolicy,
  canRevokeOrResendInvitation,
  invitationFormSchema,
} from './invitationFlow.js'

test('invitation form schema validates and trims input', () => {
  const parsed = invitationFormSchema.parse({
    email: '  invitee@example.com ',
    role: 'member',
    custom_message: '  Welcome aboard  ',
  })

  assert.equal(parsed.email, 'invitee@example.com')
  assert.equal(parsed.custom_message, 'Welcome aboard')
})

test('invitation form schema rejects invalid emails', () => {
  const result = invitationFormSchema.safeParse({
    email: 'bad-email',
    role: 'member',
    custom_message: '',
  })

  assert.equal(result.success, false)
})

test('auth href preserves the invitation token', () => {
  assert.equal(buildInvitationPath('abc123'), '/invitations/abc123')
  assert.equal(buildInvitationAuthHref({ token: 'abc123', mode: 'login' }), '/login?next=%2Finvitations%2Fabc123')
  assert.equal(buildInvitationAuthHref({ token: 'abc123', mode: 'register' }), '/register?next=%2Finvitations%2Fabc123')
})

test('invite management helpers expose correct action availability', () => {
  assert.equal(canManageInvitePolicy('admin'), true)
  assert.equal(canManageInvitePolicy('manager'), false)
  assert.equal(canEditInvitation({ status: 'pending' }), true)
  assert.equal(canEditInvitation({ status: 'accepted' }), false)
  assert.equal(canRevokeOrResendInvitation({ status: 'pending' }), true)
  assert.equal(canRevokeOrResendInvitation({ status: 'revoked' }), false)
})
