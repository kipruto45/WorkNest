import test from 'node:test'
import assert from 'node:assert/strict'

import { buildNotificationLink } from './notificationLinks.js'

test('buildNotificationLink returns the task route when task metadata is present', () => {
  assert.equal(
    buildNotificationLink({ metadata: { task_id: 'task-1' } }),
    '/tasks/task-1'
  )
})

test('buildNotificationLink returns a comment deep link when comment metadata is present', () => {
  assert.equal(
    buildNotificationLink({ metadata: { task_id: 'task-1', comment_id: 'comment-2' } }),
    '/tasks/task-1?comment=comment-2'
  )
})

test('buildNotificationLink returns invitation workspace routes for invite-related notifications', () => {
  assert.equal(
    buildNotificationLink({ type: 'team_invite', metadata: { team_id: 'team-1' } }),
    '/teams/team-1/invitations'
  )
})
