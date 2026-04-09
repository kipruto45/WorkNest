import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

import TeamAutomationRules from '../TeamAutomationRules'
import { TestMemoryRouter } from '../../test/router'

const getAutomationRules = vi.fn()

vi.mock('../../services/api', () => ({
  tasksAPI: {
    getAutomationRules: (...args) => getAutomationRules(...args),
  },
  unwrapResults: (response) => response?.data?.data?.results ?? [],
}))

vi.mock('react-toastify', () => ({
  toast: {
    error: vi.fn(),
  },
}))

test('TeamAutomationRules renders rules', async () => {
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
