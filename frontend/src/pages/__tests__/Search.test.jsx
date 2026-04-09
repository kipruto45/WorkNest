import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import Search from '../Search'
import { TestMemoryRouter } from '../../test/router'

const searchMock = vi.fn()
const getTeamsMock = vi.fn()
const getTeamMembersMock = vi.fn()

vi.mock('../../services/api', () => ({
  commonAPI: {
    search: (...args) => searchMock(...args),
  },
  teamsAPI: {
    getTeams: (...args) => getTeamsMock(...args),
    getTeamMembers: (...args) => getTeamMembersMock(...args),
  },
  unwrapData: (response) => response?.data?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

test('Search refetches when filters change', async () => {
  getTeamsMock.mockResolvedValue({
    data: {
      data: {
        results: [{ id: 'team-1', name: 'Growth' }],
      },
    },
  })
  getTeamMembersMock.mockResolvedValue({
    data: {
      data: {
        results: [{ id: 'member-1', user: { id: 'user-1', name: 'Alex' } }],
      },
    },
  })
  searchMock.mockResolvedValue({
    data: {
      data: {
        sections: {
          tasks: [],
          teams: [],
          people: [],
          comments: [],
          announcements: [],
          milestones: [],
        },
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/search?q=release']}>
      <Routes>
        <Route path="/search" element={<Search />} />
      </Routes>
    </TestMemoryRouter>
  )

  await waitFor(() => expect(searchMock).toHaveBeenCalledWith(expect.objectContaining({ q: 'release', status: undefined })))

  await userEvent.selectOptions(screen.getByLabelText('Status'), 'done')

  await waitFor(() =>
    expect(searchMock).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'release', status: 'done' }))
  )
})
