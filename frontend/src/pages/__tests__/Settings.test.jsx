import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import Settings from '../Settings'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => action)
const updateProfile = vi.fn()
const getProfile = vi.fn()
const getNotificationPreferences = vi.fn()
const updateNotificationPreferences = vi.fn()
const updatePhoneSettings = vi.fn()
const requestCredentialChange = vi.fn()
const confirmCredentialChange = vi.fn()

const currentUser = {
  id: 'user-1',
  name: 'Victor',
  email: 'victor@example.com',
  phone_number: '+254711000001',
  phone_country_code: '+254',
  phone_verified: false,
  sms_opt_in: true,
  email_verified: true,
}

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) => selector({ auth: { user: currentUser } }),
  }
})

vi.mock('../../services/api', () => ({
  usersAPI: {
    getProfile: (...args) => getProfile(...args),
    getNotificationPreferences: (...args) => getNotificationPreferences(...args),
    updateProfile: (...args) => updateProfile(...args),
    updateNotificationPreferences: (...args) => updateNotificationPreferences(...args),
    updatePhoneSettings: (...args) => updatePhoneSettings(...args),
    requestCredentialChange: (...args) => requestCredentialChange(...args),
    confirmCredentialChange: (...args) => confirmCredentialChange(...args),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
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

test('Settings saves notification preferences and same-number SMS settings together', async () => {
  const user = userEvent.setup()
  getProfile
    .mockResolvedValueOnce({
      data: {
        data: {
          ...currentUser,
        },
      },
    })
    .mockResolvedValueOnce({
      data: {
        data: {
          ...currentUser,
          phone_verified: true,
        },
      },
    })
  getNotificationPreferences.mockResolvedValueOnce({
    data: {
      data: {
        channels: {
          in_app: { task_assigned: false },
          email: { mentioned_in_comment: false },
        },
        mention_sms: true,
        task_assignment_sms: true,
        deadline_reminder_sms: true,
        invite_sms: true,
        broadcast_sms: false,
      },
    },
  })
  updateProfile.mockResolvedValueOnce({ data: { data: currentUser } })
  updateNotificationPreferences.mockResolvedValueOnce({ data: { data: {} } })
  updatePhoneSettings.mockResolvedValueOnce({ data: { data: currentUser } })

  render(
    <TestMemoryRouter>
      <Settings />
    </TestMemoryRouter>
  )

  await waitFor(() => expect(getProfile).toHaveBeenCalled())

  await user.click(screen.getByLabelText(/Admin broadcasts/i))
  await user.click(screen.getByRole('button', { name: /Save preferences/i }))

  await waitFor(() => {
    expect(updateNotificationPreferences).toHaveBeenCalledWith(
      expect.objectContaining({
        channels: expect.objectContaining({
          in_app: expect.objectContaining({ task_assigned: false }),
          email: expect.objectContaining({ mentioned_in_comment: false }),
        }),
        broadcast_sms: true,
      })
    )
  })
  expect(updatePhoneSettings).toHaveBeenCalledWith(
    expect.objectContaining({
      phone_number: '+254711000001',
      phone_country_code: '+254',
      sms_opt_in: true,
    })
  )
})

test('Settings requests email change verification before updating sign-in credentials', async () => {
  const user = userEvent.setup()
  getProfile.mockResolvedValueOnce({ data: { data: currentUser } })
  getNotificationPreferences.mockResolvedValueOnce({ data: { data: { channels: { in_app: {}, email: {} } } } })
  requestCredentialChange.mockResolvedValueOnce({ data: { data: currentUser } })

  render(
    <TestMemoryRouter>
      <Settings />
    </TestMemoryRouter>
  )

  await waitFor(() => expect(getProfile).toHaveBeenCalled())

  const emailInputs = screen.getAllByPlaceholderText('name@example.com')
  await user.clear(emailInputs[0])
  await user.type(emailInputs[0], 'updated@example.com')
  await user.click(screen.getByRole('button', { name: /Send email code/i }))

  await waitFor(() =>
    expect(requestCredentialChange).toHaveBeenCalledWith({
      credential_type: 'email',
      new_value: 'updated@example.com',
    })
  )
})
