import test from 'node:test'
import assert from 'node:assert/strict'

import {
  deriveInvitationViewState,
  resolveInvitationSubtitle,
  resolveInvitationTitle,
} from './invitationState.js'

const invitation = {
  email: 'invitee@example.com',
  status: 'pending',
  is_expired: false,
  team: { is_archived: false, description: 'Join the product delivery workspace.' },
}

test('deriveInvitationViewState returns auth_required for anonymous users', () => {
  assert.equal(
    deriveInvitationViewState({
      requestState: 'ready',
      invitation,
      currentEmail: '',
    }),
    'auth_required'
  )
})

test('deriveInvitationViewState returns mismatch for wrong account', () => {
  assert.equal(
    deriveInvitationViewState({
      requestState: 'ready',
      invitation,
      currentEmail: 'wrong@example.com',
    }),
    'mismatch'
  )
})

test('deriveInvitationViewState returns actionable for matching account', () => {
  assert.equal(
    deriveInvitationViewState({
      requestState: 'ready',
      invitation,
      currentEmail: 'invitee@example.com',
    }),
    'actionable'
  )
})

test('deriveInvitationViewState returns expired when invitation is expired', () => {
  assert.equal(
    deriveInvitationViewState({
      requestState: 'ready',
      invitation: { ...invitation, is_expired: true },
      currentEmail: 'invitee@example.com',
    }),
    'expired'
  )
})

test('resolve helpers return the expected copy', () => {
  assert.equal(resolveInvitationTitle('mismatch'), 'Wrong account for this invite')
  assert.equal(
    resolveInvitationSubtitle('actionable', invitation),
    'Join the product delivery workspace.'
  )
})
