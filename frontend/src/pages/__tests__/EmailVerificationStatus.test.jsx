import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import EmailVerificationStatus from '../EmailVerificationStatus'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn()
const verifyEmailMock = vi.fn()
const resendVerificationMock = vi.fn()

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) =>
      selector({
        auth: {
          token: 'token-1',
          user: { id: 'user-1', email: 'alex@example.com', email_verified: false },
        },
      }),
  }
})

vi.mock('../../services/api', () => ({
  authAPI: {
    verifyEmail: (...args) => verifyEmailMock(...args),
    resendVerification: (...args) => resendVerificationMock(...args),
  },
  unwrapData: (response) => response?.data?.data ?? null,
}))

vi.mock('../../features/authSlice', () => ({
  setUser: (user) => ({ type: 'auth/setUser', payload: user }),
}))

test('EmailVerificationStatus verifies token from the URL', async () => {
  verifyEmailMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'user-1',
        email: 'alex@example.com',
        email_verified: true,
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/verify-email?token=abc123']}>
      <Routes>
        <Route path="/verify-email" element={<EmailVerificationStatus />} />
      </Routes>
    </TestMemoryRouter>
  )

  await waitFor(() => expect(verifyEmailMock).toHaveBeenCalledWith({ token: 'abc123' }))
  expect(await screen.findByText(/Your email address is verified/i)).toBeInTheDocument()
})

test('EmailVerificationStatus can resend verification for signed-in users', async () => {
  resendVerificationMock.mockResolvedValueOnce({ data: { data: { delivery: { status: 'sent' } } } })

  render(
    <TestMemoryRouter initialEntries={['/verify-email']}>
      <Routes>
        <Route path="/verify-email" element={<EmailVerificationStatus />} />
      </Routes>
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Resend verification email/i }))

  await waitFor(() => expect(resendVerificationMock).toHaveBeenCalled())
  expect(await screen.findByText(/fresh verification link was sent/i)).toBeInTheDocument()
})
