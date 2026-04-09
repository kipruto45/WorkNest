import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { tasksAPI, unwrapData, unwrapResults } from '../services/api'
import { extractApiError } from '../utils/apiErrors'

export const fetchMyTasks = createAsyncThunk('tasks/fetchMyTasks', async () => {
  const response = await tasksAPI.getMyTasks()
  return unwrapResults(response)
})

export const fetchOverdueTasks = createAsyncThunk('tasks/fetchOverdue', async () => {
  const response = await tasksAPI.getOverdue()
  return unwrapResults(response)
})

export const fetchKanban = createAsyncThunk('tasks/fetchKanban', async (teamId) => {
  const response = await tasksAPI.getKanban(teamId)
  const data = unwrapData(response) || {}
  return {
    todo: data.todo?.tasks || [],
    in_progress: data.in_progress?.tasks || [],
    in_review: data.in_review?.tasks || [],
    done: data.done?.tasks || [],
  }
})

export const createTask = createAsyncThunk('tasks/create', async (data, { rejectWithValue }) => {
  try {
    const response = await tasksAPI.createTask(data)
    return unwrapData(response)
  } catch (error) {
    return rejectWithValue(extractApiError(error, { fallbackMessage: 'Unable to create task right now.' }))
  }
})

export const updateTask = createAsyncThunk('tasks/update', async ({ id, data }) => {
  const response =
    Object.keys(data).length === 1 && Object.prototype.hasOwnProperty.call(data, 'status')
      ? await tasksAPI.updateTaskStatus(id, data)
      : await tasksAPI.updateTask(id, data)
  return unwrapData(response)
})

export const deleteTask = createAsyncThunk('tasks/delete', async (id) => {
  await tasksAPI.deleteTask(id)
  return id
})

const tasksSlice = createSlice({
  name: 'tasks',
  initialState: {
    myTasks: [],
    overdue: [],
    kanban: { todo: [], in_progress: [], in_review: [], done: [] },
    currentTask: null,
    loading: false,
    error: null,
  },
  reducers: {
    setCurrentTask: (state, action) => {
      state.currentTask = action.payload
    },
    clearTasks: (state) => {
      state.myTasks = []
      state.overdue = []
      state.kanban = { todo: [], in_progress: [], in_review: [], done: [] }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchMyTasks.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchMyTasks.fulfilled, (state, action) => {
        state.loading = false
        state.myTasks = action.payload
      })
      .addCase(fetchMyTasks.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message
      })
      .addCase(fetchOverdueTasks.fulfilled, (state, action) => {
        state.overdue = action.payload
      })
      .addCase(fetchKanban.fulfilled, (state, action) => {
        state.kanban = action.payload
      })
      .addCase(createTask.fulfilled, (state, action) => {
        state.myTasks.push(action.payload)
      })
      .addCase(updateTask.fulfilled, (state, action) => {
        const index = state.myTasks.findIndex((t) => t.id === action.payload.id)
        if (index !== -1) state.myTasks[index] = action.payload
      })
      .addCase(deleteTask.fulfilled, (state, action) => {
        state.myTasks = state.myTasks.filter((t) => t.id !== action.payload)
      })
  },
})

export const { setCurrentTask, clearTasks } = tasksSlice.actions
export default tasksSlice.reducer
