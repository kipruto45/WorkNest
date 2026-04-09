import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveApiBaseUrl } from './clientConfig.js'

test('resolveApiBaseUrl prefers an explicitly configured API URL', () => {
  assert.equal(
    resolveApiBaseUrl({
      configuredApiUrl: 'https://api.example.com/api/v1',
      hostedRuntime: true,
    }),
    'https://api.example.com/api/v1'
  )
})

test('resolveApiBaseUrl falls back to the current origin api path instead of a hardcoded hosted backend', () => {
  assert.equal(
    resolveApiBaseUrl({
      configuredApiUrl: '',
      hostedRuntime: true,
    }),
    '/api/v1'
  )
})
