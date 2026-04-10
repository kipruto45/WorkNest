import { useEffect, useMemo, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { toast } from 'react-toastify'
import { logout } from '../features/authSlice'
import { fetchUnreadCount } from '../features/notificationsSlice'
import { useRealtimeNotifications } from '../hooks/useRealtimeNotifications'
import { getInitials } from '../utils/formatters'
import { commonAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig'
import { canManageInvitations, resolveMembershipRole } from '../utils/permissions'
import AppLogo from './AppLogo'

const personalNav = [
  { label: 'Dashboard', to: '/dashboard', icon: HomeIcon },
  { label: 'My Tasks', to: '/tasks', icon: QueueIcon },
  { label: 'Teams', to: '/teams', icon: PeopleIcon },
  { label: 'Calendar', to: '/calendar', icon: CalendarIcon },
  { label: 'Notifications', to: '/notifications', icon: BellIcon },
]

const secondaryNav = [
  { label: 'Profile', to: '/profile', icon: ProfileIcon },
  { label: 'Account', to: '/settings', icon: SettingsIcon },
  { label: 'Security', to: '/settings/security', icon: AuditIcon },
]

const adminPrimaryNav = [
  { label: 'Overview', to: '/admin', icon: HomeIcon },
  { label: 'Users', to: '/admin/users', icon: ProfileIcon },
  { label: 'Teams', to: '/admin/teams', icon: PeopleIcon },
  { label: 'Tasks', to: '/admin/tasks', icon: QueueIcon },
  { label: 'Notifications', to: '/admin/notifications', icon: BellIcon },
  { label: 'Communication', to: '/admin/communications', icon: MegaphoneIcon },
  { label: 'Audit Logs', to: '/admin/audit-logs', icon: AuditIcon },
  { label: 'Settings', to: '/admin/settings', icon: SettingsIcon },
]

const routeMeta = [
  { match: /^\/dashboard$/, title: 'Dashboard', description: 'Your personal productivity workspace.' },
  { match: /^\/team-setup/, title: 'Team Setup', description: 'Create the first workspace for your team.' },
  { match: /^\/tasks$/, title: 'My Tasks', description: 'Track personal work, start times, and due dates.' },
  { match: /^\/tasks\/.+/, title: 'Task Detail', description: 'Review the task details and timeline.' },
  { match: /^\/teams\/[^/]+$/, title: 'Team Tasks', description: 'Board view of active team work.' },
  { match: /^\/teams\/[^/]+\/overview/, title: 'Team Dashboard', description: 'Team progress, workload, and priorities.' },
  { match: /^\/teams\/[^/]+\/calendar/, title: 'Team Calendar', description: 'Deadlines, due-soon work, and schedule visibility.' },
  { match: /^\/teams\/[^/]+\/announcements/, title: 'Announcements', description: 'Team communication, updates, and shared messages.' },
  { match: /^\/teams\/[^/]+\/activity/, title: 'Activity Log', description: 'Recent team actions and collaboration timeline.' },
  { match: /^\/teams\/[^/]+\/members/, title: 'Team Members', description: 'Manage roles, access, and collaboration.' },
  { match: /^\/teams\/[^/]+\/analytics/, title: 'Analytics', description: 'Operational metrics, workload, and team performance.' },
  { match: /^\/teams\/[^/]+\/invitations/, title: 'Invitations', description: 'Invite teammates and track responses.' },
  { match: /^\/teams\/[^/]+\/milestones/, title: 'Milestones', description: 'Delivery checkpoints and progress tracking.' },
  { match: /^\/teams\/[^/]+\/automation/, title: 'Automation', description: 'Workflow rules that keep delivery moving.' },
  { match: /^\/teams\/[^/]+\/import-export/, title: 'Import / Export', description: 'Move task data in and out safely.' },
  { match: /^\/teams/, title: 'Teams', description: 'Manage collaboration across team workspaces.' },
  { match: /^\/calendar/, title: 'Calendar', description: 'See what is coming next and when it is due.' },
  { match: /^\/notifications/, title: 'Notifications', description: 'Review mentions, assignments, and reminders.' },
  { match: /^\/profile/, title: 'Profile', description: 'Keep your identity and details up to date.' },
  { match: /^\/settings\/security/, title: 'Security', description: 'Review verification status, sessions, and devices.' },
  { match: /^\/settings/, title: 'Account', description: 'Adjust workspace preferences and controls.' },
  { match: /^\/search/, title: 'Search', description: 'Find tasks and teams quickly.' },
  { match: /^\/archive/, title: 'Archive', description: 'Review archived work and spaces.' },
  { match: /^\/admin\/users(?:\/.*)?$/, title: 'User Management', description: 'Review accounts, membership footprint, and account health.' },
  { match: /^\/admin\/communications/, title: 'Admin Communication', description: 'Broadcast updates to users, teams, or the full platform.' },
  { match: /^\/admin(?:\/.*)?$/, title: 'Admin Dashboard', description: 'High-level platform visibility across usage, activity, and system health.' },
]

function readWorkspacePrefs() {
  try {
    const rawValue = localStorage.getItem(CLIENT_STORAGE_KEYS.workspacePrefs)
    if (!rawValue) return {}
    const parsed = JSON.parse(rawValue)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_error) {
    return {}
  }
}

function writeWorkspacePrefs(nextWorkspace) {
  try {
    const current = readWorkspacePrefs()
    localStorage.setItem(
      CLIENT_STORAGE_KEYS.workspacePrefs,
      JSON.stringify({
        ...current,
        lastWorkspace: nextWorkspace,
      })
    )
  } catch (_error) {
    // Ignore local storage write failures in private browsing modes.
  }
}

function parseRouteTeamId(pathname) {
  const match = String(pathname || '').match(/^\/teams\/([^/]+)/)
  return match ? match[1] : ''
}

export default function Layout() {
  const [isDesktop, setIsDesktop] = useState(() => (typeof window === 'undefined' ? true : window.innerWidth >= 1024))
  const [sidebarOpen, setSidebarOpen] = useState(() => (typeof window === 'undefined' ? true : window.innerWidth >= 1024))
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResults, setSearchResults] = useState({
    tasks: [],
    teams: [],
    people: [],
    comments: [],
    announcements: [],
    milestones: [],
  })
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [paletteLoading, setPaletteLoading] = useState(false)
  const [paletteResults, setPaletteResults] = useState({
    tasks: [],
    teams: [],
    people: [],
    comments: [],
    announcements: [],
    milestones: [],
  })
  const { user } = useSelector((state) => state.auth)
  const { unreadCount } = useSelector((state) => state.notifications)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const isAdminRoute = location.pathname.startsWith('/admin')
  const routeTeamId = useMemo(() => parseRouteTeamId(location.pathname), [location.pathname])
  const workspaceEntries = useMemo(() => {
    const raw = Array.isArray(user?.workspace_options) ? user.workspace_options : []
    const normalized = raw
      .filter((item) => item?.id)
      .map((item) => ({
        id: String(item.id),
        name: item.name || 'Workspace',
        isPersonal: Boolean(item.is_personal),
        role: item.my_role || '',
        allow_manager_invites: Boolean(item.allow_manager_invites),
      }))

    if ((user?.account_type === 'personal' || user?.primary_mode === 'personal') && !normalized.some((item) => item.isPersonal)) {
      normalized.unshift({
        id: 'personal',
        name: 'Personal workspace',
        isPersonal: true,
        role: 'admin',
      })
    }
    if (user?.default_team_id && !normalized.some((item) => item.id === String(user.default_team_id))) {
      normalized.push({
        id: String(user.default_team_id),
        name: 'Team workspace',
        isPersonal: false,
        role: user?.account_type === 'team' ? 'admin' : '',
      })
    }
    return normalized
  }, [user?.workspace_options, user?.default_team_id, user?.account_type, user?.primary_mode])
  const teamWorkspaces = useMemo(() => workspaceEntries.filter((item) => !item.isPersonal), [workspaceEntries])
  const hasPersonalWorkspace = useMemo(() => workspaceEntries.some((item) => item.isPersonal), [workspaceEntries])
  const hasTeamWorkspace = useMemo(
    () => teamWorkspaces.length > 0 || Boolean(user?.has_team_workspaces),
    [teamWorkspaces.length, user?.has_team_workspaces]
  )
  const [workspaceValue, setWorkspaceValue] = useState('personal')
  const showWorkspaceSwitcher = !isAdminRoute && Boolean(user)

  useEffect(() => {
    if (routeTeamId) {
      const nextValue = `team:${routeTeamId}`
      setWorkspaceValue(nextValue)
      writeWorkspacePrefs(nextValue)
      return
    }
    const storedWorkspace = String(readWorkspacePrefs().lastWorkspace || '').trim()
    if (storedWorkspace.startsWith('team:')) {
      const storedTeamId = storedWorkspace.slice(5)
      if (teamWorkspaces.some((item) => item.id === storedTeamId)) {
        setWorkspaceValue(storedWorkspace)
        return
      }
    }
    if (hasPersonalWorkspace) {
      setWorkspaceValue('personal')
      return
    }
    if (teamWorkspaces.length) {
      const nextValue = `team:${teamWorkspaces[0].id}`
      setWorkspaceValue(nextValue)
      writeWorkspacePrefs(nextValue)
      return
    }
    setWorkspaceValue('personal')
  }, [routeTeamId, teamWorkspaces, hasPersonalWorkspace])

  const selectedWorkspaceTeamId = workspaceValue.startsWith('team:') ? workspaceValue.slice(5) : ''
  const fallbackTeamId = user?.account_type === 'team' ? user?.default_team_id || '' : ''
  const activeTeamId = routeTeamId || selectedWorkspaceTeamId || fallbackTeamId
  const isTeamWorkspace = !isAdminRoute && Boolean(activeTeamId)
  const teamBasePath = activeTeamId ? `/teams/${activeTeamId}` : '/team-setup'
  const activeTeamWorkspace = useMemo(
    () => teamWorkspaces.find((workspace) => workspace.id === activeTeamId) || null,
    [teamWorkspaces, activeTeamId]
  )
  const activeTeamRole = resolveMembershipRole({ my_role: activeTeamWorkspace?.role })
  const isAdminWorkspace = activeTeamRole === 'admin'
  const isMemberWorkspace = activeTeamRole === 'member'
  const canAccessInvitations = canManageInvitations({
    role: activeTeamRole,
    allowManagerInvites: Boolean(activeTeamWorkspace?.allow_manager_invites),
  })
  const teamNav = activeTeamId
    ? isMemberWorkspace
      ? [
          { label: 'Dashboard', to: `${teamBasePath}/overview`, icon: HomeIcon },
          { label: 'My Tasks', to: `${teamBasePath}?scope=mine`, icon: QueueIcon },
          { label: 'Team Tasks', to: teamBasePath, icon: QueueIcon },
          { label: 'Calendar', to: `${teamBasePath}/calendar`, icon: CalendarIcon },
          { label: 'Announcements', to: `${teamBasePath}/announcements`, icon: MegaphoneIcon },
          { label: 'Notifications', to: '/notifications', icon: BellIcon },
          { label: 'Members', to: `${teamBasePath}/members`, icon: PeopleIcon },
          { label: 'Activity', to: `${teamBasePath}/activity`, icon: AuditIcon },
        ]
      : [
          { label: 'Dashboard', to: `${teamBasePath}/overview`, icon: HomeIcon },
          { label: 'Tasks', to: teamBasePath, icon: QueueIcon },
          { label: 'Milestones', to: `${teamBasePath}/milestones`, icon: FlagIcon },
          { label: 'Members', to: `${teamBasePath}/members`, icon: PeopleIcon },
          { label: 'Analytics', to: `${teamBasePath}/analytics`, icon: AuditIcon },
          ...(canAccessInvitations ? [{ label: 'Invitations', to: `${teamBasePath}/invitations`, icon: MailIcon }] : []),
          { label: 'Calendar', to: `${teamBasePath}/calendar`, icon: CalendarIcon },
          { label: 'Announcements', to: `${teamBasePath}/announcements`, icon: MegaphoneIcon },
          { label: 'Activity', to: `${teamBasePath}/activity`, icon: AuditIcon },
          { label: 'Automation', to: `${teamBasePath}/automation`, icon: AutomateIcon },
          { label: 'Notifications', to: '/notifications', icon: BellIcon },
          ...(isAdminWorkspace ? [{ label: 'Settings', to: `${teamBasePath}/settings`, icon: SettingsIcon }] : []),
        ]
    : [
        { label: 'Team Setup', to: '/team-setup', icon: HomeIcon },
        { label: 'Calendar', to: '/calendar', icon: CalendarIcon },
        { label: 'Notifications', to: '/notifications', icon: BellIcon },
      ]

  useRealtimeNotifications()

  useEffect(() => {
    const syncViewport = () => {
      const nextIsDesktop = window.innerWidth >= 1024
      setIsDesktop(nextIsDesktop)
      setSidebarOpen((current) => (nextIsDesktop ? true : current && nextIsDesktop))
    }

    syncViewport()
    window.addEventListener('resize', syncViewport)
    return () => window.removeEventListener('resize', syncViewport)
  }, [])

  useEffect(() => {
    dispatch(fetchUnreadCount())
  }, [dispatch])

  const userInitials = useMemo(() => getInitials(user?.name), [user?.name])
  const firstName = user?.first_name || user?.name?.split(' ')[0] || 'there'
  const currentRouteMeta = useMemo(
    () => routeMeta.find((entry) => entry.match.test(location.pathname)) || routeMeta[0],
    [location.pathname]
  )
  const visiblePrimaryNav = isAdminRoute ? adminPrimaryNav : isTeamWorkspace ? teamNav : personalNav
  const visibleSecondaryNav = useMemo(() => {
    if (isAdminRoute) return []
    const items = [...secondaryNav]
    if (user?.is_staff) {
      items.unshift({ label: 'Admin', to: '/admin', icon: AuditIcon })
    }
    return items
  }, [isAdminRoute, user?.is_staff])

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  const handleSearchSubmit = (event) => {
    event.preventDefault()
    const query = searchQuery.trim()
    setSearchFocused(false)
    navigate(query ? `/search?q=${encodeURIComponent(query)}` : '/search')
  }

  const handleWorkspaceSwitch = (event) => {
    const nextValue = event.target.value
    const previousValue = workspaceValue

    if (nextValue === 'personal') {
      if (!hasPersonalWorkspace) {
        setWorkspaceValue(previousValue)
        toast.info(
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-900">
              You do not have a personal account yet. Create one from the register page to access Personal Workspace.
            </p>
            <button
              type="button"
              onClick={() => {
                toast.dismiss()
                dispatch(logout()).finally(() => {
                  navigate('/register?account_type=personal&next=%2Fdashboard')
                })
              }}
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700"
            >
              Register personal account
            </button>
          </div>
        )
        return
      }
      setWorkspaceValue(nextValue)
      writeWorkspacePrefs(nextValue)
      navigate('/dashboard')
      return
    }
    if (nextValue.startsWith('team:')) {
      const nextTeamId = nextValue.slice(5)
      if (!nextTeamId || nextTeamId === '__none__' || !teamWorkspaces.some((item) => item.id === nextTeamId)) {
        setWorkspaceValue(previousValue)
        toast.info('You do not have access to a team dashboard because you do not belong to any group.')
        return
      }
      setWorkspaceValue(nextValue)
      writeWorkspacePrefs(nextValue)
      navigate(`/teams/${nextTeamId}/overview`)
      return
    }
    setWorkspaceValue(previousValue)
  }

  const quickActions = useMemo(() => {
    const base = isTeamWorkspace
      ? isMemberWorkspace
        ? [
            { id: 'dashboard', label: 'Open member dashboard', hint: 'Review your assigned work', to: `${teamBasePath}/overview` },
            { id: 'my-tasks', label: 'Open my tasks', hint: 'Focus on your assigned tasks', to: `${teamBasePath}?scope=mine` },
            { id: 'tasks', label: 'Open team tasks', hint: 'Track shared team delivery', to: teamBasePath },
            { id: 'calendar', label: 'Open calendar', hint: 'Review due dates and deadlines', to: `${teamBasePath}/calendar` },
            { id: 'announcements', label: 'Open announcements', hint: 'Catch up on team updates', to: `${teamBasePath}/announcements` },
            { id: 'activity', label: 'Open activity log', hint: 'See recent team changes', to: `${teamBasePath}/activity` },
            { id: 'settings', label: 'Open settings', hint: 'Adjust profile and notification preferences', to: '/settings' },
          ]
        : [
            { id: 'dashboard', label: 'Open team dashboard', hint: 'Review team progress', to: `${teamBasePath}/overview` },
            { id: 'tasks', label: 'Open team tasks', hint: 'Track team delivery', to: teamBasePath },
            { id: 'create-task', label: 'Create task', hint: 'Capture a new work item fast', to: '/tasks?compose=1' },
            { id: 'milestones', label: 'Review milestones', hint: 'Check delivery checkpoints', to: `${teamBasePath}/milestones` },
            { id: 'members', label: 'Review members', hint: 'See team roster', to: `${teamBasePath}/members` },
            { id: 'analytics', label: 'Open analytics', hint: 'Track workload and completion trends', to: `${teamBasePath}/analytics` },
            ...(canAccessInvitations
              ? [{ id: 'invitations', label: 'Invite teammates', hint: 'Manage invitations', to: `${teamBasePath}/invitations` }]
              : []),
            { id: 'calendar', label: 'Open calendar', hint: 'Review team deadlines', to: `${teamBasePath}/calendar` },
            { id: 'announcements', label: 'Open announcements', hint: 'Share updates and messages', to: `${teamBasePath}/announcements` },
            { id: 'activity', label: 'Open activity log', hint: 'Review team timeline', to: `${teamBasePath}/activity` },
            { id: 'settings', label: 'Open settings', hint: 'Adjust account and notification preferences', to: '/settings' },
          ]
      : [
          { id: 'dashboard', label: 'Go to dashboard', hint: 'Open your personal workspace', to: '/dashboard' },
          { id: 'tasks', label: 'Open my tasks', hint: 'Jump into your execution center', to: '/tasks' },
          { id: 'create-task', label: 'Create task', hint: 'Open the task composer instantly', to: '/tasks?compose=1' },
          { id: 'search', label: 'Search workspace', hint: 'Find tasks, teams, and updates', to: '/search' },
          { id: 'notifications', label: 'Check notifications', hint: 'Review mentions and reminders', to: '/notifications' },
          { id: 'calendar', label: 'Open calendar', hint: 'Review planned work and deadlines', to: '/calendar' },
          { id: 'settings', label: 'Open settings', hint: 'Adjust profile and notification controls', to: '/settings' },
          { id: 'security', label: 'Open security', hint: 'Review sessions and devices', to: '/settings/security' },
        ]
    return base.concat(
      user?.is_staff ? [{ id: 'admin', label: 'Open admin dashboard', hint: 'Platform-wide visibility', to: '/admin' }] : []
    )
  }, [canAccessInvitations, isMemberWorkspace, isTeamWorkspace, teamBasePath, user?.is_staff])

  const headerSearchGroups = useMemo(
    () =>
      [
        { key: 'tasks', label: 'Tasks', items: searchResults.tasks },
        { key: 'teams', label: 'Teams', items: searchResults.teams },
        { key: 'milestones', label: 'Milestones', items: searchResults.milestones },
        { key: 'people', label: 'People', items: searchResults.people },
      ].filter((group) => group.items.length > 0),
    [searchResults]
  )

  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen(true)
      } else if (event.key === 'Escape') {
        setPaletteOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    const query = searchQuery.trim()
    if (!query) {
      setSearchLoading(false)
      setSearchResults({ tasks: [], teams: [], people: [], comments: [], announcements: [], milestones: [] })
      return undefined
    }

    let isCancelled = false
    const timeoutId = window.setTimeout(async () => {
      setSearchLoading(true)
      try {
        const response = await commonAPI.search({ q: query, limit: 4, types: 'tasks,teams,people,milestones' })
        const sections = unwrapData(response)?.sections || {}
        if (!isCancelled) {
          setSearchResults({
            tasks: sections.tasks || [],
            teams: sections.teams || [],
            people: sections.people || [],
            comments: [],
            announcements: [],
            milestones: sections.milestones || [],
          })
        }
      } catch (_error) {
        if (!isCancelled) {
          setSearchResults({ tasks: [], teams: [], people: [], comments: [], announcements: [], milestones: [] })
        }
      } finally {
        if (!isCancelled) {
          setSearchLoading(false)
        }
      }
    }, 160)

    return () => {
      isCancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [searchQuery])

  useEffect(() => {
    if (!paletteOpen) return undefined

    let isCancelled = false
    const timeoutId = window.setTimeout(async () => {
      setPaletteLoading(true)
      try {
        const query = paletteQuery.trim()
        const response = await commonAPI.search({ q: query, limit: 5 })
        const sections = unwrapData(response)?.sections || {}
        if (!isCancelled) {
          setPaletteResults({
            tasks: sections.tasks || [],
            teams: sections.teams || [],
            people: sections.people || [],
            comments: sections.comments || [],
            announcements: sections.announcements || [],
            milestones: sections.milestones || [],
          })
        }
      } catch (error) {
        if (!isCancelled) {
          setPaletteResults({ tasks: [], teams: [], people: [], comments: [], announcements: [], milestones: [] })
        }
      } finally {
        if (!isCancelled) {
          setPaletteLoading(false)
        }
      }
    }, 180)

    return () => {
      isCancelled = true
      window.clearTimeout(timeoutId)
    }
  }, [paletteOpen, paletteQuery])

  const handlePaletteNavigate = (to) => {
    setPaletteOpen(false)
    setPaletteQuery('')
    navigate(to)
  }

  const handleHeaderSearchNavigate = (to) => {
    setSearchFocused(false)
    setSearchQuery('')
    navigate(to)
  }

  return (
    <div className="app-shell h-screen overflow-hidden px-2 py-2 sm:px-3 sm:py-3 md:px-5 md:py-5">
      <div className="relative flex h-[calc(100vh-16px)] overflow-hidden rounded-[26px] border border-slate-200/90 bg-[rgba(255,255,255,0.72)] shadow-[0_20px_60px_rgba(15,23,42,0.06)] backdrop-blur-xl sm:h-[calc(100vh-24px)] sm:rounded-[32px]">
        {!isDesktop && sidebarOpen ? (
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}
            className="absolute inset-0 z-20 bg-emerald-950/10 backdrop-blur-sm lg:hidden"
          />
        ) : null}

        <aside
          className={`absolute inset-y-0 left-0 z-30 overflow-hidden border-r border-slate-200/80 bg-[rgba(250,250,247,0.96)] shadow-[0_24px_60px_rgba(15,23,42,0.12)] transition-all duration-300 lg:relative lg:translate-x-0 lg:bg-[rgba(250,250,247,0.86)] lg:shadow-none ${
            isDesktop
              ? sidebarOpen
                ? 'w-72'
                : 'w-[92px]'
              : sidebarOpen
                ? 'w-[min(86vw,18rem)] translate-x-0'
                : 'w-[min(86vw,18rem)] -translate-x-full'
          }`}
        >
          <div className="flex h-full min-h-0 flex-col p-4">
            <div className="flex items-center justify-between rounded-[24px] border border-slate-200/80 bg-white/90 px-4 py-4 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
              <div className={`${sidebarOpen ? 'block' : 'hidden'}`}>
                <AppLogo
                  to="/dashboard"
                  subtitle="Workspace"
                  imageClassName="h-11 w-11"
                  titleClassName="mt-1 font-display text-2xl font-bold text-slate-950"
                  subtitleClassName="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"
                />
              </div>
              <div className={`${sidebarOpen ? 'hidden' : 'block'}`}>
                <img src="/logo_hd.png" alt="WorkNest logo" className="h-11 w-11 rounded-2xl object-cover" />
              </div>
              <button
                type="button"
                onClick={() => setSidebarOpen((current) => !current)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>

            <div className="mt-6 min-h-0 flex-1 space-y-8 overflow-y-auto pr-1">
              <div>
                <p className={`px-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 ${sidebarOpen ? 'block' : 'hidden'}`}>
                  Navigation
                </p>
                <nav className="mt-3 space-y-2">
                  {visiblePrimaryNav.map((item) => (
                    <NavItem key={item.to} item={item} sidebarOpen={sidebarOpen} />
                  ))}
                </nav>
              </div>

              {visibleSecondaryNav.length ? (
                <div>
                  <p className={`px-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 ${sidebarOpen ? 'block' : 'hidden'}`}>
                    Account
                  </p>
                  <nav className="mt-3 space-y-2">
                    {visibleSecondaryNav.map((item) => (
                      <NavItem key={item.to} item={item} sidebarOpen={sidebarOpen} />
                    ))}
                  </nav>
                </div>
              ) : null}
            </div>

            <div className="mt-6 shrink-0 rounded-[24px] border border-slate-200/80 bg-white/88 px-4 py-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
              <div className="flex items-center gap-3">
                <UserAvatar user={user} fallback={userInitials} className="h-11 w-11 rounded-2xl" />
                {sidebarOpen ? (
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-950">{user?.name || 'Workspace User'}</p>
                    <p className="truncate text-sm text-slate-500">{user?.email || 'Signed in'}</p>
                  </div>
                ) : null}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-4 inline-flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50"
              >
                Sign out
              </button>
            </div>
          </div>
        </aside>

        <div className="relative z-10 flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-[rgba(246,246,242,0.8)] px-4 py-4 backdrop-blur-xl sm:px-5 md:px-8">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div className="mb-3 lg:hidden">
                  <button
                    type="button"
                    onClick={() => setSidebarOpen(true)}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                  </button>
                </div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{currentRouteMeta.title}</p>
                <h1 className="mt-1 font-display text-xl font-bold text-slate-950 sm:text-2xl">{currentRouteMeta.title}</h1>
                <p className="mt-2 text-sm text-slate-500">
                  {location.pathname === '/dashboard' ? `Welcome back, ${firstName}. ${currentRouteMeta.description}` : currentRouteMeta.description}
                </p>
                {showWorkspaceSwitcher ? (
                  <div className="mt-4 max-w-sm">
                    <label className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Active workspace
                      <select
                        value={workspaceValue}
                        onChange={handleWorkspaceSwitch}
                        className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-900 outline-none transition-colors focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100"
                      >
                        {workspaceEntries
                          .filter((item) => item.isPersonal)
                          .map((item) => (
                            <option key={item.id} value="personal">
                              Personal workspace
                            </option>
                          ))}
                        {!hasPersonalWorkspace ? (
                          <option value="personal">Personal workspace (register required)</option>
                        ) : null}
                        {teamWorkspaces.map((team) => (
                          <option key={team.id} value={`team:${team.id}`}>
                            {team.name}
                          </option>
                        ))}
                        {!hasTeamWorkspace ? <option value="team:__none__">Team dashboard (no group access)</option> : null}
                      </select>
                    </label>
                  </div>
                ) : null}
              </div>

              <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
                <form
                  onSubmit={handleSearchSubmit}
                  className="relative flex w-full items-center gap-3 rounded-[20px] border border-slate-200/90 bg-white/94 px-4 py-3 shadow-[0_8px_20px_rgba(15,23,42,0.04)] lg:w-[360px]"
                >
                  <SearchIcon className="h-5 w-5 text-slate-400" />
                  <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    onFocus={() => setSearchFocused(true)}
                    onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
                    className="w-full border-none bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                    placeholder="Search tasks, teams, or updates"
                  />
                  <button
                    type="button"
                    onClick={() => setPaletteOpen(true)}
                    className="rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500"
                  >
                    ⌘K
                  </button>

                  {searchFocused && searchQuery.trim() ? (
                    <div className="absolute left-0 right-0 top-[calc(100%+12px)] z-30 overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-[0_24px_60px_rgba(15,23,42,0.12)]">
                      <div className="border-b border-slate-100 px-4 py-3">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                          {searchLoading ? 'Searching workspace' : 'Quick results'}
                        </p>
                      </div>
                      <div className="max-h-[360px] overflow-y-auto px-2 py-2">
                        {headerSearchGroups.length ? (
                          headerSearchGroups.map((group) => (
                            <div key={group.key} className="px-2 py-2">
                              <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{group.label}</p>
                              <div className="mt-2 space-y-1">
                                {group.items.map((item) => (
                                  <button
                                    key={`${group.key}-${item.id}`}
                                    type="button"
                                    onMouseDown={(event) => {
                                      event.preventDefault()
                                      handleHeaderSearchNavigate(item.href)
                                    }}
                                    className="w-full rounded-2xl px-3 py-3 text-left transition-colors hover:bg-slate-50"
                                  >
                                    <p className="font-semibold text-slate-950">{item.title}</p>
                                    <p className="mt-1 text-sm text-slate-500">{item.subtitle || 'Open result'}</p>
                                  </button>
                                ))}
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="px-4 py-5 text-sm text-slate-500">
                            {searchLoading ? 'Looking for matches...' : 'No quick matches yet. Open the full search workspace for broader filters.'}
                          </div>
                        )}
                      </div>
                      <div className="border-t border-slate-100 px-3 py-3">
                        <button
                          type="submit"
                          className="w-full rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3 text-left transition-colors hover:bg-slate-50"
                        >
                          <p className="font-semibold text-slate-950">Open full search results</p>
                          <p className="mt-1 text-sm text-slate-500">Use filters, grouped results, and broader search coverage.</p>
                        </button>
                      </div>
                    </div>
                  ) : null}
                </form>

                <NavLink
                  to="/notifications"
                  className="flex items-center gap-3 rounded-[20px] border border-slate-200/90 bg-white/92 px-4 py-3 shadow-[0_8px_20px_rgba(15,23,42,0.04)] transition-colors hover:bg-white"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                    <BellIcon className="h-5 w-5" />
                  </span>
                  <div className="text-left">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Unread</p>
                    <p className="font-semibold text-slate-950">{unreadCount}</p>
                  </div>
                </NavLink>

                <NavLink
                  to="/profile"
                  className="flex items-center gap-3 rounded-[20px] border border-slate-200/90 bg-white/92 px-4 py-3 shadow-[0_8px_20px_rgba(15,23,42,0.04)] transition-colors hover:bg-white"
                >
                  <UserAvatar user={user} fallback={userInitials} className="h-10 w-10 rounded-2xl text-sm" />
                  <div className="text-left">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Profile</p>
                    <p className="font-semibold text-slate-950">{firstName}</p>
                  </div>
                </NavLink>
              </div>
            </div>
          </header>

          {user?.email && !user?.email_verified ? (
            <div className="border-b border-slate-200/80 bg-[rgba(246,246,242,0.8)] px-5 py-4 md:px-8">
              <section className="rounded-[24px] border border-amber-200/80 bg-amber-50/70 px-5 py-4 shadow-[0_10px_26px_rgba(180,83,9,0.06)]">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Verification pending</p>
                    <h2 className="mt-2 text-lg font-semibold text-slate-950">Confirm your email to strengthen recovery and account trust.</h2>
                    <p className="mt-1 text-sm text-slate-600">
                      Your workspace is live, but verified email keeps login recovery, notifications, and future security upgrades reliable.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <NavLink to="/verify-email" className="btn-primary">
                      Verify email
                    </NavLink>
                    <NavLink to="/settings/security" className="btn-secondary">
                      Open security
                    </NavLink>
                  </div>
                </div>
              </section>
            </div>
          ) : null}

          <main className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 sm:px-5 sm:py-5 md:px-8 md:py-8">
            <Outlet />
          </main>
        </div>
      </div>

      {paletteOpen ? (
        <CommandPalette
          query={paletteQuery}
          loading={paletteLoading}
          quickActions={quickActions}
          tasks={paletteResults.tasks}
          teams={paletteResults.teams}
          people={paletteResults.people}
          comments={paletteResults.comments}
          announcements={paletteResults.announcements}
          milestones={paletteResults.milestones}
          onClose={() => setPaletteOpen(false)}
          onChangeQuery={setPaletteQuery}
          onNavigate={handlePaletteNavigate}
        />
      ) : null}
    </div>
  )
}

function CommandPalette({ query, loading, quickActions, tasks, teams, people, comments, announcements, milestones, onClose, onChangeQuery, onNavigate }) {
  const hasResults =
    quickActions.length || tasks.length || teams.length || people.length || comments.length || announcements.length || milestones.length

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-emerald-950/10 px-4 py-16 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-3xl overflow-hidden rounded-[30px] border border-slate-200/90 bg-[rgba(255,255,255,0.96)] shadow-[0_32px_120px_rgba(15,23,42,0.18)] backdrop-blur-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4">
          <SearchIcon className="h-5 w-5 text-slate-400" />
          <input
            autoFocus
            value={query}
            onChange={(event) => onChangeQuery(event.target.value)}
            className="w-full border-none bg-transparent text-base text-slate-950 outline-none placeholder:text-slate-400"
            placeholder="Search tasks, teams, or jump to an action"
          />
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
          >
            Esc
          </button>
        </div>

        <div className="grid gap-6 px-5 py-5 lg:grid-cols-[0.9fr,1.1fr]">
          <section className="space-y-3">
            <PaletteSectionTitle title="Quick actions" />
            <div className="space-y-2">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  onClick={() => onNavigate(action.to)}
                  className="w-full rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3 text-left transition-colors hover:bg-slate-50"
                >
                  <p className="font-semibold text-slate-950">{action.label}</p>
                  <p className="mt-1 text-sm text-slate-500">{action.hint}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-5">
            <div>
              <PaletteSectionTitle title="Tasks" />
              <div className="mt-3 space-y-2">
                {tasks.map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => onNavigate(task.href || `/tasks/${task.id}`)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <p className="font-semibold text-slate-950">{task.title}</p>
                    <p className="mt-1 text-sm text-slate-500">{task.subtitle || 'Task'}{task.status ? ` • ${task.status.replaceAll('_', ' ')}` : ''}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <PaletteSectionTitle title="Teams" />
              <div className="mt-3 space-y-2">
                {teams.map((team) => (
                  <button
                    key={team.id}
                    type="button"
                    onClick={() => onNavigate(team.href || `/teams/${team.id}/overview`)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <p className="font-semibold text-slate-950">{team.title || team.name}</p>
                    <p className="mt-1 text-sm text-slate-500">{team.subtitle || team.description || 'Open team workspace'}</p>
                  </button>
                ))}
              </div>
            </div>

            {milestones.length ? (
              <div>
                <PaletteSectionTitle title="Milestones" />
                <div className="mt-3 space-y-2">
                  {milestones.map((milestone) => (
                    <button
                      key={milestone.id}
                      type="button"
                      onClick={() => onNavigate(milestone.href || '/teams')}
                      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                    >
                      <p className="font-semibold text-slate-950">{milestone.title}</p>
                      <p className="mt-1 text-sm text-slate-500">{milestone.subtitle || 'Milestone'}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {people.length ? (
              <div>
                <PaletteSectionTitle title="People" />
                <div className="mt-3 space-y-2">
                  {people.map((person) => (
                    <button
                      key={person.id}
                      type="button"
                      onClick={() => onNavigate(person.href || '/profile')}
                      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                    >
                      <p className="font-semibold text-slate-950">{person.title}</p>
                      <p className="mt-1 text-sm text-slate-500">{person.subtitle}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {comments.length ? (
              <div>
                <PaletteSectionTitle title="Recent Matches" />
                <div className="mt-3 space-y-2">
                  {comments.map((comment) => (
                    <button
                      key={comment.id}
                      type="button"
                      onClick={() => onNavigate(comment.href)}
                      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                    >
                      <p className="font-semibold text-slate-950">{comment.title}</p>
                      <p className="mt-1 text-sm text-slate-500">{comment.subtitle}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {announcements.length ? (
              <div>
                <PaletteSectionTitle title="Announcements" />
                <div className="mt-3 space-y-2">
                  {announcements.map((announcement) => (
                    <button
                      key={announcement.id}
                      type="button"
                      onClick={() => onNavigate(announcement.href)}
                      className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                    >
                      <p className="font-semibold text-slate-950">{announcement.title}</p>
                      <p className="mt-1 text-sm text-slate-500">{announcement.subtitle}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {!loading && !hasResults ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-[#fcfcfb] px-4 py-6 text-sm text-slate-500">
                Nothing matched yet. Try a task title, team name, or use a quick action.
              </div>
            ) : null}
            {loading ? <p className="text-sm text-slate-500">Searching workspace…</p> : null}
          </section>
        </div>
      </div>
    </div>
  )
}

function PaletteSectionTitle({ title }) {
  return <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
}

function NavItem({ item, sidebarOpen }) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.to === '/dashboard'}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-[18px] px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
          isActive
            ? 'bg-emerald-700 text-white shadow-[0_12px_24px_rgba(15,118,110,0.18)]'
            : 'text-slate-600 hover:bg-white hover:text-slate-950'
        }`
      }
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-2xl ${sidebarOpen ? 'bg-slate-100' : 'bg-slate-100'} text-slate-700`}
      >
        <Icon className="h-5 w-5" />
      </span>
      {sidebarOpen ? <span>{item.label}</span> : null}
    </NavLink>
  )
}

function UserAvatar({ user, fallback, className = '' }) {
  if (user?.avatar) {
    return (
      <img
        src={user.avatar}
        alt={user?.name || 'User avatar'}
        className={`object-cover border border-slate-200 bg-slate-100 ${className}`}
      />
    )
  }

  return (
    <div className={`flex items-center justify-center bg-emerald-700 font-semibold text-white ${className}`}>
      {fallback}
    </div>
  )
}

function HomeIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m3 10.5 9-7 9 7M5 9.5V20h14V9.5" />
    </svg>
  )
}

function QueueIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
    </svg>
  )
}

function CalendarIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 3v3M17 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13H4V6a1 1 0 0 1 1-1Z" />
    </svg>
  )
}

function PeopleIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 21v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm9 10v-1a4 4 0 0 0-3-3.87M15 3.13A4 4 0 0 1 15 11" />
    </svg>
  )
}

function FlagIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M5 3v18M5 4h10l-1 3 4 2-4 2 1 3H5" />
    </svg>
  )
}

function AutomateIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 7h16M7 4v6M13 14h7M13 14a4 4 0 1 0 0 8h7M13 14a4 4 0 1 1 0-8h7" />
    </svg>
  )
}

function SearchIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m21 21-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" />
    </svg>
  )
}

function BellIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.4-1.4a2 2 0 0 1-.6-1.44V11a6 6 0 1 0-12 0v3.16c0 .54-.21 1.05-.6 1.44L4 17h5m6 0v1a3 3 0 1 1-6 0v-1m6 0H9" />
    </svg>
  )
}

function MailIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6h16v12H4z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m4 7 8 6 8-6" />
    </svg>
  )
}

function MegaphoneIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 11.5v1a2.5 2.5 0 0 0 2.5 2.5H7l1.5 4h2L9.5 15h2.24l5.82 2.91A1 1 0 0 0 19 17V7a1 1 0 0 0-1.44-.9L11.74 9H5.5A2.5 2.5 0 0 0 3 11.5Z" />
    </svg>
  )
}

function ProfileIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm7 9a7 7 0 0 0-14 0" />
    </svg>
  )
}

function SettingsIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7Zm7.4-3.5a7.6 7.6 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a8.2 8.2 0 0 0-1.8-1l-.4-2.5h-4l-.4 2.5a8.2 8.2 0 0 0-1.8 1l-2.4-1-2 3.4 2 1.5a7.6 7.6 0 0 0-.1 1c0 .34.03.67.1 1l-2 1.5 2 3.4 2.4-1a8.2 8.2 0 0 0 1.8 1l.4 2.5h4l.4-2.5a8.2 8.2 0 0 0 1.8-1l2.4 1 2-3.4-2-1.5c.07-.33.1-.66.1-1Z" />
    </svg>
  )
}

function AuditIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7h8M8 12h8M8 17h5M6 4h12a1 1 0 0 1 1 1v14H5V5a1 1 0 0 1 1-1Z" />
    </svg>
  )
}
