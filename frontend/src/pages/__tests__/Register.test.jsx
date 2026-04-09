import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import Register from '../Register'
import { hydrateCurrentUser, register as registerUser } from '../../features/authSlice'
import { TestMemoryRouter } from '../../test/router'

const dispatchMock = vi.fn((action) => (typeof action === 'function' ? action() : action))
const navigateMock = vi.fn()

vi.mock('react-redux', async () => {
  const actual = await vi.importActual('react-redux')
  return {
    ...actual,
    useDispatch: () => dispatchMock,
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

vi.mock('../../features/authSlice', () => ({
  register: vi.fn(() => () => {
    const result = Promise.reject({
      message: 'Email is already registered.',
      fieldErrors: { email: ['This email is already registered.'] },
    })
    result.unwrap = () => result
    return result
  }),
  hydrateCurrentUser: vi.fn(() => () => {
    const result = Promise.resolve({ id: 'user-1', email: 'new@example.com', account_type: 'personal', is_staff: false, email_verified: true })
    result.unwrap = () => result
    return result
  }),
  setUser: (payload) => ({ type: 'auth/setUser', payload }),
}))

test('Register surfaces backend errors and field validation', async () => {
  render(
    <TestMemoryRouter initialEntries={['/register']}>
      <Register />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Individual account/i }))
  await userEvent.type(screen.getByPlaceholderText('Alex Morgan'), 'Jane Doe')
  await userEvent.type(screen.getByPlaceholderText('name@company.com'), 'jane@example.com')
  await userEvent.clear(screen.getByPlaceholderText('+254712345678'))
  await userEvent.type(screen.getByPlaceholderText('+254712345678'), '+254712345678')
  await userEvent.type(screen.getByPlaceholderText('Create password'), 'StrongPass123!')
  await userEvent.type(screen.getByPlaceholderText('Confirm password'), 'StrongPass123!')

  await userEvent.click(screen.getByRole('button', { name: /Create account/i }))

  expect(await screen.findByText('Email is already registered.')).toBeInTheDocument()
  expect(await screen.findByText('This email is already registered.')).toBeInTheDocument()
})

test('Register signs the user in and routes to the personal dashboard after success', async () => {
  registerUser.mockImplementationOnce(() => () => {
    const result = Promise.resolve({
      email: 'new@example.com',
      token: 'access-token',
      user: { id: 'user-1', email: 'new@example.com', account_type: 'personal', is_staff: false, email_verified: true },
    })
    result.unwrap = () => result
    return result
  })
  hydrateCurrentUser.mockImplementationOnce(() => () => {
    const result = Promise.resolve({ id: 'user-1', email: 'new@example.com', account_type: 'personal', is_staff: false, email_verified: true })
    result.unwrap = () => result
    return result
  })

  render(
    <TestMemoryRouter initialEntries={['/register?next=/dashboard']}>
      <Register />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Individual account/i }))
  await userEvent.type(screen.getByPlaceholderText('Alex Morgan'), 'Jane Doe')
  await userEvent.type(screen.getByPlaceholderText('name@company.com'), 'new@example.com')
  await userEvent.clear(screen.getByPlaceholderText('+254712345678'))
  await userEvent.type(screen.getByPlaceholderText('+254712345678'), '+254712345678')
  await userEvent.type(screen.getByPlaceholderText('Create password'), 'StrongPass123!')
  await userEvent.type(screen.getByPlaceholderText('Confirm password'), 'StrongPass123!')

  await userEvent.click(screen.getByRole('button', { name: /Create account/i }))

  await waitFor(() => {
    expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true })
  })
})

test('Register routes team users straight into their new workspace', async () => {
  registerUser.mockImplementationOnce(() => () => {
    const result = Promise.resolve({
      email: 'team@example.com',
      token: 'access-token',
      user: {
        id: 'user-2',
        email: 'team@example.com',
        account_type: 'team',
        default_team_id: 'team-42',
        is_staff: false,
        email_verified: false,
      },
    })
    result.unwrap = () => result
    return result
  })
  hydrateCurrentUser.mockImplementationOnce(() => () => {
    const result = Promise.resolve({
      id: 'user-2',
      email: 'team@example.com',
      account_type: 'team',
      default_team_id: 'team-42',
      is_staff: false,
      email_verified: false,
    })
    result.unwrap = () => result
    return result
  })

  render(
    <TestMemoryRouter initialEntries={['/register']}>
      <Register />
    </TestMemoryRouter>
  )

  await userEvent.type(screen.getByPlaceholderText('Alex Morgan'), 'Jane Doe')
  await userEvent.click(screen.getByRole('button', { name: /Team account/i }))
  await userEvent.type(screen.getByPlaceholderText('Growth Squad'), 'Growth Squad')
  await userEvent.type(screen.getByPlaceholderText('name@company.com'), 'team@example.com')
  await userEvent.clear(screen.getByPlaceholderText('+254712345678'))
  await userEvent.type(screen.getByPlaceholderText('+254712345678'), '+254712345678')
  await userEvent.type(screen.getByPlaceholderText('Create password'), 'StrongPass123!')
  await userEvent.type(screen.getByPlaceholderText('Confirm password'), 'StrongPass123!')

  await userEvent.click(screen.getByRole('button', { name: /Create workspace/i }))

  await waitFor(() => {
    expect(navigateMock).toHaveBeenCalledWith('/teams/team-42/overview', { replace: true })
  })
})
