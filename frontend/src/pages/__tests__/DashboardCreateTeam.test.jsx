import React from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import Dashboard from '../Dashboard'
import { createTeam } from '../../features/teamsSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) =>
      selector({
        auth: { user: { name: 'Test User', first_name: 'Test' } },
        notifications: { unreadCount: 0 },
        teams: { teams: [], loading: false },
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

vi.mock('../../features/teamsSlice', () => ({
  createTeam: vi.fn(() => () => {
    const result = Promise.resolve({ id: 'team-1', name: 'Test Team' })
    result.unwrap = () => result
    return result
  }),
}))

const emptyResults = { data: { data: { results: [] } } }
const emptySummary = { data: { data: { summary: {} } } }

vi.mock('../../services/api', () => ({
  dashboardAPI: {
    getPersonalSummary: vi.fn(() => Promise.resolve(emptySummary)),
    getPersonalTasks: vi.fn(() => Promise.resolve(emptyResults)),
    getPersonalOverdue: vi.fn(() => Promise.resolve(emptyResults)),
    getCompletedThisWeek: vi.fn(() => Promise.resolve(emptyResults)),
  },
  notificationsAPI: {
    getNotifications: vi.fn(() => Promise.resolve(emptyResults)),
  },
  tasksAPI: {
    getFavorites: vi.fn(() => Promise.resolve(emptyResults)),
    getRecent: vi.fn(() => Promise.resolve(emptyResults)),
  },
  teamsAPI: {
    getTeams: vi.fn(() => Promise.resolve(emptyResults)),
    getPinnedTeams: vi.fn(() => Promise.resolve(emptyResults)),
    getRecentTeams: vi.fn(() => Promise.resolve(emptyResults)),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

test('Dashboard create team modal validates empty names and submits on success', async () => {
  render(
    <TestMemoryRouter initialEntries={['/dashboard']}>
      <Dashboard />
    </TestMemoryRouter>
  )

  await screen.findByText(/My Teams/i)

  await userEvent.click(screen.getByRole('button', { name: /Create team/i }))

  const modal = await screen.findByText('Create a new team')
  const modalRoot = modal.closest('.page-shell')
  const modalScope = modalRoot ? within(modalRoot) : screen

  await userEvent.click(modalScope.getByRole('button', { name: /Create team/i }))

  expect(await screen.findByText('Team name is required.')).toBeInTheDocument()

  await userEvent.type(screen.getByPlaceholderText('Growth Squad'), 'Core Platform')
  await userEvent.click(modalScope.getByRole('button', { name: /Create team/i }))

  await waitFor(() => {
    expect(createTeam).toHaveBeenCalled()
  })
})
