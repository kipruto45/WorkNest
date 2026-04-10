import React from 'react'
import { render, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PersonalDashboard from '../PersonalDashboard'
import { TestMemoryRouter } from '../../test/router'

const getPersonalCalendarMock = vi.fn()

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useSelector: (selector) =>
      selector({
        auth: { user: { id: 'user-1', name: 'Alex Doe', first_name: 'Alex' } },
      }),
  }
})

vi.mock('../../services/api', () => ({
  dashboardAPI: {
    getPersonalSummary: vi.fn(() => Promise.resolve({ data: { data: { summary: {} } } })),
    getPersonalTasks: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })),
    getPersonalOverdue: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })),
    getPersonalCalendar: (...args) => getPersonalCalendarMock(...args),
  },
  notificationsAPI: {
    getNotifications: vi.fn(() => Promise.resolve({ data: { data: { results: [] } } })),
  },
  tasksAPI: {},
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

test('PersonalDashboard requests calendar without unsupported pagination params', async () => {
  getPersonalCalendarMock.mockReset()
  getPersonalCalendarMock.mockResolvedValueOnce({ data: { data: [] } })

  render(
    <TestMemoryRouter initialEntries={['/dashboard']}>
      <PersonalDashboard />
    </TestMemoryRouter>
  )

  await waitFor(() => {
    expect(getPersonalCalendarMock).toHaveBeenCalledWith()
  })
})
