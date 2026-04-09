import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { authAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { normalizeTeamEntity } from '../utils/teamEntities'
import { setUser } from './authSlice'

export const fetchTeams = createAsyncThunk('teams/fetchAll', async () => {
  const response = await teamsAPI.getTeams()
  return unwrapResults(response).map(normalizeTeamEntity)
})

export const createTeam = createAsyncThunk('teams/create', async (data, { dispatch, rejectWithValue }) => {
  try {
    const response = await teamsAPI.createTeam(data)
    const team = normalizeTeamEntity(unwrapData(response))
    try {
      const currentUserResponse = await authAPI.getCurrentUser()
      dispatch(setUser(unwrapData(currentUserResponse)))
    } catch (_error) {
      // Team creation should still succeed even if the user bootstrap refresh is temporarily unavailable.
    }
    return team
  } catch (error) {
    return rejectWithValue(
      extractApiError(error, {
        fallbackMessage: 'Failed to create team.',
        forbiddenMessage: 'You are not authorized to create a team.',
        serverMessage: 'Server error while creating team.',
      })
    )
  }
})

export const updateTeam = createAsyncThunk('teams/update', async ({ id, data }) => {
  const response = await teamsAPI.updateTeam(id, data)
  return unwrapData(response)
})

export const deleteTeam = createAsyncThunk('teams/delete', async (id) => {
  await teamsAPI.deleteTeam(id)
  return id
})

export const fetchTeamMembers = createAsyncThunk('teams/fetchMembers', async (teamId) => {
  const response = await teamsAPI.getTeamMembers(teamId)
  return { teamId, members: unwrapResults(response) }
})

export const addTeamMember = createAsyncThunk('teams/addMember', async ({ teamId, data }) => {
  const response = await teamsAPI.inviteMember(teamId, data)
  return unwrapData(response)
})

const teamsSlice = createSlice({
  name: 'teams',
  initialState: {
    teams: [],
    currentTeam: null,
    members: [],
    loading: false,
    error: null,
  },
  reducers: {
    setCurrentTeam: (state, action) => {
      state.currentTeam = action.payload
    },
    clearTeams: (state) => {
      state.teams = []
      state.currentTeam = null
      state.members = []
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTeams.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchTeams.fulfilled, (state, action) => {
        state.loading = false
        state.teams = action.payload
      })
      .addCase(fetchTeams.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      .addCase(createTeam.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createTeam.fulfilled, (state, action) => {
        state.loading = false
        state.teams.push(action.payload)
      })
      .addCase(createTeam.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload?.message || action.payload || action.error.message
      })
      .addCase(updateTeam.fulfilled, (state, action) => {
        const index = state.teams.findIndex((t) => t.id === action.payload.id)
        if (index !== -1) state.teams[index] = action.payload
      })
      .addCase(deleteTeam.fulfilled, (state, action) => {
        state.teams = state.teams.filter((t) => t.id !== action.payload)
      })
      .addCase(fetchTeamMembers.fulfilled, (state, action) => {
        if (state.currentTeam?.id === action.payload.teamId) {
          state.members = action.payload.members
        }
      })
  },
})

export const { setCurrentTeam, clearTeams } = teamsSlice.actions
export default teamsSlice.reducer
