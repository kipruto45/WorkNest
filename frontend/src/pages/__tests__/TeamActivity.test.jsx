import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamActivity from '../TeamActivity'
import { TestMemoryRouter } from '../../test/router'

const getTeamMock = vi.fn()
const getAuditLogsMock = vi.fn()

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
  },
  auditLogsAPI: {
    getForTeam: (...args) => getAuditLogsMock(...args),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

beforeEach(() => {
  getTeamMock.mockReset()
  getAuditLogsMock.mockReset()
})

test('renders retry state when team timeline fails to load', async () => {
  getTeamMock.mockRejectedValueOnce({
    response: {
      status: 404,
      data: {
        message: 'Team not found.',
      },
    },
  })
  getAuditLogsMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/activity']}>
      <Routes>
        <Route path="/teams/:teamId/activity" element={<TeamActivity />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Team activity is unavailable')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})
