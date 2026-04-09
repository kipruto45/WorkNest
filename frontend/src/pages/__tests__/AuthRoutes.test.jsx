import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { MemoryRouter, Outlet } from 'react-router-dom'
import { vi } from 'vitest'

vi.mock('../../components/Layout', () => ({
  default: function MockLayout() {
    return <Outlet />
  },
}))

vi.mock('../../pages/Login', () => ({
  default: function MockLogin() {
    return <div>Mock login page</div>
  },
}))

vi.mock('../../pages/Register', () => ({
  default: function MockRegister() {
    return <div>Mock register page</div>
  },
}))

vi.mock('../../pages/PersonalDashboard', () => ({
  default: function MockPersonalDashboard() {
    return <div>Mock personal dashboard</div>
  },
}))

vi.mock('../../pages/TeamOverview', () => ({
  default: function MockTeamOverview() {
    return <div>Mock team overview</div>
  },
}))

import App from '../../App'

const buildStore = (authState) =>
  configureStore({
    reducer: {
      auth: (state = authState) => state,
    },
    preloadedState: {
      auth: authState,
    },
  })

const renderApp = (authState, initialEntries) =>
  render(
    <Provider store={buildStore(authState)}>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
      </MemoryRouter>
    </Provider>
  )

test('Authenticated personal users are redirected away from register', async () => {
  renderApp(
    {
      token: 'access-token',
      user: { id: 'user-1', account_type: 'personal', is_staff: false },
      hydrating: false,
      bootstrapped: true,
    },
    ['/register']
  )

  await waitFor(() => {
    expect(screen.getByText('Mock personal dashboard')).toBeInTheDocument()
  })
})

test('Authenticated team users are redirected away from login to their workspace', async () => {
  renderApp(
    {
      token: 'access-token',
      user: { id: 'user-2', account_type: 'team', default_team_id: 'team-42', is_staff: false },
      hydrating: false,
      bootstrapped: true,
    },
    ['/login']
  )

  await waitFor(() => {
    expect(screen.getByText('Mock team overview')).toBeInTheDocument()
  })
})
