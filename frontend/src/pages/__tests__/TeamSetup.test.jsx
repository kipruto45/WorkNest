import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import TeamSetup from '../TeamSetup'
import { createTeam } from '../../features/teamsSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))
const navigateMock = vi.fn()
let authState = { user: { id: 'user-1', account_type: 'team', default_team_id: null } }

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

vi.mock('../../features/teamsSlice', () => ({
  createTeam: vi.fn(() => () => {
    const result = Promise.resolve({ id: 'team-1', name: 'Core Platform' })
    result.unwrap = () => result
    return result
  }),
}))

beforeEach(() => {
  dispatchMock.mockClear()
  navigateMock.mockClear()
  createTeam.mockClear()
})

test('Team setup creates a workspace and routes into team dashboard overview', async () => {
  authState = { user: { id: 'user-1', account_type: 'team', default_team_id: null } }

  render(
    <TestMemoryRouter initialEntries={['/team-setup']}>
      <TeamSetup />
    </TestMemoryRouter>
  )

  await userEvent.type(screen.getByPlaceholderText('Growth Squad'), 'Core Platform')
  await userEvent.type(screen.getByPlaceholderText('What does this team own and deliver?'), 'Builds the shared platform.')
  await userEvent.click(screen.getByRole('button', { name: /Create team workspace/i }))

  await waitFor(() => {
    expect(createTeam).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/teams/team-1/overview', { replace: true })
  })
})

test('Team setup redirects personal accounts back to the personal dashboard', async () => {
  authState = { user: { id: 'user-2', account_type: 'personal', default_team_id: 'personal-team-1' } }

  render(
    <TestMemoryRouter initialEntries={['/team-setup']}>
      <TeamSetup />
    </TestMemoryRouter>
  )

  await waitFor(() => {
    expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true })
  })
})
