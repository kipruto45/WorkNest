import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import AdminCommunications from '../AdminCommunications'

const getAdminCommunications = vi.fn()
const createAdminCommunication = vi.fn()
const searchAdminUsers = vi.fn()
const searchAdminTeams = vi.fn()

vi.mock('../../services/api', () => ({
  notificationsAPI: {
    getAdminCommunications: (...args) => getAdminCommunications(...args),
    createAdminCommunication: (...args) => createAdminCommunication(...args),
  },
  usersAPI: {
    searchAdminUsers: (...args) => searchAdminUsers(...args),
  },
  teamsAPI: {
    searchAdminTeams: (...args) => searchAdminTeams(...args),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => {
    const payload = response?.data?.data ?? response?.data ?? null
    if (Array.isArray(payload?.results)) return payload.results
    if (Array.isArray(payload)) return payload
    return []
  },
}))

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

beforeEach(() => {
  getAdminCommunications.mockReset()
  createAdminCommunication.mockReset()
  searchAdminUsers.mockReset()
  searchAdminTeams.mockReset()
})

test('Admin communications sends payload for selected users', async () => {
  const user = userEvent.setup()
  getAdminCommunications.mockResolvedValueOnce({ data: { data: { results: [] } } })
  searchAdminUsers.mockResolvedValueOnce({
    data: { data: { results: [{ id: 'user-1', name: 'Jane Doe', email: 'jane@example.com' }] } },
  })
  createAdminCommunication.mockResolvedValueOnce({
    data: { data: { id: 'comm-1', title: 'Update', message: 'Hello' } },
  })

  render(<AdminCommunications />)

  await waitFor(() => expect(getAdminCommunications).toHaveBeenCalled())

  await user.click(screen.getByRole('button', { name: /Selected Users/i }))
  await user.type(screen.getByPlaceholderText('Search users by name or email'), 'Jane')

  await waitFor(() => expect(searchAdminUsers).toHaveBeenCalled())
  await user.click(screen.getByText('Jane Doe'))

  await user.type(screen.getByPlaceholderText('Title for the communication'), 'Update')
  await user.type(screen.getByPlaceholderText('Write a clear update for your users'), 'Hello')

  await user.click(screen.getByRole('button', { name: /Send communication/i }))

  await waitFor(() =>
    expect(createAdminCommunication).toHaveBeenCalledWith(
      expect.objectContaining({
        audience_type: 'selected_users',
        channel_type: 'email_and_in_app',
        title: 'Update',
        message: 'Hello',
        user_ids: ['user-1'],
      })
    )
  )
}, 10000)

test('Admin communications requires confirmation before SMS send', async () => {
  const user = userEvent.setup()
  getAdminCommunications.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(<AdminCommunications />)

  await waitFor(() => expect(getAdminCommunications).toHaveBeenCalled())

  await user.click(screen.getByRole('button', { name: /SMS only/i }))
  await user.type(screen.getByPlaceholderText('Title for the communication'), 'SMS Update')
  await user.type(screen.getByPlaceholderText('Write a clear update for your users'), 'Hello by text')
  await user.click(screen.getByRole('button', { name: /Send communication/i }))

  await waitFor(() => {
    expect(createAdminCommunication).toHaveBeenCalledTimes(0)
  })
})
