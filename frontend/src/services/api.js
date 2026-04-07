import axios from 'axios'
import { extractAuthSession, persistAuthSession } from '../utils/authSession'
import { API_BASE_URL, CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'

const API_URL = API_BASE_URL

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionAccess)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const refreshToken = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionRefresh)
        const response = await axios.post(`${API_URL}/auth/refresh/`, {
          refresh: refreshToken,
        })
        const session = extractAuthSession(unwrapData(response))
        if (!session.isValid) {
          throw new Error('Invalid refresh response')
        }
        persistAuthSession(session)
        originalRequest.headers.Authorization = `Bearer ${session.accessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionAccess)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionRefresh)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const unwrapData = (response) => response?.data?.data ?? response?.data ?? null

export const unwrapResults = (response) => {
  const payload = unwrapData(response)
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

export const unwrapMeta = (response) => {
  const payload = unwrapData(response)
  if (payload && !Array.isArray(payload) && Array.isArray(payload.results)) {
    return payload
  }
  return {
    count: Array.isArray(payload) ? payload.length : 0,
    next: null,
    previous: null,
    results: Array.isArray(payload) ? payload : [],
  }
}

export const authAPI = {
  login: (data) => api.post('/auth/login/', data),
  register: (data) => api.post('/auth/register/', data),
  logout: (data) => api.post('/auth/logout/', data),
  getCurrentUser: () => api.get('/auth/me/'),
  requestPasswordReset: (data) => api.post('/auth/password-reset/', data),
  confirmPasswordReset: (data) => api.post('/auth/password-reset/confirm/', data),
  getGoogleConfig: () => api.get('/auth/google/config/'),
  getGoogleLoginUrl: () => api.get('/auth/google/login/', { params: { redirect: 'false' } }),
  authenticateGoogle: (credential) => api.post('/auth/google/auth/', { credential }),
}

export const teamsAPI = {
  getTeams: (params) => api.get('/teams/', { params }),
  createTeam: (data) => api.post('/teams/', data),
  getTeam: (id) => api.get(`/teams/${id}/`),
  updateTeam: (id, data) => api.patch(`/teams/${id}/`, data),
  deleteTeam: (id) => api.delete(`/teams/${id}/`),
  getTeamMembers: (id, params) => api.get(`/teams/${id}/members/`, { params }),
  inviteMember: (id, data) => api.post(`/teams/${id}/members/invite/`, data),
  getInvitations: (id, params) => api.get(`/teams/${id}/invitations/`, { params }),
  updateInvitationRole: (id, invitationId, data) => api.patch(`/teams/${id}/invitations/${invitationId}/role/`, data),
  updateMemberRole: (id, memberId, data) => api.patch(`/teams/${id}/members/${memberId}/role/`, data),
  removeMember: (id, userId) => api.delete(`/teams/${id}/members/${userId}/`),
  archiveTeam: (id) => api.post(`/teams/${id}/archive/`),
}

export const tasksAPI = {
  getTasks: (params) => api.get('/tasks/', { params }),
  createTask: (data) => api.post('/tasks/', data),
  getTask: (id) => api.get(`/tasks/${id}/`),
  updateTask: (id, data) => api.patch(`/tasks/${id}/`, data),
  deleteTask: (id) => api.delete(`/tasks/${id}/`),
  updateTaskStatus: (id, data) => api.patch(`/tasks/${id}/status/`, data),
  assignTask: (id, data) => api.patch(`/tasks/${id}/assign/`, data),
  archiveTask: (id) => api.post(`/tasks/${id}/archive/`),
  getKanban: (teamId) => api.get('/tasks/board/', { params: { team: teamId } }),
  getMyTasks: (params) => api.get('/tasks/my-tasks/', { params }),
  getOverdue: () => api.get('/tasks/overdue/'),
}

export const commentsAPI = {
  getComments: (taskId, params) => api.get(`/tasks/${taskId}/comments/`, { params }),
  createComment: (taskId, data) => api.post(`/tasks/${taskId}/comments/`, data),
  updateComment: (id, data) => api.patch(`/comments/${id}/`, data),
  deleteComment: (id) => api.delete(`/comments/${id}/`),
  replyToComment: (id, data) => api.post(`/comments/${id}/reply/`, data),
  toggleReaction: (id, data) => api.post(`/comments/${id}/reactions/`, data),
}

export const notificationsAPI = {
  getNotifications: (params) => api.get('/notifications/', { params }),
  getNotification: (id) => api.get(`/notifications/${id}/`),
  markAsRead: (id) => api.patch(`/notifications/${id}/read/`),
  markAsUnread: (id) => api.patch(`/notifications/${id}/unread/`),
  markAllAsRead: () => api.patch('/notifications/mark-all-read/'),
  deleteNotification: (id) => api.delete(`/notifications/${id}/`),
  getUnreadCount: () => api.get('/notifications/unread-count/'),
  sendAdminNotification: (data) => api.post('/notifications/admin/send/', data),
}

export const usersAPI = {
  getProfile: () => api.get('/users/me/'),
  updateProfile: (data) =>
    api.patch('/users/me/', data, data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined),
  searchAdminUsers: (params) => api.get('/users/admin/search/', { params }),
}

export const dashboardAPI = {
  getAdminOverview: () => api.get('/dashboard/admin/overview/'),
  getPersonalSummary: () => api.get('/dashboard/me/summary/'),
  getPersonalTasks: (params) => api.get('/dashboard/me/tasks/', { params }),
  getPersonalOverdue: (params) => api.get('/dashboard/me/overdue/', { params }),
  getCompletedThisWeek: (params) => api.get('/dashboard/me/completed-this-week/', { params }),
  getPersonalCalendar: (params) => api.get('/dashboard/me/calendar/', { params }),
  getTeamSummary: (teamId) => api.get(`/dashboard/teams/${teamId}/summary/`),
  getTeamActivity: (teamId) => api.get(`/dashboard/teams/${teamId}/activity/`),
  getTeamProgress: (teamId) => api.get(`/dashboard/teams/${teamId}/progress/`),
  getTeamCalendar: (teamId, params) => api.get(`/dashboard/teams/${teamId}/calendar/`, { params }),
  getTeamWorkload: (teamId) => api.get(`/dashboard/teams/${teamId}/workload/`),
  getTeamStatusDistribution: (teamId) => api.get(`/dashboard/teams/${teamId}/status-distribution/`),
  getTeamPriorityDistribution: (teamId) => api.get(`/dashboard/teams/${teamId}/priority-distribution/`),
}

export const invitationsAPI = {
  getInvitation: (token) => api.get(`/invitations/${token}/`),
  accept: (token) => api.post(`/invitations/${token}/accept/`),
  decline: (token) => api.post(`/invitations/${token}/decline/`),
  resend: (invitationId) => api.post(`/invitations/${invitationId}/resend/`),
  revoke: (invitationId) => api.post(`/invitations/${invitationId}/revoke/`),
}

export const auditLogsAPI = {
  getAll: (params) => api.get('/audit-logs/', { params }),
  getForTeam: (teamId, params) => api.get(`/teams/${teamId}/audit-logs/`, { params }),
}

export const commonAPI = {
  getHealth: () => api.get('/health/'),
  getSystemInfo: () => api.get('/system/info/'),
}

export const attachmentsAPI = {
  getForTask: (taskId) => api.get(`/tasks/${taskId}/attachments/`),
  uploadForTask: (taskId, formData) =>
    api.post(`/tasks/${taskId}/attachments/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getAttachment: (id) => api.get(`/attachments/${id}/`),
  previewAttachment: (id) => api.get(`/attachments/${id}/preview/`, { responseType: 'blob' }),
  downloadAttachment: (id) => api.get(`/attachments/${id}/download/`, { responseType: 'blob' }),
  deleteAttachment: (id) => api.delete(`/attachments/${id}/`),
}

export default api
