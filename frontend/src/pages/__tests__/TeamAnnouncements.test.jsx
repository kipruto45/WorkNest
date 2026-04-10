import React from 'react'
import { render, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import TeamAnnouncements from '../TeamAnnouncements'
import { TestMemoryRouter } from '../../test/router'

const getTeamMock = vi.fn()
const getAnnouncementsMock = vi.fn()

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
    getAnnouncements: (...args) => getAnnouncementsMock(...args),
    createAnnouncement: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? response?.data?.results ?? response?.data ?? [],
}))

beforeEach(() => {
  getTeamMock.mockReset()
  getAnnouncementsMock.mockReset()
})

test('renders retry state when announcements fail to load', async () => {
  getTeamMock.mockRejectedValueOnce({
    response: {
      status: 404,
      data: {
        message: 'Team not found.',
      },
    },
  })
  getAnnouncementsMock.mockResolvedValueOnce({ data: { data: { results: [] } } })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/announcements']}>
      <Routes>
        <Route path="/teams/:teamId/announcements" element={<TeamAnnouncements />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(await screen.findByText('Announcements are unavailable')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})
