import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { authAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'
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
  }
}

const extractErrorMessage = (error, fallbackMessage) => {
  const payload = error?.response?.data
  if (typeof payload?.message === 'string' && payload.message.trim()) {
    return payload.message
  }

  const errorEntries = payload?.errors
  if (errorEntries && typeof errorEntries === 'object') {
    for (const value of Object.values(errorEntries)) {
      if (Array.isArray(value) && value[0]) {
        return value[0]
      }
      if (typeof value === 'string' && value.trim()) {
        return value
      }
    }
  }

  return fallbackMessage
}

export const login = createAsyncThunk('auth/login', async (credentials, { rejectWithValue }) => {
  try {
    const response = await authAPI.login(credentials)
    const session = extractAuthSession(unwrapData(response))
    persistAuthSession(session)
    return { user: session.user, token: session.accessToken }
  } catch (error) {
    return rejectWithValue(extractErrorMessage(error, 'Login failed'))
  }
})

export const register = createAsyncThunk('auth/register', async (userData, { rejectWithValue }) => {
  try {
    const response = await authAPI.register(userData)
    const session = extractAuthSession(unwrapData(response))
    persistAuthSession(session)
    return { user: session.user, token: session.accessToken }
  } catch (error) {
    return rejectWithValue(extractErrorMessage(error, 'Registration failed'))
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
    clearAuthSession()
    return rejectWithValue(extractErrorMessage(error, 'Session expired'))
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
    },
    setUser: (state, action) => {
      state.user = action.payload
      state.isAuthenticated = true
    },
    clearAuth: (state) => {
      state.token = null
      state.user = null
      state.isAuthenticated = false
      state.hydrating = false
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.token = action.payload.token
        state.isAuthenticated = true
        state.error = null
      })
      .addCase(login.rejected, (state, action) => {
        state.error = action.payload
      })
      .addCase(register.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.token = action.payload.token
        state.isAuthenticated = true
        state.error = null
      })
      .addCase(register.rejected, (state, action) => {
        state.error = action.payload
      })
      .addCase(logout.fulfilled, (state) => {
        state.token = null
        state.user = null
        state.isAuthenticated = false
      })
      .addCase(hydrateCurrentUser.pending, (state) => {
        state.hydrating = true
      })
      .addCase(hydrateCurrentUser.fulfilled, (state, action) => {
        state.hydrating = false
        state.user = action.payload
        state.isAuthenticated = Boolean(state.token)
        state.error = null
      })
      .addCase(hydrateCurrentUser.rejected, (state, action) => {
        state.hydrating = false
        state.token = null
        state.user = null
        state.isAuthenticated = false
        state.error = action.payload
      })
  },
})

export const { setSession, setUser, clearAuth } = authSlice.actions
export default authSlice.reducer
