import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

import TeamAutomationRules from '../TeamAutomationRules'
import { TestMemoryRouter } from '../../test/router'

const getAutomationRules = vi.fn()
const getTeam = vi.fn()

vi.mock('../../services/api', () => ({
  teamsAPI: {
    getTeam: (...args) => getTeam(...args),
  },
  tasksAPI: {
    getAutomationRules: (...args) => getAutomationRules(...args),
  },
  unwrapData: (response) => response?.data?.data ?? null,
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
  },
}))

test('TeamAutomationRules renders rules', async () => {
  getTeam.mockResolvedValueOnce({
    data: {
      data: {
        id: 'team-1',
        name: 'Product Team',
      },
    },
  })
  getAutomationRules.mockResolvedValueOnce({
    data: {
      data: {
        results: [{ id: 'r1', name: 'Auto notify', trigger_type: 'task_created', action_type: 'create_notification', is_active: true }],
      },
    },
  })

  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/automation']}>
      <Routes>
        <Route path="/teams/:teamId/automation" element={<TeamAutomationRules />} />
      </Routes>
    </TestMemoryRouter>
  )

  await waitFor(() => expect(getAutomationRules).toHaveBeenCalled())
  expect(screen.getByText(/Auto notify/i)).toBeInTheDocument()
})
