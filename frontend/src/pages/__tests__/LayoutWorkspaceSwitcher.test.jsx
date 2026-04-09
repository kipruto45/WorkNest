import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import Layout from '../../components/Layout'
import { TestMemoryRouter } from '../../test/router'
import { CLIENT_STORAGE_KEYS } from '../../utils/clientConfig'

vi.mock('../../hooks/useRealtimeNotifications', () => ({
  useRealtimeNotifications: () => undefined,
}))

vi.mock('../../features/notificationsSlice', () => ({
  fetchUnreadCount: () => ({ type: 'notifications/fetchUnreadCount/mock' }),
}))

vi.mock('../../features/authSlice', () => ({
  logout: () => ({ type: 'auth/logout/mock' }),
}))

vi.mock('../../services/api', () => ({
  commonAPI: {
    search: vi.fn(async () => ({ data: { data: { sections: {} } } })),
  },
  unwrapData: (response) => response?.data?.data ?? response?.data ?? null,
}))

function renderLayoutWithState(user, initialEntry = '/dashboard') {
  const store = configureStore({
    reducer: {
      auth: (state = { user }) => state,
      notifications: (state = { unreadCount: 0 }) => state,
    },
    preloadedState: {
      auth: { user },
      notifications: { unreadCount: 0 },
    },
  })

  return render(
    <Provider store={store}>
      <TestMemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<div>Personal Home</div>} />
            <Route path="/teams/:teamId/overview" element={<div>Team Home</div>} />
            <Route path="/notifications" element={<div>Notifications</div>} />
            <Route path="/profile" element={<div>Profile</div>} />
            <Route path="/search" element={<div>Search</div>} />
            <Route path="/settings" element={<div>Settings</div>} />
            <Route path="/settings/security" element={<div>Security</div>} />
            <Route path="/teams/:teamId" element={<div>Team Tasks</div>} />
            <Route path="/teams/:teamId/calendar" element={<div>Team Calendar</div>} />
            <Route path="/teams/:teamId/members" element={<div>Team Members</div>} />
            <Route path="/teams/:teamId/invitations" element={<div>Team Invites</div>} />
            <Route path="/teams/:teamId/milestones" element={<div>Team Milestones</div>} />
            <Route path="/teams/:teamId/announcements" element={<div>Team Announcements</div>} />
            <Route path="/teams/:teamId/activity" element={<div>Team Activity</div>} />
            <Route path="/teams/:teamId/settings" element={<div>Team Settings</div>} />
            <Route path="/teams/:teamId/automation" element={<div>Team Automation</div>} />
          </Route>
        </Routes>
      </TestMemoryRouter>
    </Provider>
  )
}

test('workspace switcher allows changing from personal to team workspace', async () => {
  localStorage.setItem(CLIENT_STORAGE_KEYS.workspacePrefs, JSON.stringify({}))
  const user = {
    id: 'user-1',
    name: 'Morgan',
    email: 'morgan@example.com',
    account_type: 'personal',
    workspace_options: [
      { id: 'personal-team', is_personal: true, name: 'Personal workspace', my_role: 'admin' },
      { id: 'team-42', is_personal: false, name: 'Delivery Team', my_role: 'member' },
    ],
    default_team_id: 'team-42',
  }

  renderLayoutWithState(user)

  const select = screen.getByLabelText('Active workspace')
  fireEvent.change(select, { target: { value: 'team:team-42' } })

  expect(await screen.findByText('Team Home')).toBeInTheDocument()
})
