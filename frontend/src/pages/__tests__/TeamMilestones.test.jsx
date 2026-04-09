import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

import TeamMilestones from '../TeamMilestones'
import { TestMemoryRouter } from '../../test/router'

const getMilestones = vi.fn()
const getTeam = vi.fn()

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: (...args) => getTeam(...args),
  },
  tasksAPI: {
    getMilestones: (...args) => getMilestones(...args),
  },
  unwrapData: (response) => response?.data?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
  },
}))

test('TeamMilestones renders list', async () => {
  getTeam.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Product Team',
      },
    },
  })
  getMilestones.mockResolvedValueOnce({
    data: {
      data: {
        results: [
          {
            id: 'm1',
            title: 'Release',
            status: 'in_progress',
            progress: { total: 4, completed: 2, percentage: 50 },
            linked_tasks: [{ id: 't1', title: 'QA sign-off', status: 'in_review', assignee_name: 'Morgan' }],
          },
        ],
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/milestones?milestone=m1']}>
      <Routes>
        <Route path="/teams/:teamId/milestones" element={<TeamMilestones />} />
      </Routes>
    </TestMemoryRouter>
  )

  await waitFor(() => expect(getMilestones).toHaveBeenCalled())
  expect(screen.getByText(/Release/i)).toBeInTheDocument()
  expect(screen.getByText(/QA sign-off/i)).toBeInTheDocument()
  expect(screen.getAllByText(/In progress/i).length).toBeGreaterThan(0)
})
