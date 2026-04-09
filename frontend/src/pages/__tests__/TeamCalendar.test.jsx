import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamCalendar from '../TeamCalendar'
import { TestMemoryRouter } from '../../test/router'

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

const getTeamMock = vi.fn()
const getTeamCalendarMock = vi.fn()
const getGoogleStatusMock = vi.fn()

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: (...args) => getTeamMock(...args),
  },
  dashboardAPI: {
    getTeamCalendar: (...args) => getTeamCalendarMock(...args),
  },
  calendarAPI: {
    getGoogleStatus: (...args) => getGoogleStatusMock(...args),
    exportTasksICS: vi.fn(),
    previewICSImport: vi.fn(),
    confirmImport: vi.fn(),
    connectGoogle: vi.fn(),
    disconnectGoogle: vi.fn(),
    listGoogleCalendars: vi.fn(),
    selectGoogleCalendar: vi.fn(),
    syncGoogleTasks: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
}))

function buildCalendarResponse(role) {
  return {
    team: {
      id: 'team-1',
      name: 'Delivery Team',
      my_membership: { role },
    },
    calendar: {
      events: [
        {
          task_id: 'task-1',
          title: 'Prepare release notes',
          due_date: '2026-04-10T10:00:00Z',
          start_at: '2026-04-10T09:00:00Z',
          status: 'todo',
          priority: 'high',
          assigned_to_name: 'Grace',
        },
      ],
    },
    status: {
      connected: false,
      status: 'disconnected',
    },
  }
}

async function renderTeamCalendar(role = 'member') {
  const payload = buildCalendarResponse(role)
  getTeamMock.mockResolvedValue({ data: { data: payload.team } })
  getTeamCalendarMock.mockResolvedValue({ data: { data: payload.calendar.events } })
  getGoogleStatusMock.mockResolvedValue({ data: { data: payload.status } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/calendar']}>
      <Routes>
        <Route path="/teams/:teamId/calendar" element={<TeamCalendar />} />
      </Routes>
    </TestMemoryRouter>
  )

  return screen.findByText('Delivery Team schedule view')
}

test('member view hides import and google management actions', async () => {
  await renderTeamCalendar('member')

  expect(screen.getByRole('button', { name: 'Export .ics' })).toBeInTheDocument()
  expect(screen.queryByText('Import .ics')).not.toBeInTheDocument()
  expect(screen.queryByText('Connect Google')).not.toBeInTheDocument()
})

test('admin view shows import and google management actions', async () => {
  await renderTeamCalendar('admin')

  expect(screen.getByRole('button', { name: 'Export .ics' })).toBeInTheDocument()
  expect(screen.getByText('Import .ics')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Connect Google' })).toBeInTheDocument()
})
