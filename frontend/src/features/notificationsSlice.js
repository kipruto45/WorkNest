import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { notificationsAPI, unwrapData, unwrapResults } from '../services/api'

export const fetchNotifications = createAsyncThunk('notifications/fetchAll', async () => {
  const response = await notificationsAPI.getNotifications()
  return unwrapResults(response)
})

export const fetchUnreadCount = createAsyncThunk('notifications/fetchUnreadCount', async () => {
  const response = await notificationsAPI.getUnreadCount()
  return unwrapData(response).unread_count
})

export const markAsRead = createAsyncThunk('notifications/markAsRead', async (id) => {
  await notificationsAPI.markAsRead(id)
  return id
})

export const markAllAsRead = createAsyncThunk('notifications/markAllAsRead', async () => {
  await notificationsAPI.markAllAsRead()
})

export const markAsUnread = createAsyncThunk('notifications/markAsUnread', async (id) => {
  await notificationsAPI.markAsUnread(id)
  return id
})

const notificationsSlice = createSlice({
  name: 'notifications',
  initialState: {
    items: [],
    unreadCount: 0,
    loading: false,
  },
  reducers: {
    upsertNotification: (state, action) => {
      const incoming = action.payload
      const index = state.items.findIndex((item) => item.id === incoming.id)
      if (index === -1) {
        state.items.unshift(incoming)
        if (!incoming.is_read) {
          state.unreadCount += 1
        }
      } else {
        const previousUnread = !state.items[index].is_read
        const nextUnread = !incoming.is_read
        state.items[index] = { ...state.items[index], ...incoming }
        if (previousUnread !== nextUnread) {
          state.unreadCount += nextUnread ? 1 : -1
        }
      }
    },
    removeNotification: (state, action) => {
      state.items = state.items.filter((item) => item.id !== action.payload)
    },
    setUnreadCount: (state, action) => {
      state.unreadCount = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.loading = true
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload
      })
      .addCase(fetchNotifications.rejected, (state) => {
        state.loading = false
      })
      .addCase(fetchUnreadCount.fulfilled, (state, action) => {
        state.unreadCount = action.payload
      })
      .addCase(markAsRead.fulfilled, (state, action) => {
        const notification = state.items.find((n) => n.id === action.payload)
        if (notification) {
          notification.is_read = true
          state.unreadCount = Math.max(0, state.unreadCount - 1)
        }
      })
      .addCase(markAsUnread.fulfilled, (state, action) => {
        const notification = state.items.find((n) => n.id === action.payload)
        if (notification && notification.is_read) {
          notification.is_read = false
          state.unreadCount += 1
        }
      })
      .addCase(markAllAsRead.fulfilled, (state) => {
        state.items.forEach((n) => (n.is_read = true))
        state.unreadCount = 0
      })
  },
})

export const { upsertNotification, removeNotification, setUnreadCount } = notificationsSlice.actions
export default notificationsSlice.reducer
