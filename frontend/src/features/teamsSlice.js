import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { teamsAPI, unwrapData, unwrapResults } from '../services/api'

export const fetchTeams = createAsyncThunk('teams/fetchAll', async () => {
  const response = await teamsAPI.getTeams()
  return unwrapResults(response)
})

export const createTeam = createAsyncThunk('teams/create', async (data) => {
  const response = await teamsAPI.createTeam(data)
  return unwrapData(response)
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
      })
      .addCase(fetchTeams.fulfilled, (state, action) => {
        state.loading = false
        state.teams = action.payload
      })
      .addCase(fetchTeams.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      .addCase(createTeam.fulfilled, (state, action) => {
        state.teams.push(action.payload)
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
