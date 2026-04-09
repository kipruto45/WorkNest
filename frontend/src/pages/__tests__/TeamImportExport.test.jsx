import React from 'react'
import { render, screen } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { vi } from 'vitest'

import TeamImportExport from '../TeamImportExport'
import { TestMemoryRouter } from '../../test/router'

vi.mock('../../services/api', () => ({
  tasksAPI: {
    importTasks: vi.fn(),
    exportTasks: vi.fn(),
  },
  unwrapData: (response) => response?.data?.data ?? null,
}))

test('TeamImportExport renders import/export controls', () => {
  render(
    <TestMemoryRouter initialEntries={['/teams/team-1/import-export']}>
      <Routes>
        <Route path="/teams/:teamId/import-export" element={<TeamImportExport />} />
      </Routes>
    </TestMemoryRouter>
  )

  expect(screen.getByRole('heading', { name: /Import tasks/i })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /Export tasks/i })).toBeInTheDocument()
})
