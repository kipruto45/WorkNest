import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamAnalytics from '../TeamAnalytics'
import { TestMemoryRouter } from '../../test/router'

const getTeamMock = vi.fn()
const getTeamSummaryMock = vi.fn()
const getTeamProgressMock = vi.fn()
const getTeamWorkloadMock = vi.fn()
const getTeamStatusDistributionMock = vi.fn()
const getTeamPriorityDistributionMock = vi.fn()
const getMilestonesMock = vi.fn()

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: (...args) => getTeamMock(...args),
  },
  dashboardAPI: {
    getTeamSummary: (...args) => getTeamSummaryMock(...args),
    getTeamProgress: (...args) => getTeamProgressMock(...args),
    getTeamWorkload: (...args) => getTeamWorkloadMock(...args),
    getTeamStatusDistribution: (...args) => getTeamStatusDistributionMock(...args),
    getTeamPriorityDistribution: (...args) => getTeamPriorityDistributionMock(...args),
  },
  tasksAPI: {
    getMilestones: (...args) => getMilestonesMock(...args),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
}))

beforeEach(() => {
  getTeamMock.mockReset()
  getTeamSummaryMock.mockReset()
  getTeamProgressMock.mockReset()
  getTeamWorkloadMock.mockReset()
  getTeamStatusDistributionMock.mockReset()
  getTeamPriorityDistributionMock.mockReset()
  getMilestonesMock.mockReset()
})

test('member users are blocked from analytics page', async () => {
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Delivery Team',
        my_membership: { role: 'member' },
      },
    },
  })
  getTeamSummaryMock.mockResolvedValueOnce({ data: { data: { summary: {} } } })
  getTeamProgressMock.mockResolvedValueOnce({ data: { data: { progress: {} } } })
  getTeamWorkloadMock.mockResolvedValueOnce({ data: { data: { workload: [] } } })
  getTeamStatusDistributionMock.mockResolvedValueOnce({ data: { data: { status_distribution: [] } } })
  getTeamPriorityDistributionMock.mockResolvedValueOnce({ data: { data: { priority_distribution: [] } } })
  getMilestonesMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/analytics']}>
      <Routes>
        <Route path="/teams/:teamId/analytics" element={<TeamAnalytics />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('You do not have access to this area.')).toBeInTheDocument()
})

test('shows retry state when analytics request fails', async () => {
  getTeamMock.mockRejectedValueOnce({
    response: {
      status: 404,
      data: {
        message: 'Team not found.',
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/analytics']}>
      <Routes>
        <Route path="/teams/:teamId/analytics" element={<TeamAnalytics />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Team analytics are unavailable')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})
