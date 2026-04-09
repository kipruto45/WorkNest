import test from 'node:test'
import assert from 'node:assert/strict'

import { CLIENT_STORAGE_KEYS } from './clientConfig.js'
import { clearAuthSession, extractAuthSession, hasCompleteCurrentUser, persistAuthSession, persistCurrentUser } from './authSession.js'

test('extractAuthSession returns a valid session for auth payloads', () => {
  const session = extractAuthSession({
    user: { id: '1', email: 'user@example.com' },
    tokens: {
      access: 'access-token',
      refresh: 'refresh-token',
    },
  })

  assert.equal(session.isValid, true)
  assert.equal(session.accessToken, 'access-token')
  assert.equal(session.refreshToken, 'refresh-token')
  assert.deepEqual(session.user, { id: '1', email: 'user@example.com' })
})

test('extractAuthSession handles empty payloads safely', () => {
  const session = extractAuthSession(null)

  assert.equal(session.isValid, false)
  assert.equal(session.accessToken, null)
  assert.equal(session.refreshToken, null)
  assert.equal(session.user, null)
})

test('hasCompleteCurrentUser detects partial cached auth users', () => {
  assert.equal(
    hasCompleteCurrentUser({ id: '1', email: 'user@example.com', name: 'User Example' }),
    false
  )

  assert.equal(
    hasCompleteCurrentUser({
      id: '1',
      email: 'user@example.com',
      name: 'User Example',
      auth_provider: 'google',
      email_verified: true,
      notification_preferences: {},
      profile_completion: 50,
    }),
    true
  )
})

test('persistCurrentUser stores the serialized user in localStorage', () => {
  const store = new Map()
  global.localStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
  }

  const result = persistCurrentUser({ id: '1', email: 'user@example.com' })

  assert.equal(result, true)
  assert.equal(store.get(CLIENT_STORAGE_KEYS.sessionUser), JSON.stringify({ id: '1', email: 'user@example.com' }))
})

test('persistAuthSession removes stale refresh tokens when the new session only uses cookies', () => {
  const store = new Map([[CLIENT_STORAGE_KEYS.sessionRefresh, 'stale-refresh-token']])
  global.localStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
  }

  const result = persistAuthSession({
    accessToken: 'fresh-access-token',
    refreshToken: null,
    user: { id: '1', email: 'user@example.com' },
  })

  assert.equal(result, true)
  assert.equal(store.get(CLIENT_STORAGE_KEYS.sessionAccess), 'fresh-access-token')
  assert.equal(store.has(CLIENT_STORAGE_KEYS.sessionRefresh), false)
})

test('clearAuthSession removes all auth keys from localStorage', () => {
  const store = new Map([
    [CLIENT_STORAGE_KEYS.sessionAccess, 'access'],
    [CLIENT_STORAGE_KEYS.sessionRefresh, 'refresh'],
    [CLIENT_STORAGE_KEYS.sessionUser, '{"id":"1"}'],
  ])
  global.localStorage = {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: (key) => store.delete(key),
  }

  clearAuthSession()

  assert.equal(store.has(CLIENT_STORAGE_KEYS.sessionAccess), false)
  assert.equal(store.has(CLIENT_STORAGE_KEYS.sessionRefresh), false)
  assert.equal(store.has(CLIENT_STORAGE_KEYS.sessionUser), false)
})
