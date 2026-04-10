import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamInvitations from '../TeamInvitations'
import { TestMemoryRouter } from '../../test/router'

const getTeamMock = vi.fn()
const getInvitationsMock = vi.fn()
const getInviteLinksMock = vi.fn()

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useSelector: (selector) =>
      selector({
        auth: {
          user: {
            id: 'user-1',
            is_staff: true,
          },
        },
      }),
  }
})

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: (...args) => getTeamMock(...args),
    getInvitations: (...args) => getInvitationsMock(...args),
    inviteMember: vi.fn(),
    updateInvitationRole: vi.fn(),
    updateTeam: vi.fn(),
  },
  invitationsAPI: {
    getInviteLinks: (...args) => getInviteLinksMock(...args),
    createInviteLink: vi.fn(),
    revokeInviteLink: vi.fn(),
    regenerateInviteLink: vi.fn(),
    copyInviteLink: vi.fn(),
    resend: vi.fn(),
    revoke: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

test('TeamInvitations still renders team shell when invite list fails', async () => {
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Delivery Team',
        allow_manager_invites: true,
        my_membership: { role: 'admin' },
      },
    },
  })
  getInvitationsMock.mockRejectedValueOnce({
    response: {
      status: 400,
      data: {
        message: 'Validation failed.',
        errors: {
          team_id: ['Team not found or unavailable.'],
        },
      },
    },
  })
  getInviteLinksMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/invitations']}>
      <Routes>
        <Route path="/teams/:teamId/invitations" element={<TeamInvitations />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Invite people to Delivery Team')).toBeInTheDocument()
  expect(screen.getByText('Team not found or unavailable.')).toBeInTheDocument()
})

test('TeamInvitations opens invite-link composer modal from empty state', async () => {
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Delivery Team',
        allow_manager_invites: true,
        my_membership: { role: 'admin' },
      },
    },
  })
  getInvitationsMock.mockResolvedValueOnce({ data: { data: { results: [] } } })
  getInviteLinksMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/invitations']}>
      <Routes>
        <Route path="/teams/:teamId/invitations" element={<TeamInvitations />} />
      </Routes>
    </TestMemoryRouter>
  )

  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /Create first link/i }))

  expect(screen.getByText('Create a secure shareable link')).toBeInTheDocument()
  expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0)
  expect(screen.getByRole('button', { name: /Create link/i })).toBeInTheDocument()
})

test('manager invite modal only exposes member role selection', async () => {
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Delivery Team',
        allow_manager_invites: true,
        my_membership: { role: 'manager' },
      },
    },
  })
  getInvitationsMock.mockResolvedValueOnce({ data: { data: { results: [] } } })
  getInviteLinksMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/invitations']}>
      <Routes>
        <Route path="/teams/:teamId/invitations" element={<TeamInvitations />} />
      </Routes>
    </TestMemoryRouter>
  )

  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /Invite first member/i }))

  const roleSelect = screen.getAllByRole('combobox')[0]
  const options = Array.from(roleSelect.querySelectorAll('option')).map((option) => option.value)
  expect(options).toEqual(['member'])
})
