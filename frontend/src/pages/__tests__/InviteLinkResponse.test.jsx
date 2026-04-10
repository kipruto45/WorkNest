import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import InviteLinkResponse from '../InviteLinkResponse'
import { hydrateCurrentUser } from '../../features/authSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))
const navigateMock = vi.fn()

const apiMocks = vi.hoisted(() => ({
  invitationsAPI: {
    resolveInviteLink: vi.fn(),
    acceptInviteLink: vi.fn(() => Promise.resolve({ data: { data: {} } })),
  },
}))

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
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
  invitationsAPI: apiMocks.invitationsAPI,
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
}))

vi.mock('../../features/authSlice', () => ({
  hydrateCurrentUser: vi.fn(() => () => {
    const result = Promise.resolve({
      email: 'invitee@example.com',
      default_team_id: 'team-42',
    })
    result.unwrap = () => result
    return result
  }),
}))

beforeEach(() => {
  dispatchMock.mockClear()
  navigateMock.mockClear()
  apiMocks.invitationsAPI.resolveInviteLink.mockReset()
  apiMocks.invitationsAPI.acceptInviteLink.mockClear()
  hydrateCurrentUser.mockClear()
})

test('accepting an actionable invite link joins the team and routes with member onboarding', async () => {
  apiMocks.invitationsAPI.resolveInviteLink.mockResolvedValueOnce({
    data: {
      data: {
        id: 'link-1',
        invited_role: 'member',
        status: 'active',
        team: { id: 'team-42', name: 'Core Platform', is_archived: false },
        viewer_state: { is_authenticated: true, is_already_member: false },
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/invite-links/token-123']}>
      <Routes>
        <Route path="/invite-links/:token" element={<InviteLinkResponse />} />
      </Routes>
    </TestMemoryRouter>
  )

  await screen.findByText('Core Platform')
  await userEvent.click(screen.getByRole('button', { name: /Join team workspace/i }))

  await waitFor(() => {
    expect(apiMocks.invitationsAPI.acceptInviteLink).toHaveBeenCalledWith('token-123')
    expect(hydrateCurrentUser).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/teams/team-42/overview?onboarding=member', { replace: true })
  })
})

test('invite-link auth-required state shows sign-in actions', async () => {
  apiMocks.invitationsAPI.resolveInviteLink.mockResolvedValueOnce({
    data: {
      data: {
        id: 'link-1',
        invited_role: 'member',
        status: 'active',
        team: { id: 'team-42', name: 'Core Platform', is_archived: false },
        viewer_state: { is_authenticated: false, is_already_member: false },
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/invite-links/token-xyz']}>
      <Routes>
        <Route path="/invite-links/:token" element={<InviteLinkResponse />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Core Platform')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Sign in to continue/i })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Create account/i })).toBeInTheDocument()
})
