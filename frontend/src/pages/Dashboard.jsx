import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { dashboardAPI, notificationsAPI, tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { createTeam } from '../features/teamsSlice'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, formatRelativeDate, getInitials, toSentenceCase } from '../utils/formatters'

const dashboardSurface = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const compactSurface = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function Dashboard() {
  const { user } = useSelector((state) => state.auth)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [assignedTasks, setAssignedTasks] = useState([])
  const [overdueTasks, setOverdueTasks] = useState([])
  const [completedThisWeek, setCompletedThisWeek] = useState([])
  const [notifications, setNotifications] = useState([])
  const [teams, setTeams] = useState([])
  const [teamsRefreshing, setTeamsRefreshing] = useState(false)
  const [pinnedTeams, setPinnedTeams] = useState([])
  const [recentTeams, setRecentTeams] = useState([])
  const [favoriteTasks, setFavoriteTasks] = useState([])
  const [recentTasks, setRecentTasks] = useState([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const {
    register: registerTeam,
    handleSubmit: handleCreateSubmit,
    reset: resetCreateForm,
    setError: setCreateError,
    clearErrors: clearCreateErrors,
    formState: { errors: createErrors, isSubmitting: isCreating },
  } = useForm()

  const loadDashboard = useCallback(
    async ({ silent = false } = {}) => {
      if (!silent) {
        setLoading(true)
      } else {
        setTeamsRefreshing(true)
      }
      try {
        const [
          summaryResponse,
          tasksResponse,
          overdueResponse,
          completedResponse,
          notificationsResponse,
          teamsResponse,
          pinnedTeamsResponse,
          recentTeamsResponse,
          favoriteTasksResponse,
          recentTasksResponse,
        ] = await Promise.all([
          dashboardAPI.getPersonalSummary(),
          dashboardAPI.getPersonalTasks(),
          dashboardAPI.getPersonalOverdue(),
          dashboardAPI.getCompletedThisWeek(),
          notificationsAPI.getNotifications(),
          teamsAPI.getTeams({ page_size: 6 }),
          teamsAPI.getPinnedTeams({ page_size: 6 }),
          teamsAPI.getRecentTeams({ page_size: 6 }),
          tasksAPI.getFavorites({ page_size: 6 }),
          tasksAPI.getRecent({ page_size: 6 }),
        ])

        setSummary(unwrapData(summaryResponse)?.summary || {})
        setAssignedTasks(unwrapResults(tasksResponse))
        setOverdueTasks(unwrapResults(overdueResponse))
        setCompletedThisWeek(unwrapResults(completedResponse))
        setNotifications(unwrapResults(notificationsResponse))
        setTeams(unwrapResults(teamsResponse))
        setPinnedTeams(unwrapResults(pinnedTeamsResponse))
        setRecentTeams(unwrapResults(recentTeamsResponse))
        setFavoriteTasks(unwrapResults(favoriteTasksResponse))
        setRecentTasks(unwrapResults(recentTasksResponse))
      } finally {
        if (!silent) {
          setLoading(false)
        } else {
          setTeamsRefreshing(false)
        }
      }
    },
    []
  )

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const dueSoonTasks = useMemo(() => {
    const now = new Date()
    const soon = new Date()
    soon.setDate(soon.getDate() + 5)

    return assignedTasks
      .filter((task) => {
        if (!task.due_date || task.status === 'done') return false
        const dueDate = new Date(task.due_date)
        return dueDate >= now && dueDate <= soon
      })
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
  }, [assignedTasks])

  const urgentTasks = useMemo(() => {
    const nearDeadline = dueSoonTasks.filter((task) => task.priority === 'high' || task.priority === 'critical')
    const merged = [...overdueTasks, ...nearDeadline]
    return merged.filter((task, index, array) => array.findIndex((item) => item.id === task.id) === index).slice(0, 6)
  }, [dueSoonTasks, overdueTasks])

  const statusDistribution = useMemo(() => {
    const counts = assignedTasks.reduce(
      (accumulator, task) => {
        accumulator[task.status] = (accumulator[task.status] || 0) + 1
        return accumulator
      },
      { todo: 0, in_progress: 0, in_review: 0, done: 0 }
    )

    const maxValue = Math.max(1, ...Object.values(counts))

    return [
      { label: 'To do', value: counts.todo, width: `${(counts.todo / maxValue) * 100}%` },
      { label: 'In progress', value: counts.in_progress, width: `${(counts.in_progress / maxValue) * 100}%` },
      { label: 'In review', value: counts.in_review, width: `${(counts.in_review / maxValue) * 100}%` },
      { label: 'Done', value: counts.done, width: `${(counts.done / maxValue) * 100}%` },
    ]
  }, [assignedTasks])

  const upcomingDeadlines = useMemo(() => dueSoonTasks.slice(0, 5), [dueSoonTasks])
  const previewNotifications = useMemo(() => notifications.slice(0, 5), [notifications])
  const firstName = user?.first_name || user?.name?.split(' ')[0] || 'there'
  const weeklyCompletionSeries = useMemo(() => {
    const today = new Date()
    const startOfWeek = new Date(today)
    const dayOffset = (today.getDay() + 6) % 7
    startOfWeek.setDate(today.getDate() - dayOffset)
    startOfWeek.setHours(0, 0, 0, 0)

    return Array.from({ length: 7 }, (_, index) => {
      const date = new Date(startOfWeek)
      date.setDate(startOfWeek.getDate() + index)
      const count = completedThisWeek.filter((task) => {
        const reference = task.completed_at || task.updated_at
        if (!reference) return false
        const completedAt = new Date(reference)
        return completedAt.toDateString() === date.toDateString()
      }).length

      return {
        label: ['M', 'T', 'W', 'T', 'F', 'S', 'S'][index],
        count,
      }
    })
  }, [completedThisWeek])
  const maxWeeklyCount = Math.max(1, ...weeklyCompletionSeries.map((item) => item.count))
  const teamWorkspacePreview = useMemo(() => {
    const now = new Date()
    return teams
      .map((team) => {
        const relevantTasks = assignedTasks.filter((task) => String(task.team || task.team_id || '') === String(team.id))
        const dueSoonCount = relevantTasks.filter((task) => {
          if (!task.due_date || task.status === 'done') return false
          const dueDate = new Date(task.due_date)
          const soon = new Date()
          soon.setDate(soon.getDate() + 5)
          return dueDate >= now && dueDate <= soon
        }).length

        return {
          ...team,
          myTaskCount: relevantTasks.length,
          dueSoonCount,
        }
      })
      .sort((left, right) => right.myTaskCount - left.myTaskCount || right.dueSoonCount - left.dueSoonCount)
      .slice(0, 3)
  }, [assignedTasks, teams])
  const continueItems = useMemo(() => recentTasks.slice(0, 4), [recentTasks])
  const favoriteTaskItems = useMemo(() => favoriteTasks.slice(0, 4), [favoriteTasks])
  const pinnedTeamItems = useMemo(() => pinnedTeams.slice(0, 4), [pinnedTeams])
  const recentTeamItems = useMemo(() => recentTeams.slice(0, 4), [recentTeams])

  if (loading) {
    return <LoadingState label="Loading your personal dashboard" />
  }

  const handleOpenCreateModal = () => {
    clearCreateErrors()
    setShowCreateModal(true)
  }

  const handleCloseCreateModal = () => {
    clearCreateErrors()
    resetCreateForm()
    setShowCreateModal(false)
  }

  const handleCreateTeam = async (data) => {
    clearCreateErrors()
    try {
      const team = await dispatch(
        createTeam({
          name: data.name.trim(),
          description: data.description?.trim() || '',
        })
      ).unwrap()
      toast.success(
        <div className="flex flex-wrap items-center gap-3">
          <span>Team created. Invite your teammates by email next.</span>
          <button
            type="button"
            onClick={() => navigate(`/teams/${team.id}/overview`)}
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700"
          >
            Open team
          </button>
        </div>
      )
      handleCloseCreateModal()
      await loadDashboard({ silent: true })
      navigate(`/teams/${team.id}/overview`)
    } catch (error) {
      const apiError =
        typeof error === 'string'
          ? { message: error, fieldErrors: {} }
          : error?.fieldErrors || error?.status
            ? error
            : extractApiError(error, {
                fallbackMessage: 'Failed to create team.',
                forbiddenMessage: 'You are not authorized to create a team.',
                serverMessage: 'Server error while creating team.',
              })

      Object.entries(apiError.fieldErrors || {}).forEach(([field, value]) => {
        const message = Array.isArray(value) ? value[0] : value
        if (field === 'name' || field === 'description') {
          setCreateError(field, { type: 'server', message })
        }
      })
      setCreateError('root', { type: 'server', message: apiError.message })
      console.error('create_team_failed', {
        location: 'dashboard',
        status: apiError.status,
        requestId: apiError.requestId,
        errors: apiError.errors,
      })
      toast.error(apiError.message)
    }
  }

  return (
    <div className="space-y-6">
      <section className={`${dashboardSurface} overflow-hidden`}>
        <div className="grid gap-8 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <div className="mb-5 flex items-center gap-4">
              <DashboardAvatar user={user} />
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Personal Dashboard</p>
                <p className="mt-1 text-sm text-slate-500">Your profile updates appear here as soon as they are saved.</p>
              </div>
            </div>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-slate-950">
              Welcome back, {firstName}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              {overdueTasks.length
                ? `You have ${overdueTasks.length} overdue task${overdueTasks.length === 1 ? '' : 's'} and ${dueSoonTasks.length} item${dueSoonTasks.length === 1 ? '' : 's'} due soon.`
                : `Your workload looks steady today with ${dueSoonTasks.length} task${dueSoonTasks.length === 1 ? '' : 's'} due soon and ${completedThisWeek.length} completed this week.`}
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/tasks" className="inline-flex items-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700">
                Open my tasks
              </Link>
              <Link to="/calendar" className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50">
                View calendar
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <OverviewCard
              label="Today"
              value={summary.due_today ?? dueSoonTasks.filter((task) => formatRelativeDate(task.due_date) === 'Today').length}
              note="tasks due today"
            />
            <OverviewCard
              label="Attention"
              value={summary.overdue_tasks ?? overdueTasks.length}
              note="overdue items"
            />
            <OverviewCard
              label="Momentum"
              value={summary.completed_this_week ?? completedThisWeek.length}
              note="completed this week"
            />
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<QueueIcon className="h-5 w-5" />}
          title="Tasks Assigned to Me"
          value={summary.assigned_tasks ?? assignedTasks.length}
          trend={`${statusDistribution.find((item) => item.label === 'In progress')?.value || 0} currently in progress`}
        />
        <MetricCard
          icon={<AlertIcon className="h-5 w-5" />}
          title="Overdue Tasks"
          value={summary.overdue_tasks ?? overdueTasks.length}
          trend={overdueTasks.length ? 'Needs attention first' : 'Nothing overdue right now'}
          accent="text-amber-700 bg-amber-50"
        />
        <MetricCard
          icon={<CheckIcon className="h-5 w-5" />}
          title="Completed This Week"
          value={summary.completed_this_week ?? completedThisWeek.length}
          trend="Recent wins across your teams"
        />
        <MetricCard
          icon={<CalendarIcon className="h-5 w-5" />}
          title="Due Today or Soon"
          value={summary.due_soon ?? dueSoonTasks.length}
          trend="Within the next 5 days"
          accent="text-indigo-700 bg-indigo-50"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="My Tasks"
            title="Assigned work"
            action={<Link to="/tasks" className="text-sm font-semibold text-emerald-700">View all</Link>}
          />

          <div className="mt-5 space-y-3">
            {assignedTasks.length === 0 ? (
              <EmptyState
                eyebrow="Assigned work"
                title="No tasks assigned yet"
                description="Tasks assigned to you will appear here with due dates, status, and priority."
              />
            ) : (
              assignedTasks.slice(0, 6).map((task) => (
                <Link
                  key={task.id}
                  to={`/tasks/${task.id}`}
                  className="block rounded-[22px] border border-slate-200 bg-[#fcfcfb] px-4 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white"
                >
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <PriorityChip priority={task.priority} />
                        <StatusChip status={task.status} />
                      </div>
                      <h3 className="mt-3 truncate text-base font-semibold text-slate-950">{task.title}</h3>
                      <p className="mt-1 text-sm text-slate-600">
                        <TeamReference task={task} /> • Due {formatDate(task.due_date)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 xl:min-w-[180px] xl:justify-end">
                      <div className="text-right">
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Due window</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{formatRelativeDate(task.due_date)}</p>
                      </div>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Productivity" title="Tasks by status" />

          <div className="mt-6 space-y-5">
            {statusDistribution.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700">{item.label}</span>
                  <span className="text-slate-500">{item.value}</span>
                </div>
                <div className="mt-2 h-2.5 rounded-full bg-slate-100">
                  <div
                    className="h-2.5 rounded-full bg-emerald-600 transition-all duration-700"
                    style={{ width: item.width }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className={`mt-8 ${compactSurface} p-5`}>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Weekly completions</p>
            <div className="mt-4 grid grid-cols-7 items-end gap-2">
              {weeklyCompletionSeries.map((item, index) => (
                <div key={`${item.label}-${index}`} className="flex flex-col items-center gap-2">
                  <div
                    className={`w-full rounded-t-xl ${index === 6 ? 'bg-emerald-600' : 'bg-slate-200'}`}
                    style={{ height: `${item.count ? Math.max(18, (item.count / maxWeeklyCount) * 96) : 8}px` }}
                  />
                  <span className="text-[11px] font-medium text-slate-500">
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-slate-500">
              {completedThisWeek.length
                ? `${completedThisWeek.length} task${completedThisWeek.length === 1 ? '' : 's'} completed this week.`
                : 'No completions recorded yet this week.'}
            </p>
          </div>
        </section>
      </div>

      <section className={`${dashboardSurface} p-6 lg:p-7`}>
        <SectionHeader
          eyebrow="My Teams"
          title="Member workspaces"
          action={
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={handleOpenCreateModal} className="text-sm font-semibold text-emerald-700">
                Create team
              </button>
              <Link to="/teams" className="text-sm font-semibold text-emerald-700">Open teams</Link>
            </div>
          }
        />

        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          Only teams you belong to appear here, so every workspace link takes you into a member-only team dashboard.
        </p>
        {teamsRefreshing ? (
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Refreshing teams…</p>
        ) : null}

        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {teamWorkspacePreview.length === 0 ? (
            <EmptyState
              eyebrow="Teams"
              title="No team workspaces yet"
              description="As soon as you join or create a team, its workspace dashboard will appear here for quick access."
              action={
                <button type="button" onClick={handleOpenCreateModal} className="btn-primary">
                  Create your first team
                </button>
              }
            />
          ) : (
            teamWorkspacePreview.map((team) => (
              <Link
                key={team.id}
                to={`/teams/${team.id}/overview`}
                className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 font-semibold text-white">
                      {getInitials(team.name)}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{team.name}</p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        {toSentenceCase(team.my_role || team.my_membership?.role || 'member')}
                      </p>
                    </div>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
                    Team
                  </span>
                </div>

                <p className="mt-4 min-h-[48px] text-sm leading-6 text-slate-600">
                  {team.description || 'Open the team dashboard to review progress, workload, deadlines, and collaboration activity.'}
                </p>

                <div className="mt-5 grid grid-cols-3 gap-3">
                  <WorkspaceMetric label="Members" value={team.member_count || 0} />
                  <WorkspaceMetric label="My tasks" value={team.myTaskCount} />
                  <WorkspaceMetric label="Due soon" value={team.dueSoonCount} />
                </div>
              </Link>
            ))
          )}
          {teamsRefreshing && teamWorkspacePreview.length > 0
            ? Array.from({ length: Math.max(0, 3 - teamWorkspacePreview.length) }).map((_, index) => (
                <div
                  key={`team-skeleton-${index}`}
                  className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-5 animate-pulse"
                >
                  <div className="h-10 w-10 rounded-2xl bg-slate-200" />
                  <div className="mt-4 h-4 w-3/4 rounded bg-slate-200" />
                  <div className="mt-2 h-3 w-1/2 rounded bg-slate-200" />
                  <div className="mt-5 grid grid-cols-3 gap-3">
                    <div className="h-8 rounded bg-slate-200" />
                    <div className="h-8 rounded bg-slate-200" />
                    <div className="h-8 rounded bg-slate-200" />
                  </div>
                </div>
              ))
            : null}
        </div>
      </section>

      {showCreateModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/30 px-4 backdrop-blur-sm">
          <div className="page-shell w-full max-w-xl p-6 md:p-8">
            <h3 className="font-display text-3xl font-bold text-emerald-950">Create a new team</h3>
            <p className="mt-2 text-sm leading-6 text-soft">Start a workspace for shared task planning, invites, and delivery tracking.</p>

            <form onSubmit={handleCreateSubmit(handleCreateTeam)} className="mt-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Team name</label>
                <input
                  {...registerTeam('name', {
                    required: 'Team name is required.',
                    validate: (value) => value.trim().length > 0 || 'Team name is required.',
                  })}
                  className="input-field"
                  placeholder="Growth Squad"
                />
                {createErrors.name ? <p className="mt-2 text-sm text-red-500">{createErrors.name.message}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Description</label>
                <textarea
                  {...registerTeam('description')}
                  className="input-field min-h-[140px]"
                  placeholder="What does this team own?"
                />
                {createErrors.description ? <p className="mt-2 text-sm text-red-500">{createErrors.description.message}</p> : null}
              </div>

              {createErrors.root ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {createErrors.root.message}
                </div>
              ) : null}

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={handleCloseCreateModal} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={isCreating} className="btn-primary">
                  {isCreating ? 'Creating...' : 'Create team'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Continue" title="Recent task context" />
          <div className="mt-5 space-y-3">
            {continueItems.length === 0 ? (
              <EmptyState
                eyebrow="Recent tasks"
                title="No recent work yet"
                description="As you open tasks, your recent items will show up here so you can jump back in quickly."
              />
            ) : (
              continueItems.map((entry) => (
                <Link key={entry.id} to={`/tasks/${entry.task?.id}`} className={`block ${compactSurface} p-4 transition hover:-translate-y-0.5 hover:bg-white`}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-950">{entry.task?.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {entry.task?.team_name || 'Workspace'} • {formatRelativeDate(entry.last_accessed_at)}
                      </p>
                    </div>
                    <StatusChip status={entry.task?.status || 'todo'} />
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Favorites" title="Pinned workspaces and starred tasks" />
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className={`${compactSurface} p-4`}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Pinned teams</p>
              <div className="mt-4 space-y-3">
                {pinnedTeamItems.length === 0 ? (
                  <p className="text-sm text-slate-500">Pin your most-used teams to keep them close.</p>
                ) : (
                  pinnedTeamItems.map((entry) => (
                    <Link key={entry.id} to={`/teams/${entry.team?.id}/overview`} className="block rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-900 transition hover:border-slate-300">
                      {entry.team?.name}
                    </Link>
                  ))
                )}
              </div>
            </div>

            <div className={`${compactSurface} p-4`}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Favorite tasks</p>
              <div className="mt-4 space-y-3">
                {favoriteTaskItems.length === 0 ? (
                  <p className="text-sm text-slate-500">Star high-signal tasks from the task detail page.</p>
                ) : (
                  favoriteTaskItems.map((entry) => (
                    <Link key={entry.id} to={`/tasks/${entry.task?.id}`} className="block rounded-2xl border border-slate-200 bg-white px-4 py-3 transition hover:border-slate-300">
                      <p className="truncate text-sm font-semibold text-slate-950">{entry.task?.title}</p>
                      <p className="mt-1 text-xs text-slate-500">{entry.task?.team_name || 'Workspace'}</p>
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className={`${dashboardSurface} p-6 lg:p-7`}>
        <SectionHeader eyebrow="Workspaces" title="Pinned and recent teams" />
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className={`${compactSurface} p-5`}>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Pinned first</p>
            <div className="mt-4 space-y-3">
              {(pinnedTeamItems.length ? pinnedTeamItems : recentTeamItems).slice(0, 4).map((entry) => {
                const team = entry.team || entry
                return (
                  <Link key={entry.id} to={`/teams/${team?.id}/overview`} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 transition hover:border-slate-300">
                    <span className="text-sm font-semibold text-slate-950">{team?.name}</span>
                    <span className="text-xs uppercase tracking-[0.16em] text-slate-500">{team?.member_count || 0} members</span>
                  </Link>
                )
              })}
            </div>
          </div>

          <div className={`${compactSurface} p-5`}>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Recently opened</p>
            <div className="mt-4 space-y-3">
              {recentTeamItems.length === 0 ? (
                <p className="text-sm text-slate-500">As you move through team workspaces, they’ll show up here.</p>
              ) : (
                recentTeamItems.map((entry) => (
                  <Link key={entry.id} to={`/teams/${entry.team?.id}/overview`} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 transition hover:border-slate-300">
                    <span className="text-sm font-semibold text-slate-950">{entry.team?.name}</span>
                    <span className="text-xs text-slate-500">{formatRelativeDate(entry.last_accessed_at)}</span>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.92fr,1.08fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Urgent Work" title="Overdue and near-deadline tasks" />

          <div className="mt-5 space-y-3">
            {urgentTasks.length === 0 ? (
              <EmptyState
                eyebrow="Urgency"
                title="No urgent tasks"
                description="You do not have overdue or high-priority near-deadline tasks right now."
              />
            ) : (
              urgentTasks.map((task) => (
                <Link
                  key={task.id}
                  to={`/tasks/${task.id}`}
                  className="block rounded-[22px] border border-amber-200 bg-amber-50/60 px-4 py-4 transition-all duration-200 hover:border-amber-300 hover:bg-amber-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-base font-semibold text-slate-950">{task.title}</h3>
                      <p className="mt-1 text-sm text-slate-600">
                        <TeamReference task={task} /> • {toSentenceCase(task.status)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
                        {task.is_overdue ? 'Overdue' : 'Due soon'}
                      </p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{formatDate(task.due_date)}</p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Notifications"
            title="Recent activity"
            action={<Link to="/notifications" className="text-sm font-semibold text-emerald-700">Open all</Link>}
          />

          <div className="mt-5 space-y-3">
            {previewNotifications.length === 0 ? (
              <EmptyState
                eyebrow="Notifications"
                title="No new notifications"
                description="Mentions, assignments, comments, and reminders will appear here."
              />
            ) : (
              previewNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`rounded-[22px] border px-4 py-4 ${
                    notification.is_read ? 'border-slate-200 bg-[#fcfcfb]' : 'border-emerald-200 bg-emerald-50/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{notification.title}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{notification.message}</p>
                    </div>
                    <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                      {formatRelativeDate(notification.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Completed This Week"
            title="Recently finished"
            action={<Link to="/tasks" className="text-sm font-semibold text-emerald-700">Go to tasks</Link>}
          />

          <div className="mt-5 space-y-3">
            {completedThisWeek.length === 0 ? (
              <EmptyState
                eyebrow="Completed"
                title="Nothing completed yet"
                description="Completed tasks from this week will show up here as progress starts to build."
              />
            ) : (
              completedThisWeek.slice(0, 5).map((task) => (
                <div key={task.id} className={`flex items-center justify-between gap-4 ${compactSurface} px-4 py-4`}>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-950">{task.title}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      <TeamReference task={task} />
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">Completed</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{formatDate(task.updated_at)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Upcoming Deadlines"
            title="What is coming next"
            action={<Link to="/calendar" className="text-sm font-semibold text-emerald-700">Open calendar</Link>}
          />

          <div className="mt-5 space-y-3">
            {upcomingDeadlines.length === 0 ? (
              <EmptyState
                eyebrow="Upcoming"
                title="No upcoming deadlines"
                description="Tasks with approaching due dates will surface here for quick review."
              />
            ) : (
              upcomingDeadlines.map((task) => (
                <Link
                  key={task.id}
                  to={`/tasks/${task.id}`}
                  className={`flex items-center justify-between gap-4 ${compactSurface} px-4 py-4 transition-all duration-200 hover:border-slate-300 hover:bg-white`}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-950">{task.title}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      <TeamReference task={task} /> • {toSentenceCase(task.priority)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {formatRelativeDate(task.due_date)}
                    </p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{formatDate(task.due_date)}</p>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function DashboardAvatar({ user }) {
  const initials = getInitials(user?.name || 'You')

  if (user?.avatar) {
    return (
      <img
        src={user.avatar}
        alt={user?.name || 'User avatar'}
        className="h-16 w-16 rounded-[22px] border border-slate-200 object-cover shadow-[0_12px_28px_rgba(15,23,42,0.08)]"
      />
    )
  }

  return (
    <div className="flex h-16 w-16 items-center justify-center rounded-[22px] bg-gradient-to-br from-emerald-500 to-teal-500 text-lg font-bold text-white shadow-[0_12px_28px_rgba(15,23,42,0.08)]">
      {initials}
    </div>
  )
}

function OverviewCard({ label, value, note }) {
  return (
    <div className={`${compactSurface} px-4 py-4`}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-600">{note}</p>
    </div>
  )
}

function MetricCard({ icon, title, value, trend, accent = 'text-emerald-700 bg-emerald-50' }) {
  return (
    <div className={`${dashboardSurface} p-5 transition-transform duration-200 hover:-translate-y-0.5`}>
      <div className="flex items-start justify-between gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${accent}`}>
          {icon}
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Overview</p>
      </div>
      <p className="mt-5 text-sm font-medium text-slate-600">{title}</p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{trend}</p>
    </div>
  )
}

function WorkspaceMetric({ label, value }) {
  return (
    <div className={`${compactSurface} px-3 py-3 text-center`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-950">{value}</p>
    </div>
  )
}

function TeamReference({ task }) {
  const teamId = task.team || task.team_id

  if (!teamId) {
    return <span>{task.team_name || 'Personal workspace'}</span>
  }

  return (
    <Link to={`/teams/${teamId}/overview`} className="font-medium text-emerald-700 transition-colors hover:text-emerald-800">
      {task.team_name || 'Team workspace'}
    </Link>
  )
}

function SectionHeader({ eyebrow, title, action }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
      </div>
      {action ? action : null}
    </div>
  )
}

function PriorityChip({ priority }) {
  const toneMap = {
    critical: 'bg-amber-100 text-amber-800',
    high: 'bg-orange-100 text-orange-700',
    medium: 'bg-slate-100 text-slate-700',
    low: 'bg-slate-100 text-slate-600',
  }

  return (
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${toneMap[priority] || toneMap.low}`}>
      {toSentenceCase(priority)}
    </span>
  )
}

function StatusChip({ status }) {
  return (
    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
      {toSentenceCase(status)}
    </span>
  )
}

function QueueIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />
    </svg>
  )
}

function AlertIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 9v4m0 4h.01M10.29 3.86 1.82 18A2 2 0 0 0 3.53 21h16.94a2 2 0 0 0 1.71-3l-8.47-14.14a2 2 0 0 0-3.42 0Z" />
    </svg>
  )
}

function CheckIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m5 12 5 5L20 7" />
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
