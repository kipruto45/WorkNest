import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamAnalytics from '../TeamAnalytics'
import { TestMemoryRouter } from '../../test/router'

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: vi.fn(async () => ({
      data: {
        data: {
          id: 'team-1',
          name: 'Delivery Team',
          my_membership: { role: 'member' },
        },
      },
    })),
  },
  dashboardAPI: {
    getTeamSummary: vi.fn(async () => ({ data: { data: { summary: {} } } })),
    getTeamProgress: vi.fn(async () => ({ data: { data: { progress: {} } } })),
    getTeamWorkload: vi.fn(async () => ({ data: { data: { workload: [] } } })),
    getTeamStatusDistribution: vi.fn(async () => ({ data: { data: { status_distribution: [] } } })),
    getTeamPriorityDistribution: vi.fn(async () => ({ data: { data: { priority_distribution: [] } } })),
  },
  tasksAPI: {
    getMilestones: vi.fn(async () => ({ data: { data: { results: [] } } })),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
}))

test('member users are blocked from analytics page', async () => {
  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/analytics']}>
      <Routes>
        <Route path="/teams/:teamId/analytics" element={<TeamAnalytics />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('You do not have access to this area.')).toBeInTheDocument()
})
