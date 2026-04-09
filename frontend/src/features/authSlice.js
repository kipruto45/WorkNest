import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { authAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'
import { extractApiError } from '../utils/apiErrors'
import { clearAuthSession, extractAuthSession, persistAuthSession, persistCurrentUser } from '../utils/authSession'

const loadUserFromStorage = () => {
  const token = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionAccess)
  const user = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionUser)
  let parsedUser = null
  if (user) {
    try {
      parsedUser = JSON.parse(user)
    } catch (error) {
      localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
    }
  }
  return {
    token,
    user: parsedUser,
    isAuthenticated: !!token,
    bootstrapped: !token,
  }
}

const buildAuthError = (error, overrides = {}) => {
  if (typeof error === 'string') {
    return { message: error, errors: {}, fieldErrors: {}, status: null, requestId: null, isNetworkError: false }
  }
  return extractApiError(error, overrides)
}

const buildHydrationError = (error, fallbackMessage) => {
  const parsedError = buildAuthError(error, { fallbackMessage })
  return {
    ...parsedError,
    message: parsedError.message || fallbackMessage,
    clearSession: parsedError.status === 401,
  }
}

export const login = createAsyncThunk('auth/login', async (credentials, { rejectWithValue }) => {
  try {
    const response = await authAPI.login(credentials)
    const session = extractAuthSession(unwrapData(response))
    persistAuthSession(session)
    return { user: session.user, token: session.accessToken }
  } catch (error) {
    return rejectWithValue(buildAuthError(error, { fallbackMessage: 'Login failed' }))
  }
})

export const register = createAsyncThunk('auth/register', async (userData, { rejectWithValue }) => {
  try {
    const response = await authAPI.register(userData)
    const session = extractAuthSession(unwrapData(response))
    if (!session.isValid) {
      throw new Error('Registration did not return a valid authenticated session.')
    }
    persistAuthSession(session)
    return { user: session.user, token: session.accessToken, email: session.user?.email || userData?.email || '' }
  } catch (error) {
    return rejectWithValue(buildAuthError(error, { fallbackMessage: 'Registration failed' }))
  }
})

export const logout = createAsyncThunk('auth/logout', async () => {
  const refreshToken = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionRefresh)
  try {
    await authAPI.logout(refreshToken ? { refresh: refreshToken } : {})
  } catch (error) {
    // The local session should still be cleared even if the remote token
    // has already expired or the network is unavailable.
  }
  clearAuthSession()
})

export const hydrateCurrentUser = createAsyncThunk('auth/hydrateCurrentUser', async (_, { rejectWithValue }) => {
  try {
    const response = await authAPI.getCurrentUser()
    const user = unwrapData(response)
    persistCurrentUser(user)
    return user
  } catch (error) {
    const hydrationError = buildHydrationError(error, 'Session expired')
    if (hydrationError.clearSession) {
      clearAuthSession()
    }
    return rejectWithValue(hydrationError)
  }
})

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    ...loadUserFromStorage(),
    error: null,
    hydrating: false,
  },
  reducers: {
    setSession: (state, action) => {
      state.token = action.payload?.token ?? null
      state.user = action.payload?.user ?? null
      state.isAuthenticated = Boolean(action.payload?.token)
      state.error = null
      state.bootstrapped = Boolean(action.payload?.token)
    },
    setUser: (state, action) => {
      state.user = action.payload
      state.isAuthenticated = true
      persistCurrentUser(action.payload)
      state.bootstrapped = true
    },
    clearAuth: (state) => {
      state.token = null
      state.user = null
      state.isAuthenticated = false
      state.hydrating = false
      state.bootstrapped = true
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.token = action.payload.token
        state.isAuthenticated = true
        state.error = null
        state.bootstrapped = true
      })
      .addCase(login.rejected, (state, action) => {
        state.error = action.payload?.message || action.payload
        state.bootstrapped = true
      })
      .addCase(register.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.token = action.payload.token
        state.isAuthenticated = true
        state.error = null
        state.bootstrapped = true
      })
      .addCase(register.rejected, (state, action) => {
        state.error = action.payload?.message || action.payload
        state.bootstrapped = true
      })
      .addCase(logout.fulfilled, (state) => {
        state.token = null
        state.user = null
        state.isAuthenticated = false
        state.bootstrapped = true
      })
      .addCase(hydrateCurrentUser.pending, (state) => {
        state.hydrating = true
      })
      .addCase(hydrateCurrentUser.fulfilled, (state, action) => {
        state.hydrating = false
        state.user = action.payload
        state.isAuthenticated = Boolean(state.token)
        state.error = null
        state.bootstrapped = true
      })
      .addCase(hydrateCurrentUser.rejected, (state, action) => {
        state.hydrating = false
        if (action.payload?.clearSession) {
          state.token = null
          state.user = null
          state.isAuthenticated = false
        }
        state.error = action.payload?.message || action.payload
        state.bootstrapped = true
      })
  },
})

export const { setSession, setUser, clearAuth } = authSlice.actions
export default authSlice.reducer
