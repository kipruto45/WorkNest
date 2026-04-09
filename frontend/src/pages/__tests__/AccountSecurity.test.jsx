import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import AccountSecurity from '../AccountSecurity'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => action)
const getSessions = vi.fn()
const getPushDevices = vi.fn()

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) =>
      selector({
        auth: {
          user: {
            id: 'user-1',
            email: 'victor@example.com',
            email_verified: true,
            two_factor_status: 'disabled',
          },
        },
      }),
  }
})

vi.mock('../../services/api', () => ({
  authAPI: {
    getSessions: (...args) => getSessions(...args),
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
    revokeSession: vi.fn(),
  },
  usersAPI: {
    getPushDevices: (...args) => getPushDevices(...args),
    removePushDevice: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

vi.mock('../../features/authSlice', () => ({
  setUser: (payload) => ({ type: 'auth/setUser', payload }),
}))

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

test('AccountSecurity still renders when push devices fail to load', async () => {
  getSessions.mockResolvedValueOnce({
    data: {
      data: [{ id: 'session-1', device_name: 'Chrome', status: 'active', ip_address: '127.0.0.1', user_agent: 'UA' }],
    },
  })
  getPushDevices.mockRejectedValueOnce(new Error('offline'))

  render(
    <TestMemoryRouter>
      <AccountSecurity />
    </TestMemoryRouter>
  )

  await waitFor(() => expect(screen.getByText(/Recent devices/i)).toBeInTheDocument())
  expect(screen.getByText('Chrome')).toBeInTheDocument()
  expect(screen.getByText(/Some security data is temporarily unavailable/i)).toBeInTheDocument()
  expect(screen.getByText(/Push device details are temporarily unavailable/i)).toBeInTheDocument()
})
