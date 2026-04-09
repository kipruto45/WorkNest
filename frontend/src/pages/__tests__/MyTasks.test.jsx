import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import MyTasks from '../MyTasks'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))
const navigateMock = vi.fn()
const getMyTasks = vi.fn()
const getSavedViews = vi.fn()
const getTemplates = vi.fn()
const getTeams = vi.fn()
const createTemplate = vi.fn()

const currentUser = {
  id: 'user-1',
  name: 'Solo User',
  email: 'solo@example.com',
  account_type: 'personal',
  default_team_id: 'stale-personal-team',
}

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
    useSelector: (selector) => selector({ auth: { user: currentUser } }),
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

const createTaskMock = vi.fn((payload) => () => {
  const result = Promise.resolve({ id: 'task-1', ...payload })
  result.unwrap = () => result
  return result
})

vi.mock('../../features/tasksSlice', () => ({
  createTask: (...args) => createTaskMock(...args),
}))

vi.mock('../../services/api', () => ({
  tasksAPI: {
    getMyTasks: (...args) => getMyTasks(...args),
    getSavedViews: (...args) => getSavedViews(...args),
    getTemplates: (...args) => getTemplates(...args),
    createTemplate: (...args) => createTemplate(...args),
  },
  teamsAPI: {
    getTeams: (...args) => getTeams(...args),
    getTeamMembers: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

beforeEach(() => {
  vi.clearAllMocks()
  getTeams.mockResolvedValue({
    data: {
      data: {
        results: [{ id: 'personal-team-1', name: 'Solo Personal Workspace', is_personal: true }],
      },
    },
  })
  getSavedViews.mockResolvedValue({ data: { data: { results: [] } } })
  getMyTasks.mockResolvedValue({ data: { data: { results: [] } } })
  getTemplates.mockResolvedValue({ data: { data: { results: [] } } })
})

test('Personal task creation does not send a team id from the personal dashboard composer', async () => {
  const user = userEvent.setup()

  render(
    <TestMemoryRouter>
      <MyTasks />
    </TestMemoryRouter>
  )

  await waitFor(() => expect(getTeams).toHaveBeenCalled())

  await user.click(screen.getByRole('button', { name: /Add task/i }))
  await user.type(screen.getByPlaceholderText('Prepare launch checklist'), 'Plan the quarter')
  await user.click(screen.getByRole('button', { name: /^Create task$/i }))

  await waitFor(() => {
    expect(createTaskMock).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Plan the quarter',
      })
    )
  })

  expect(createTaskMock.mock.calls[0][0]).not.toHaveProperty('team_id')
  expect(navigateMock).toHaveBeenCalledWith('/tasks/task-1')
})
