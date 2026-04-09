import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamMembers from '../TeamMembers'
import { TestMemoryRouter } from '../../test/router'

const getTeamMock = vi.fn()
const getTeamMembersMock = vi.fn()
const getTeamWorkloadMock = vi.fn()
const getKanbanMock = vi.fn()

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
    getTeamMembers: (...args) => getTeamMembersMock(...args),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn(),
  },
  dashboardAPI: {
    getTeamWorkload: (...args) => getTeamWorkloadMock(...args),
  },
  tasksAPI: {
    getKanban: (...args) => getKanbanMock(...args),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

test('TeamMembers renders roster even when auxiliary endpoints fail', async () => {
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Delivery Team',
        my_membership: { role: 'admin' },
      },
    },
  })
  getTeamMembersMock.mockResolvedValueOnce({
    data: {
      data: {
        results: [
          {
            id: 'membership-1',
            role: 'member',
            joined_at: '2026-04-08T12:00:00Z',
            user: {
              id: 'user-1',
              name: 'Alex Member',
              email: 'alex@example.com',
            },
          },
        ],
      },
    },
  })
  getTeamWorkloadMock.mockRejectedValueOnce(new Error('workload failed'))
  getKanbanMock.mockRejectedValueOnce(new Error('board failed'))

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/members']}>
      <Routes>
        <Route path="/teams/:teamId/members" element={<TeamMembers />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Delivery Team team roster')).toBeInTheDocument()
  expect(screen.getByText('Alex Member')).toBeInTheDocument()
})
