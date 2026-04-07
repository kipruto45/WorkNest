import test from 'node:test'
import assert from 'node:assert/strict'

import {
  canAssignTask,
  canChangeTaskStatus,
  canCreateTask,
  canDeleteComment,
  canDeleteTask,
  canManageInvitations,
  canManageMembers,
  canManageTask,
  resolveMembershipRole,
} from './permissions.js'

test('resolveMembershipRole reads nested membership first', () => {
  assert.equal(resolveMembershipRole({ my_membership: { role: 'manager' }, my_role: 'member' }), 'manager')
  assert.equal(resolveMembershipRole({ my_role: 'admin' }), 'admin')
  assert.equal(resolveMembershipRole(null), null)
})

test('task permission helpers respect role constraints', () => {
  assert.equal(canCreateTask('admin'), true)
  assert.equal(canCreateTask('manager'), true)
  assert.equal(canCreateTask('member'), true)
  assert.equal(canManageTask('manager'), true)
  assert.equal(canDeleteTask('manager'), false)
  assert.equal(canAssignTask('admin'), true)
})

test('members can only change status for tasks assigned to them', () => {
  assert.equal(
    canChangeTaskStatus({ role: 'member', currentUserId: 'u1', assignedToId: 'u1' }),
    true
  )
  assert.equal(
    canChangeTaskStatus({ role: 'member', currentUserId: 'u1', assignedToId: 'u2' }),
    false
  )
  assert.equal(
    canChangeTaskStatus({ role: 'manager', currentUserId: 'u1', assignedToId: 'u2' }),
    true
  )
})

test('team invitation and member management helpers align with backend rules', () => {
  assert.equal(canManageInvitations({ role: 'admin', allowManagerInvites: false }), true)
  assert.equal(canManageInvitations({ role: 'manager', allowManagerInvites: true }), true)
  assert.equal(canManageInvitations({ role: 'manager', allowManagerInvites: false }), false)
  assert.equal(canManageMembers('admin'), true)
  assert.equal(canManageMembers('manager'), false)
})

test('comment deletion allows authors and moderators only', () => {
  assert.equal(canDeleteComment({ role: 'member', currentUserId: 'u1', authorId: 'u1' }), true)
  assert.equal(canDeleteComment({ role: 'manager', currentUserId: 'u2', authorId: 'u1' }), true)
  assert.equal(canDeleteComment({ role: 'member', currentUserId: 'u2', authorId: 'u1' }), false)
})
