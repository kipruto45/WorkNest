import axios from 'axios'
import { clearAuthSession, extractAuthSession, persistAuthSession } from '../utils/authSession'
import { API_BASE_URL, CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'

const API_URL = API_BASE_URL
const PUBLIC_AUTH_PATH_PREFIXES = ['/auth/login/', '/auth/register/', '/auth/password-reset/', '/auth/google/']
let refreshRequest = null
const DEFAULT_API_TIMEOUT_MS = 12000

const resolveApiTimeoutMs = () => {
  const rawTimeout = Number(import.meta?.env?.VITE_API_TIMEOUT_MS)
  if (!Number.isFinite(rawTimeout) || rawTimeout <= 0) {
    return DEFAULT_API_TIMEOUT_MS
  }
  return Math.floor(rawTimeout)
}

const normalizeBaseUrl = (value) => {
  if (!value) return ''
  return value.replace(/\/+$/, '')
}

const buildApiUrl = (url, baseUrl) => {
  if (!url) return url
  const trimmed = String(url)
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed
  }
  const base = normalizeBaseUrl(baseUrl)
  if (!base) return trimmed
  if (trimmed.startsWith('/')) {
    return `${base}${trimmed}`
  }
  return `${base}/${trimmed}`
}

const api = axios.create({
  baseURL: '',
  withCredentials: true,
  timeout: resolveApiTimeoutMs(),
  headers: {
    'Content-Type': 'application/json',
  },
})

const normalizeRequestPath = (url) => {
  const resolvedUrl = buildApiUrl(url, API_URL)
  if (!resolvedUrl) return ''

  try {
    const parsed = new URL(resolvedUrl, window.location.origin)
    return parsed.pathname
  } catch (_error) {
    return String(resolvedUrl)
  }
}

const shouldSkipAuthRefresh = (config) => {
  const requestPath = normalizeRequestPath(config?.url)
  return PUBLIC_AUTH_PATH_PREFIXES.some((prefix) => requestPath.includes(prefix))
}

const shouldAttachAuthHeader = (config) => !shouldSkipAuthRefresh(config)

const redirectToLogin = () => {
  const currentPath = `${window.location.pathname || ''}${window.location.search || ''}`
  const next = currentPath && !currentPath.startsWith('/login') ? `?next=${encodeURIComponent(currentPath)}` : ''
  window.location.replace(`/login${next}`)
}

const refreshSession = async () => {
  const refreshToken = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionRefresh)
  const refreshUrl = buildApiUrl('/auth/refresh/', API_URL)
  const response = await axios.post(refreshUrl, refreshToken ? { refresh: refreshToken } : {}, { withCredentials: true })
  const session = extractAuthSession(unwrapData(response))
  if (!session.isValid) {
    throw new Error('Invalid refresh response')
  }
  persistAuthSession(session)
  return session
}

api.interceptors.request.use((config) => {
  const normalizedUrl = buildApiUrl(config.url, API_URL)
  if (normalizedUrl) {
    config.url = normalizedUrl
  }
  const token = localStorage.getItem(CLIENT_STORAGE_KEYS.sessionAccess)
  if (token && shouldAttachAuthHeader(config)) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  } else if (config.headers?.Authorization) {
    delete config.headers.Authorization
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !shouldSkipAuthRefresh(originalRequest)) {
      originalRequest._retry = true
      try {
        if (!refreshRequest) {
          refreshRequest = refreshSession().finally(() => {
            refreshRequest = null
          })
        }
        const session = await refreshRequest
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers.Authorization = `Bearer ${session.accessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        clearAuthSession()
        redirectToLogin()
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
  verifyEmail: (data) => api.post('/auth/email-verification/verify/', data),
  resendVerification: () => api.post('/auth/email-verification/resend/'),
  getSessions: () => api.get('/auth/sessions/'),
  revokeSession: (id) => api.delete(`/auth/sessions/${id}/`),
  requestPasswordReset: (data) => api.post('/auth/password-reset/', data),
  confirmPasswordReset: (data) => api.post('/auth/password-reset/confirm/', data),
  getGoogleConfig: () => api.get('/auth/google/config/'),
  getGoogleLoginUrl: (nextPath, accountType, flow = 'login', teamName = '') =>
    api.get('/auth/google/login/', {
      params: {
        redirect: 'false',
        next: nextPath,
        account_type: accountType,
        flow,
        team_name: teamName || undefined,
      },
    }),
  authenticateGoogle: (credential) => api.post('/auth/google/auth/', { credential }),
}

export const teamsAPI = {
  getTeams: (params) => api.get('/teams/', { params }),
  createTeam: (data) => api.post('/teams/', data),
  getTeam: (id) => api.get(`/teams/${id}/`),
  updateTeam: (id, data) => api.patch(`/teams/${id}/`, data),
  deleteTeam: (id) => api.delete(`/teams/${id}/`),
  searchAdminTeams: (params) => api.get('/teams/admin/search/', { params }),
  getPinnedTeams: (params) => api.get('/teams/pinned/', { params }),
  getRecentTeams: (params) => api.get('/teams/recent/', { params }),
  togglePin: (id) => api.post(`/teams/${id}/pin/`),
  getTimeline: (id, params) => api.get(`/teams/${id}/timeline/`, { params }),
  getAnnouncements: (id, params) => api.get(`/teams/${id}/announcements/`, { params }),
  createAnnouncement: (id, data) => api.post(`/teams/${id}/announcements/`, data),
  updateAnnouncement: (id, announcementId, data) => api.patch(`/teams/${id}/announcements/${announcementId}/`, data),
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
  getLabels: (params) => api.get('/tasks/labels/', { params }),
  createLabel: (data) => api.post('/tasks/labels/', data),
  updateTaskStatus: (id, data) => api.patch(`/tasks/${id}/status/`, data),
  assignTask: (id, data) => api.patch(`/tasks/${id}/assign/`, data),
  archiveTask: (id) => api.post(`/tasks/${id}/archive/`),
  getChecklist: (id) => api.get(`/tasks/${id}/checklist/`),
  createChecklistItem: (id, data) => api.post(`/tasks/${id}/checklist/`, data),
  updateChecklistItem: (id, data) => api.patch(`/tasks/checklist/${id}/`, data),
  deleteChecklistItem: (id) => api.delete(`/tasks/checklist/${id}/`),
  getWatchers: (id) => api.get(`/tasks/${id}/watchers/`),
  watchTask: (id) => api.post(`/tasks/${id}/watchers/`),
  unwatchTask: (id) => api.delete(`/tasks/${id}/watchers/`),
  getTimeline: (id, params) => api.get(`/tasks/${id}/timeline/`, { params }),
  toggleFavorite: (id) => api.post(`/tasks/${id}/favorite/`),
  getFavorites: (params) => api.get('/tasks/favorites/', { params }),
  getRecent: (params) => api.get('/tasks/recent/', { params }),
  bulkAction: (data) => api.post('/tasks/bulk/', data),
  getKanban: (teamId) => api.get('/tasks/board/', { params: { team: teamId } }),
  getMyTasks: (params) => api.get('/tasks/my-tasks/', { params }),
  getOverdue: () => api.get('/tasks/overdue/'),
  getTemplates: (params) => api.get('/tasks/templates/', { params }),
  createTemplate: (data) => api.post('/tasks/templates/', data),
  createFromTemplate: (id, data) => api.post(`/tasks/templates/${id}/create-task/`, data),
  getSavedViews: (params) => api.get('/tasks/views/saved/', { params }),
  createSavedView: (data) => api.post('/tasks/views/saved/', data),
  updateSavedView: (id, data) => api.patch(`/tasks/views/saved/${id}/`, data),
  deleteSavedView: (id) => api.delete(`/tasks/views/saved/${id}/`),
  getDependencies: (id) => api.get(`/tasks/${id}/dependencies/`),
  createDependency: (id, data) => api.post(`/tasks/${id}/dependencies/`, data),
  deleteDependency: (dependencyId) => api.delete(`/tasks/dependencies/${dependencyId}/`),
  getTimeEntries: (id, params) => api.get(`/tasks/${id}/time-entries/`, { params }),
  createTimeEntry: (id, data) => api.post(`/tasks/${id}/time-entries/`, data),
  startTimeEntry: (id) => api.post(`/tasks/${id}/time-entries/start/`),
  stopTimeEntry: (entryId) => api.post(`/tasks/time-entries/${entryId}/stop/`),
  getTimeSummary: (params) => api.get('/tasks/time-entries/summary/', { params }),
  getMilestones: (teamId, params) => api.get(`/tasks/teams/${teamId}/milestones/`, { params }),
  createMilestone: (teamId, data) => api.post(`/tasks/teams/${teamId}/milestones/`, data),
  updateMilestone: (teamId, milestoneId, data) => api.patch(`/tasks/teams/${teamId}/milestones/${milestoneId}/`, data),
  deleteMilestone: (teamId, milestoneId) => api.delete(`/tasks/teams/${teamId}/milestones/${milestoneId}/`),
  getAutomationRules: (teamId, params) => api.get(`/tasks/teams/${teamId}/automation-rules/`, { params }),
  createAutomationRule: (teamId, data) => api.post(`/tasks/teams/${teamId}/automation-rules/`, data),
  updateAutomationRule: (teamId, ruleId, data) => api.patch(`/tasks/teams/${teamId}/automation-rules/${ruleId}/`, data),
  deleteAutomationRule: (teamId, ruleId) => api.delete(`/tasks/teams/${teamId}/automation-rules/${ruleId}/`),
  getGuestAccess: (taskId) => api.get(`/tasks/${taskId}/guest-access/`),
  createGuestAccess: (taskId, data) => api.post(`/tasks/${taskId}/guest-access/`, data),
  revokeGuestAccess: (accessId) => api.post(`/tasks/guest-access/${accessId}/revoke/`),
  importTasks: (formData, params) =>
    api.post('/tasks/import/', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  exportTasks: (params) => api.get('/tasks/export/', { params }),
}

export const commentsAPI = {
  getComments: (taskId, params) => api.get(`/tasks/${taskId}/comments/`, { params }),
  createComment: (taskId, data) => api.post(`/tasks/${taskId}/comments/`, data),
  updateComment: (id, data) => api.patch(`/comments/${id}/`, data),
  deleteComment: (id) => api.delete(`/comments/${id}/`),
  getHistory: (id, params) => api.get(`/comments/${id}/history/`, { params }),
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
  getAdminCommunications: (params) => api.get('/notifications/admin/communications/', { params }),
  getAdminCommunication: (id) => api.get(`/notifications/admin/communications/${id}/`),
  createAdminCommunication: (data) => api.post('/notifications/admin/communications/', data),
  getSmsLogs: (params) => api.get('/notifications/admin/sms-logs/', { params }),
  getSmsLog: (id) => api.get(`/notifications/admin/sms-logs/${id}/`),
}

export const usersAPI = {
  getProfile: () => api.get('/users/me/'),
  updateProfile: (data) =>
    api.patch('/users/me/', data, data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined),
  requestCredentialChange: (data) => api.post('/users/me/credentials/change/request/', data),
  confirmCredentialChange: (data) => api.post('/users/me/credentials/change/confirm/', data),
  savePhoneSettings: (data) => api.post('/users/me/phone/', data),
  updatePhoneSettings: (data) => api.patch('/users/me/phone/', data),
  requestPhoneVerification: () => api.post('/users/me/phone/verify/request/'),
  confirmPhoneVerification: (data) => api.post('/users/me/phone/verify/confirm/', data),
  getNotificationPreferences: () => api.get('/users/me/notification-preferences/'),
  updateNotificationPreferences: (data) => api.patch('/users/me/notification-preferences/', data),
  searchAdminUsers: (params) => api.get('/users/admin/search/', { params }),
  getAdminUser: (id) => api.get(`/users/admin/${id}/`),
  updateAdminUser: (id, data) => api.patch(`/users/admin/${id}/`, data),
  getPushDevices: (params) => api.get('/users/me/devices/', { params }),
  registerPushDevice: (data) => api.post('/users/me/devices/', data),
  removePushDevice: (id) => api.delete(`/users/me/devices/${id}/`),
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

export const calendarAPI = {
  exportTasksICS: (data) => api.post('/calendar/export/ics/', data),
  previewICSImport: (formData) =>
    api.post('/calendar/import/preview/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  confirmImport: (data) => api.post('/calendar/import/confirm/', data),
  getGoogleStatus: (data) => api.post('/calendar/google/status/', data),
  connectGoogle: (data) => api.post('/calendar/google/connect/', data),
  listGoogleCalendars: (data) => api.post('/calendar/google/calendars/', data),
  selectGoogleCalendar: (data) => api.post('/calendar/google/select-calendar/', data),
  disconnectGoogle: (data) => api.post('/calendar/google/disconnect/', data),
  syncGoogleTasks: (data) => api.post('/calendar/google/sync/', data),
  previewGoogleImport: (data) => api.post('/calendar/google/import/preview/', data),
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
  search: (params) => api.get('/search/', { params }),
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
