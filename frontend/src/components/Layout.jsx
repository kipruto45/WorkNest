import { useEffect, useMemo, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { logout } from '../features/authSlice'
import { fetchUnreadCount } from '../features/notificationsSlice'
import { useRealtimeNotifications } from '../hooks/useRealtimeNotifications'
import { getInitials } from '../utils/formatters'
import { tasksAPI, teamsAPI, unwrapResults } from '../services/api'
import AppLogo from './AppLogo'

const primaryNav = [
  { label: 'Dashboard', to: '/dashboard', icon: HomeIcon },
  { label: 'Tasks', to: '/tasks', icon: QueueIcon },
  { label: 'Teams', to: '/teams', icon: PeopleIcon },
  { label: 'Calendar', to: '/calendar', icon: CalendarIcon },
  { label: 'Notifications', to: '/notifications', icon: BellIcon },
]

const secondaryNav = [
  { label: 'Profile', to: '/profile', icon: ProfileIcon },
  { label: 'Account', to: '/settings', icon: SettingsIcon },
]

const adminPrimaryNav = [
  { label: 'Overview', to: '/admin', icon: HomeIcon },
  { label: 'Users', to: '/admin/users', icon: ProfileIcon },
  { label: 'Teams', to: '/admin/teams', icon: PeopleIcon },
  { label: 'Tasks', to: '/admin/tasks', icon: QueueIcon },
  { label: 'Notifications', to: '/admin/notifications', icon: BellIcon },
  { label: 'Messaging', to: '/admin/messaging', icon: MegaphoneIcon },
  { label: 'Audit Logs', to: '/admin/audit-logs', icon: AuditIcon },
  { label: 'Settings', to: '/admin/settings', icon: SettingsIcon },
]

const routeMeta = [
  { match: /^\/dashboard$/, title: 'Dashboard', description: 'Your personal productivity workspace.' },
  { match: /^\/tasks/, title: 'Tasks', description: 'Track assigned work, deadlines, and status.' },
  { match: /^\/teams/, title: 'Teams', description: 'Manage collaboration across team workspaces.' },
  { match: /^\/calendar/, title: 'Calendar', description: 'See what is coming next and when it is due.' },
  { match: /^\/notifications/, title: 'Notifications', description: 'Review mentions, assignments, and reminders.' },
  { match: /^\/profile/, title: 'Profile', description: 'Keep your identity and details up to date.' },
  { match: /^\/settings/, title: 'Account', description: 'Adjust workspace preferences and controls.' },
  { match: /^\/search/, title: 'Search', description: 'Find tasks and teams quickly.' },
  { match: /^\/archive/, title: 'Archive', description: 'Review archived work and spaces.' },
  { match: /^\/admin(?:\/.*)?$/, title: 'Admin Dashboard', description: 'High-level platform visibility across usage, activity, and system health.' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [paletteLoading, setPaletteLoading] = useState(false)
  const [paletteResults, setPaletteResults] = useState({ tasks: [], teams: [] })
  const { user } = useSelector((state) => state.auth)
  const { unreadCount } = useSelector((state) => state.notifications)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const isAdminRoute = location.pathname.startsWith('/admin')

  useRealtimeNotifications()

  useEffect(() => {
    dispatch(fetchUnreadCount())
  }, [dispatch])

  const userInitials = useMemo(() => getInitials(user?.name), [user?.name])
  const firstName = user?.first_name || user?.name?.split(' ')[0] || 'there'
  const currentRouteMeta = useMemo(
    () => routeMeta.find((entry) => entry.match.test(location.pathname)) || routeMeta[0],
    [location.pathname]
  )
  const visiblePrimaryNav = isAdminRoute ? adminPrimaryNav : primaryNav
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
    navigate(query ? `/search?q=${encodeURIComponent(query)}` : '/search')
  }

  const quickActions = useMemo(
    () =>
      [
        { id: 'dashboard', label: 'Go to dashboard', hint: 'Open your personal workspace', to: '/dashboard' },
        { id: 'tasks', label: 'Open my tasks', hint: 'Jump into your execution center', to: '/tasks' },
        { id: 'notifications', label: 'Check notifications', hint: 'Review mentions and reminders', to: '/notifications' },
        { id: 'calendar', label: 'Open calendar', hint: 'Review planned work and deadlines', to: '/calendar' },
        { id: 'teams', label: 'Browse teams', hint: 'Move between workspaces quickly', to: '/teams' },
      ].concat(user?.is_staff ? [{ id: 'admin', label: 'Open admin dashboard', hint: 'Platform-wide visibility', to: '/admin' }] : []),
    [user?.is_staff]
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
    if (!paletteOpen) return undefined

    let isCancelled = false
    const timeoutId = window.setTimeout(async () => {
      setPaletteLoading(true)
      try {
        const query = paletteQuery.trim()
        const params = query ? { search: query, page_size: 5 } : { page_size: 5 }
        const [tasksResponse, teamsResponse] = await Promise.all([tasksAPI.getTasks(params), teamsAPI.getTeams(params)])
        if (!isCancelled) {
          setPaletteResults({
            tasks: unwrapResults(tasksResponse),
            teams: unwrapResults(teamsResponse),
          })
        }
      } catch (error) {
        if (!isCancelled) {
          setPaletteResults({ tasks: [], teams: [] })
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

  return (
    <div className="app-shell bg-[#f7f8f6] px-3 py-3 md:px-5 md:py-5">
      <div className="relative flex min-h-[calc(100vh-24px)] overflow-hidden rounded-[30px] border border-slate-200 bg-[#fbfbfa] shadow-[0_20px_60px_rgba(15,23,42,0.06)]">

        <aside
          className={`relative z-10 border-r border-slate-200 bg-white transition-all duration-300 ${
            sidebarOpen ? 'w-72' : 'w-[92px]'
          }`}
        >
          <div className="flex h-full flex-col p-4">
            <div className="flex items-center justify-between rounded-[22px] border border-slate-200 bg-[#fcfcfb] px-4 py-4">
              <div className={`${sidebarOpen ? 'block' : 'hidden'}`}>
                <AppLogo
                  to="/dashboard"
                  subtitle="Workspace"
                  imageClassName="h-11 w-11"
                  titleClassName="mt-1 font-display text-2xl font-bold text-slate-950"
                  subtitleClassName="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700"
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

            <div className="mt-6 flex-1 space-y-8">
              <div>
                <p className={`px-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 ${sidebarOpen ? 'block' : 'hidden'}`}>
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
                  <p className={`px-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 ${sidebarOpen ? 'block' : 'hidden'}`}>
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

            <div className="mt-6 rounded-[22px] border border-slate-200 bg-[#fcfcfb] px-4 py-4">
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
          <header className="border-b border-slate-200 bg-[#fbfbfa] px-5 py-4 md:px-8">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{currentRouteMeta.title}</p>
                <h1 className="mt-1 font-display text-2xl font-bold text-slate-950">{currentRouteMeta.title}</h1>
                <p className="mt-2 text-sm text-slate-500">
                  {location.pathname === '/dashboard' ? `Welcome back, ${firstName}. ${currentRouteMeta.description}` : currentRouteMeta.description}
                </p>
              </div>

              <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
                <form
                  onSubmit={handleSearchSubmit}
                  className="flex w-full items-center gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3 lg:w-[320px]"
                >
                  <SearchIcon className="h-5 w-5 text-slate-400" />
                  <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
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
                </form>

                <NavLink
                  to="/notifications"
                  className="flex items-center gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3 transition-colors hover:bg-slate-50"
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
                  className="flex items-center gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3 transition-colors hover:bg-slate-50"
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

          <main className="flex-1 overflow-auto px-5 py-5 md:px-8 md:py-8">
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
          onClose={() => setPaletteOpen(false)}
          onChangeQuery={setPaletteQuery}
          onNavigate={handlePaletteNavigate}
        />
      ) : null}
    </div>
  )
}

function CommandPalette({ query, loading, quickActions, tasks, teams, onClose, onChangeQuery, onNavigate }) {
  const hasResults = quickActions.length || tasks.length || teams.length

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-950/30 px-4 py-16 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-3xl overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_32px_120px_rgba(15,23,42,0.22)]"
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
                    onClick={() => onNavigate(`/tasks/${task.id}`)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <p className="font-semibold text-slate-950">{task.title}</p>
                    <p className="mt-1 text-sm text-slate-500">{task.team_name || 'Task'} • {task.status?.replaceAll('_', ' ')}</p>
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
                    onClick={() => onNavigate(`/teams/${team.id}/overview`)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <p className="font-semibold text-slate-950">{team.name}</p>
                    <p className="mt-1 text-sm text-slate-500">{team.description || 'Open team workspace'}</p>
                  </button>
                ))}
              </div>
            </div>

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
  return <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{title}</p>
}

function NavItem({ item, sidebarOpen }) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.to === '/dashboard'}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-colors ${
          isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
        }`
      }
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
          sidebarOpen ? 'bg-slate-100' : 'bg-slate-100'
        } text-slate-700`}
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
    <div className={`flex items-center justify-center bg-emerald-600 font-semibold text-white ${className}`}>
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
