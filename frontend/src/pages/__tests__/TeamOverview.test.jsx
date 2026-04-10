import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamOverview from '../TeamOverview'
import { TestMemoryRouter } from '../../test/router'

const pendingPromise = new Promise(() => {})
const getTeamMock = vi.fn()
const getTeamCalendarMock = vi.fn()

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
    getAnnouncements: vi.fn(),
    getTeamMembers: vi.fn(),
    getTimeline: vi.fn(),
    createAnnouncement: vi.fn(),
    togglePin: vi.fn(),
  },
  dashboardAPI: {
    getTeamSummary: vi.fn(),
    getTeamProgress: vi.fn(),
    getTeamWorkload: vi.fn(),
    getTeamStatusDistribution: vi.fn(),
    getTeamPriorityDistribution: vi.fn(),
    getTeamCalendar: (...args) => getTeamCalendarMock(...args),
    getTeamActivity: vi.fn(),
  },
  tasksAPI: {
    getKanban: vi.fn(),
    getMilestones: vi.fn(),
  },
  auditLogsAPI: {
    getForTeam: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

test('TeamOverview renders loading state while team payload is pending', () => {
  getTeamMock.mockReset()
  getTeamCalendarMock.mockReset()
  getTeamMock.mockReturnValueOnce(pendingPromise)

  render(
    <TestMemoryRouter initialEntries={['/teams/team-42/overview']}>
      <Routes>
        <Route path="/teams/:teamId/overview" element={<TeamOverview />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(screen.getByText('Loading team dashboard')).toBeInTheDocument()
})

test('TeamOverview requests calendar feed without unsupported page_size params', async () => {
  getTeamMock.mockReset()
  getTeamCalendarMock.mockReset()
  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-42',
        name: 'Delivery Team',
        my_membership: { role: 'admin' },
      },
    },
  })
  getTeamCalendarMock.mockResolvedValueOnce({ data: { data: [] } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-42/overview']}>
      <Routes>
        <Route path="/teams/:teamId/overview" element={<TeamOverview />} />
      </Routes>
    </TestMemoryRouter>
  )

  await waitFor(() => {
    expect(getTeamCalendarMock).toHaveBeenCalledWith('team-42')
  })
})
