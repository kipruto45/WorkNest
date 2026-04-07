import test from 'node:test'
import assert from 'node:assert/strict'

import { buildRealtimeUrl } from './realtime.js'

global.window = {
  location: {
    origin: 'http://localhost:5173',
  },
}

test('buildRealtimeUrl converts API URLs into websocket URLs', () => {
  const url = buildRealtimeUrl({
    apiUrl: 'http://localhost:8000/api/v1',
    accessToken: 'token-123',
    path: '/ws/notifications/',
  })

  assert.equal(url, 'ws://localhost:8000/ws/notifications/?token=token-123')
})

test('buildRealtimeUrl resolves relative API URLs against the current origin', () => {
  const url = buildRealtimeUrl({
    apiUrl: '/api/v1',
    accessToken: 'token-123',
    path: '/ws/notifications/',
  })

  assert.equal(url, 'ws://localhost:5173/ws/notifications/?token=token-123')
})
