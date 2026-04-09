import React from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import Teams from '../Teams'
import { createTeam, fetchTeams } from '../../features/teamsSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) =>
      selector({
        auth: { user: { name: 'Test User' } },
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
  fetchTeams: vi.fn(() => () => {
    const result = Promise.resolve([])
    result.unwrap = () => result
    return result
  }),
}))

vi.mock('../../services/api', () => ({
  teamsAPI: {
    togglePin: vi.fn(() => Promise.resolve({ data: { data: { is_pinned: true } } })),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

test('Teams create modal submits and refreshes team list', async () => {
  render(
    <TestMemoryRouter initialEntries={['/teams']}>
      <Teams />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Create team/i }))

  const modal = await screen.findByText('Create a new team')
  const modalRoot = modal.closest('.page-shell')
  const modalScope = modalRoot ? within(modalRoot) : screen

  await userEvent.type(screen.getByPlaceholderText('Growth Squad'), 'Core Platform')
  await userEvent.click(modalScope.getByRole('button', { name: /Create team/i }))

  await waitFor(() => {
    expect(createTeam).toHaveBeenCalled()
    expect(fetchTeams).toHaveBeenCalled()
  })
})
