import test from 'node:test'
import assert from 'node:assert/strict'

import { extractApiError } from './apiErrors.js'

test('extractApiError prefers backend field validation messages over generic payload messages', () => {
  const error = {
    response: {
      status: 400,
      data: {
        success: false,
        message: 'Validation failed.',
        errors: {
          name: ['Team name is required.'],
        },
      },
    },
  }

  const result = extractApiError(error, { fallbackMessage: 'Failed to create team' })

  assert.equal(result.message, 'Team name is required.')
  assert.deepEqual(result.fieldErrors, { name: ['Team name is required.'] })
})

test('extractApiError maps authentication failures to a session-expired message', () => {
  const error = {
    response: {
      status: 401,
      data: {
        success: false,
        message: 'Authentication credentials were not provided or are invalid.',
        errors: {
          detail: 'Given token not valid for any token type',
        },
      },
    },
  }

  const result = extractApiError(error)

  assert.equal(result.message, 'Your session expired. Please log in again.')
})

test('extractApiError returns a network-specific fallback when no response is available', () => {
  const result = extractApiError({ code: 'ERR_NETWORK', message: 'Network Error' })

  assert.equal(result.message, 'Could not connect to the server.')
  assert.equal(result.isNetworkError, true)
})

test('extractApiError maps server failures to a clean fallback message', () => {
  const error = {
    response: {
      status: 500,
      data: {
        success: false,
        message: 'An unexpected error occurred.',
        errors: { detail: 'Internal server error.' },
      },
    },
  }

  const result = extractApiError(error, { serverMessage: 'Server error while creating team.' })

  assert.equal(result.message, 'Server error while creating team.')
})
