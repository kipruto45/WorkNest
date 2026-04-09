import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import Login from '../Login'
import { login } from '../../features/authSlice'
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
  login: vi.fn(() => () => {
    const result = Promise.reject({
      message: 'Invalid phone number or password.',
      fieldErrors: { credential: ['Enter your email or phone number.'] },
    })
    result.unwrap = () => result
    return result
  }),
}))

test('Login surfaces backend errors and field validation', async () => {
  render(
    <TestMemoryRouter initialEntries={['/login']}>
      <Login />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Individual account/i }))
  await userEvent.type(screen.getByPlaceholderText('name@company.com or +254712345678'), 'invalid@example.com')
  await userEvent.type(screen.getByPlaceholderText('Enter your password'), 'bad-pass')

  await userEvent.click(screen.getByRole('button', { name: /Sign In/i }))

  expect(await screen.findByText('Invalid phone number or password.')).toBeInTheDocument()
  expect(await screen.findByText('Enter your email or phone number.')).toBeInTheDocument()
})

test('Login blocks admin access for non-staff users', async () => {
  login.mockImplementationOnce(() => () => {
    const result = Promise.resolve({ user: { is_staff: false } })
    result.unwrap = () => result
    return result
  })

  render(
    <TestMemoryRouter initialEntries={['/login?next=/admin']}>
      <Login />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Individual account/i }))
  await userEvent.type(screen.getByPlaceholderText('name@company.com or +254712345678'), 'user@example.com')
  await userEvent.type(screen.getByPlaceholderText('Enter your password'), 'valid-pass')

  await userEvent.click(screen.getByRole('button', { name: /Sign In/i }))

  await waitFor(() => {
    expect(navigateMock).toHaveBeenCalledWith('/403', { replace: true })
  })
})

test('Login redirects after successful authentication', async () => {
  login.mockImplementationOnce(() => () => {
    const result = Promise.resolve({ user: { is_staff: false } })
    result.unwrap = () => result
    return result
  })

  render(
    <TestMemoryRouter initialEntries={['/login']}>
      <Login />
    </TestMemoryRouter>
  )

  await userEvent.click(screen.getByRole('button', { name: /Individual account/i }))
  await userEvent.type(screen.getByPlaceholderText('name@company.com or +254712345678'), 'user@example.com')
  await userEvent.type(screen.getByPlaceholderText('Enter your password'), 'valid-pass')

  await userEvent.click(screen.getByRole('button', { name: /Sign In/i }))

  await waitFor(() => {
    expect(navigateMock).toHaveBeenCalledWith('/dashboard', { replace: true })
  })
})
