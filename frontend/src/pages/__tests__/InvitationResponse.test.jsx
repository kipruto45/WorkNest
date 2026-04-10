import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

import InvitationResponse from '../InvitationResponse'
import { hydrateCurrentUser, logout } from '../../features/authSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))
const navigateMock = vi.fn()
let authState = { user: { email: 'invitee@example.com' } }

const apiMocks = vi.hoisted(() => {
  const invitationPayload = {
    id: 'invite-1',
    email: 'invitee@example.com',
    role: 'member',
    status: 'pending',
    expires_at: '2026-05-01T12:00:00Z',
    invited_by: { name: 'Owner User' },
    team: {
      id: 'team-42',
      name: 'Core Platform',
      is_archived: false,
    },
  }

  return {
    invitationsAPI: {
      getInvitation: vi.fn(() => Promise.resolve({ data: { data: invitationPayload } })),
      accept: vi.fn(() => Promise.resolve({ data: { data: {} } })),
      decline: vi.fn(() => Promise.resolve({ data: { data: {} } })),
    },
  }
})

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) => selector({ auth: authState }),
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
  logout: vi.fn(() => () => {
    const result = Promise.resolve()
    result.unwrap = () => result
    return result
  }),
}))

beforeEach(() => {
  dispatchMock.mockClear()
  navigateMock.mockClear()
  apiMocks.invitationsAPI.getInvitation.mockClear()
  apiMocks.invitationsAPI.accept.mockClear()
  apiMocks.invitationsAPI.decline.mockClear()
  hydrateCurrentUser.mockClear()
  logout.mockClear()
  authState = { user: { email: 'invitee@example.com' } }
})

test('Invitation response accepts a matching invite and routes into the team workspace', async () => {
  render(
    <TestMemoryRouter initialEntries={['/invitations/token-123']}>
      <Routes>
        <Route path="/invitations/:token" element={<InvitationResponse />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Core Platform')).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: /Accept invitation/i }))

  await waitFor(() => {
    expect(apiMocks.invitationsAPI.accept).toHaveBeenCalledWith('token-123')
    expect(hydrateCurrentUser).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/teams/team-42/overview?onboarding=member', { replace: true })
  })
})
