import test from 'node:test'
import assert from 'node:assert/strict'

import { resolvePostAuthPath, sanitizeNextPath } from './authRouting.js'

test('sanitizeNextPath accepts safe in-app paths and rejects open redirects', () => {
  assert.equal(sanitizeNextPath('/dashboard'), '/dashboard')
  assert.equal(sanitizeNextPath('  /teams/123/overview '), '/teams/123/overview')
  assert.equal(sanitizeNextPath('https://evil.example.com'), '')
  assert.equal(sanitizeNextPath('//evil.example.com'), '')
})

test('resolvePostAuthPath routes users to the correct workspace', () => {
  assert.equal(resolvePostAuthPath({ nextPath: '/tasks', user: { is_staff: false } }), '/tasks')
  assert.equal(resolvePostAuthPath({ nextPath: '/admin', user: { is_staff: false } }), '/403')
  assert.equal(resolvePostAuthPath({ nextPath: '/dashboard', user: { is_staff: true } }), '/admin')
  assert.equal(
    resolvePostAuthPath({
      nextPath: '',
      user: { is_staff: false, account_type: 'team', default_team_id: 'team-1' },
    }),
    '/teams/team-1/overview'
  )
  assert.equal(resolvePostAuthPath({ nextPath: '', user: { is_staff: false, account_type: 'personal' } }), '/dashboard')
})
