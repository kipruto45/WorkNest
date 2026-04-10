import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamOverview from '../TeamOverview'
import { TestMemoryRouter } from '../../test/router'

const pendingPromise = new Promise(() => {})
const getTeamMock = vi.fn()
const getTeamCalendarMock = vi.fn()
const getKanbanMock = vi.fn()
const getNotificationsMock = vi.fn()
const getTeamMemberOverviewMock = vi.fn()

vi.mock('react-redux', () => ({
  useSelector: (selector) =>
    selector({
      auth: {
        user: {
          id: 'user-42',
          name: 'Member User',
        },
      },
    }),
}))

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
    getTeamMemberOverview: (...args) => getTeamMemberOverviewMock(...args),
  },
  notificationsAPI: {
    getNotifications: (...args) => getNotificationsMock(...args),
  },
  tasksAPI: {
    getKanban: (...args) => getKanbanMock(...args),
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
  getTeamMemberOverviewMock.mockReset()
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
  getKanbanMock.mockReset()
  getNotificationsMock.mockReset()
  getTeamMemberOverviewMock.mockReset()
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
  getKanbanMock.mockResolvedValueOnce({ data: { data: { todo: { tasks: [] }, in_progress: { tasks: [] }, in_review: { tasks: [] }, done: { tasks: [] } } } })
  getNotificationsMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

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

test('TeamOverview renders member-focused assigned tasks section for member role', async () => {
  getTeamMock.mockReset()
  getTeamCalendarMock.mockReset()
  getKanbanMock.mockReset()
  getNotificationsMock.mockReset()
  getTeamMemberOverviewMock.mockReset()

  getTeamMock.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-42',
        name: 'Delivery Team',
        my_membership: { role: 'member' },
      },
    },
  })
  getTeamMemberOverviewMock.mockResolvedValueOnce({
    data: {
      data: {
        my_assigned_tasks: [
          {
            id: 'task-1',
            title: 'Prepare release notes',
            status: 'todo',
            priority: 'high',
            due_date: '2026-04-14T08:00:00Z',
            assigned_to: 'user-42',
            assigned_to_data: { id: 'user-42', name: 'Member User' },
          },
        ],
        my_progress: {
          total: 1,
          completed: 0,
          pending: 1,
          overdue: 0,
          completion_rate: 0,
        },
        welcome: {
          due_this_week: 1,
        },
        calendar_preview: [],
        recent_activity: [],
        notifications_preview: [],
        members_snapshot: [],
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-42/overview']}>
      <Routes>
        <Route path="/teams/:teamId/overview" element={<TeamOverview />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('My Assigned Tasks')).toBeInTheDocument()
  expect(screen.getAllByText('Prepare release notes').length).toBeGreaterThan(0)
  expect(getTeamMemberOverviewMock).toHaveBeenCalledWith('team-42')
})
