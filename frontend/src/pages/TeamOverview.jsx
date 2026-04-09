import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import Forbidden from './Forbidden'
import { auditLogsAPI, dashboardAPI, tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { clampPercent, formatDate, formatRelativeDate, getInitials, toSentenceCase } from '../utils/formatters'
import { canCreateTask, canManageInvitations, canManageMembers, resolveMembershipRole } from '../utils/permissions'

const dashboardSurface = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const compactSurface = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'
const subtleSurface = 'rounded-[20px] border border-slate-200 bg-white/90'
const emptyBuckets = {
  todo: [],
  in_progress: [],
  in_review: [],
  done: [],
}

const statusPalette = ['bg-emerald-600', 'bg-sky-600', 'bg-violet-600', 'bg-amber-500', 'bg-slate-500', 'bg-rose-500']
const priorityPalette = {
  low: 'bg-slate-500',
  medium: 'bg-sky-600',
  high: 'bg-amber-500',
  urgent: 'bg-rose-600',
}

export default function TeamOverview() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [accessDenied, setAccessDenied] = useState(false)
  const [fetchError, setFetchError] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)
  const [team, setTeam] = useState(null)
  const [summary, setSummary] = useState({})
  const [progress, setProgress] = useState({})
  const [workload, setWorkload] = useState([])
  const [statuses, setStatuses] = useState([])
  const [priorities, setPriorities] = useState([])
  const [calendarItems, setCalendarItems] = useState([])
  const [activityEntries, setActivityEntries] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [members, setMembers] = useState([])
  const [taskBuckets, setTaskBuckets] = useState(emptyBuckets)
  const [milestones, setMilestones] = useState([])
  const [announcementDraft, setAnnouncementDraft] = useState({ title: '', content: '' })
  const [savingAnnouncement, setSavingAnnouncement] = useState(false)
  const [pinningTeam, setPinningTeam] = useState(false)
  const [workspaceQuery, setWorkspaceQuery] = useState('')
  const deferredWorkspaceQuery = useDeferredValue(workspaceQuery.trim().toLowerCase())

  useEffect(() => {
    if (!teamId) {
      setLoading(false)
      setFetchError('No team was selected.')
      return
    }

    const loadWorkspace = async () => {
      setLoading(true)
      setAccessDenied(false)
      setFetchError('')

      try {
        const teamResponse = await teamsAPI.getTeam(teamId)
        const teamData = unwrapData(teamResponse)
        const membershipRole = teamData?.my_membership?.role || teamData?.my_role || null

        if (!membershipRole) {
          setAccessDenied(true)
          setTeam(teamData)
          return
        }

        setTeam(teamData)

        const [
          summaryResult,
          progressResult,
          workloadResult,
          statusResult,
          priorityResult,
          calendarResult,
          activityResult,
          announcementsResult,
          membersResult,
          kanbanResult,
          timelineResult,
          auditLogsResult,
          milestoneResult,
        ] = await Promise.allSettled([
          dashboardAPI.getTeamSummary(teamId),
          dashboardAPI.getTeamProgress(teamId),
          dashboardAPI.getTeamWorkload(teamId),
          dashboardAPI.getTeamStatusDistribution(teamId),
          dashboardAPI.getTeamPriorityDistribution(teamId),
          dashboardAPI.getTeamCalendar(teamId, { page_size: 40 }),
          dashboardAPI.getTeamActivity(teamId),
          teamsAPI.getAnnouncements(teamId, { page_size: 10 }),
          teamsAPI.getTeamMembers(teamId, { page_size: 50 }),
          tasksAPI.getKanban(teamId),
          teamsAPI.getTimeline(teamId, { page_size: 12 }),
          auditLogsAPI.getForTeam(teamId, { page_size: 12 }),
          tasksAPI.getMilestones(teamId, { page_size: 8 }),
        ])

        const summaryPayload = readPayload(summaryResult) || {}
        const progressPayload = readPayload(progressResult) || {}

        setSummary(summaryPayload.summary || {})
        setProgress(progressPayload.progress || {})
        setWorkload(readPayload(workloadResult)?.workload || summaryPayload.member_activity || [])
        setStatuses(readPayload(statusResult)?.status_distribution || [])
        setPriorities(readPayload(priorityResult)?.priority_distribution || [])
        setCalendarItems(readCollection(readPayload(calendarResult), ['results', 'events', 'calendar']))
        setAnnouncements(readCollection(readPayload(announcementsResult)))
        setMembers(readCollection(readPayload(membersResult)))
        setMilestones(readCollection(readPayload(milestoneResult)))

        const kanbanPayload = readPayload(kanbanResult) || {}
        setTaskBuckets({
          todo: kanbanPayload.todo?.tasks || [],
          in_progress: kanbanPayload.in_progress?.tasks || [],
          in_review: kanbanPayload.in_review?.tasks || [],
          done: kanbanPayload.done?.tasks || [],
        })

        const rawActivity = readPayload(timelineResult) || readPayload(activityResult)
        const fallbackLogs = unwrapIfFulfilled(auditLogsResult)
        setActivityEntries(normalizeActivity(rawActivity, fallbackLogs))
      } catch (error) {
        if (error.response?.status === 403) {
          setAccessDenied(true)
          return
        }

        setFetchError(error?.response?.data?.message || 'Unable to load this workspace right now.')
      } finally {
        setLoading(false)
      }
    }

    loadWorkspace()
  }, [teamId, refreshTick])

  const allTasks = useMemo(
    () => [...taskBuckets.todo, ...taskBuckets.in_progress, ...taskBuckets.in_review, ...taskBuckets.done],
    [taskBuckets]
  )

  const completionRate = clampPercent(progress.completion_rate ?? summary.completion_rate ?? 0)
  const completedTasks = progress.completed_tasks ?? summary.completed_tasks ?? taskBuckets.done.length
  const totalTasks = summary.total_tasks ?? allTasks.length
  const pendingTasks =
    summary.pending_tasks ??
    Math.max(totalTasks - completedTasks, taskBuckets.todo.length + taskBuckets.in_progress.length + taskBuckets.in_review.length)
  const overdueTasks = summary.overdue_tasks ?? allTasks.filter((task) => isTaskOverdue(task)).length

  const memberActivity = useMemo(() => {
    const sourceMembers = members.length
      ? members
      : workload.map((entry, index) => ({
          id: `workload-${index}`,
          role: null,
          user: {
            id: entry.user_id || entry.member_id || `workload-user-${index}`,
            name: entry.user_name || entry.member_name || 'Team member',
          },
        }))

    const baseMembers = sourceMembers.map((membership) => {
      const user = membership.user || membership.member || {}
      const userId = String(user.id ?? membership.user_id ?? membership.id ?? '')
      const assigned = allTasks.filter((task) => {
        const assignedId = String(task.assigned_to ?? task.assigned_to_data?.id ?? task.assigned_to_data?.user?.id ?? '')
        return assignedId && userId && assignedId === userId
      })
      const completed = assigned.filter((task) => task.status === 'done').length
      const overdue = assigned.filter((task) => isTaskOverdue(task)).length
      const dueSoon = assigned.filter((task) => isTaskDueSoon(task)).length
      const recentEntry = activityEntries.find((entry) => {
        const actorId = String(entry.actorId ?? '')
        return actorId && actorId === userId
      })

      return {
        id: membership.id || userId,
        user,
        role: membership.role,
        joinedAt: membership.joined_at,
        assignedCount: assigned.length,
        completedCount: completed,
        overdueCount: overdue,
        dueSoonCount: dueSoon,
        recentActivity: recentEntry?.subtitle || 'No recent activity recorded',
        recentActivityAt: recentEntry?.createdAt || null,
      }
    })

    const maxAssigned = Math.max(1, ...baseMembers.map((member) => member.assignedCount))

    return baseMembers
      .map((member) => ({
        ...member,
        loadWidth: `${(member.assignedCount / maxAssigned) * 100}%`,
      }))
      .sort((left, right) => right.assignedCount - left.assignedCount || right.overdueCount - left.overdueCount)
  }, [activityEntries, allTasks, members, workload])

  const activeMembers =
    memberActivity.filter((member) => member.assignedCount > 0 || member.completedCount > 0).length ||
    workload.filter((entry) => (entry.assigned_tasks ?? entry.task_count ?? entry.count ?? 0) > 0).length

  const statusItems = useMemo(() => {
    if (statuses.length) {
      return statuses.map((item) => ({
        label: toSentenceCase(item.label || item.status || 'status'),
        key: String(item.label || item.status || 'status').toLowerCase(),
        value: item.count ?? 0,
      }))
    }

    return [
      { label: 'To Do', key: 'todo', value: taskBuckets.todo.length },
      { label: 'In Progress', key: 'in_progress', value: taskBuckets.in_progress.length },
      { label: 'In Review', key: 'in_review', value: taskBuckets.in_review.length },
      { label: 'Done', key: 'done', value: taskBuckets.done.length },
      { label: 'Overdue', key: 'overdue', value: overdueTasks },
    ]
  }, [statuses, taskBuckets, overdueTasks])

  const priorityItems = useMemo(() => {
    if (priorities.length) {
      return priorities.map((item) => {
        const label = normalizePriorityLabel(item.label || item.priority || 'low')
        return {
          label,
          key: label.toLowerCase(),
          value: item.count ?? 0,
        }
      })
    }

    const counts = allTasks.reduce(
      (accumulator, task) => {
        const priorityLabel = normalizePriorityLabel(task.priority || 'low').toLowerCase()
        accumulator[priorityLabel] = (accumulator[priorityLabel] || 0) + 1
        return accumulator
      },
      { low: 0, medium: 0, high: 0, urgent: 0 }
    )

    return Object.entries(counts).map(([key, value]) => ({
      label: toSentenceCase(key),
      key,
      value,
    }))
  }, [allTasks, priorities])

  const workloadItems = useMemo(() => {
    const items = workload.length
      ? workload.map((entry) => ({
          label: entry.name || entry.user_name || entry.member_name || 'Team member',
          value: entry.assigned_tasks ?? entry.task_count ?? entry.count ?? 0,
          completed: entry.completed_tasks ?? entry.completed_count ?? null,
          overdue: entry.overdue_tasks ?? null,
          dueSoon: entry.due_soon_tasks ?? null,
        }))
      : memberActivity.map((member) => ({
          label: member.user?.name || 'Unnamed member',
          value: member.assignedCount,
          completed: member.completedCount,
          overdue: member.overdueCount,
          dueSoon: member.dueSoonCount,
        }))

    const maxValue = Math.max(1, ...items.map((item) => item.value))

    return items.slice(0, 8).map((item) => ({
      ...item,
      width: `${(item.value / maxValue) * 100}%`,
    }))
  }, [memberActivity, workload])

  const deadlineItems = useMemo(() => {
    const merged = readCollection(calendarItems).length
      ? readCollection(calendarItems).map((item) => ({
          id: item.task_id || item.id || `${item.title}-${item.due_date || item.date}`,
          title: item.title || item.task_title || 'Scheduled work',
          startAt: item.start_at || item.start_date || null,
          dueDate: item.due_date || item.date,
          priority: normalizePriorityLabel(item.priority || 'medium'),
          status: item.status || 'scheduled',
          teamName: item.team?.name || item.team_name || team?.name,
          assigneeName:
            item.assigned_to_data?.name ||
            item.assigned_to_name ||
            item.assignee?.name ||
            item.assigned_to?.name ||
            null,
          taskId: item.task_id || item.task || null,
        }))
      : allTasks
          .filter((task) => task.due_date)
          .map((task) => ({
            id: task.id,
            title: task.title,
            startAt: task.start_at || null,
            dueDate: task.due_date,
            priority: normalizePriorityLabel(task.priority || 'medium'),
            status: task.status,
            teamName: team?.name,
            assigneeName: task.assigned_to_data?.name || null,
            taskId: task.id,
          }))

    return merged.sort((left, right) => new Date(left.dueDate) - new Date(right.dueDate))
  }, [allTasks, calendarItems, team?.name])

  const filteredDeadlines = useMemo(() => {
    if (!deferredWorkspaceQuery) return deadlineItems

    return deadlineItems.filter((item) => {
      const haystack = `${item.title} ${item.assigneeName || ''} ${item.teamName || ''} ${item.priority || ''} ${item.status || ''}`
      return haystack.toLowerCase().includes(deferredWorkspaceQuery)
    })
  }, [deadlineItems, deferredWorkspaceQuery])

  const groupedDeadlines = useMemo(() => {
    const groups = {
      overdue: [],
      today: [],
      soon: [],
    }

    for (const item of filteredDeadlines) {
      const bucket = classifyDeadline(item.dueDate, item.status)
      if (bucket) {
        groups[bucket].push(item)
      }
      if (groups.overdue.length + groups.today.length + groups.soon.length >= 12) {
        break
      }
    }

    return groups
  }, [filteredDeadlines])

  const filteredActivity = useMemo(() => {
    const entries = activityEntries.slice(0, 16)
    if (!deferredWorkspaceQuery) return entries

    return entries.filter((entry) => {
      const haystack = `${entry.title} ${entry.subtitle}`
      return haystack.toLowerCase().includes(deferredWorkspaceQuery)
    })
  }, [activityEntries, deferredWorkspaceQuery])

  const memberSnapshots = useMemo(
    () =>
      memberActivity.slice(0, 8).map((member) => ({
        ...member,
        activityState: isRecentlyActive(member.recentActivityAt) ? 'Active now' : member.assignedCount > 0 ? 'Active this week' : 'No active tasks',
      })),
    [memberActivity]
  )

  const healthLabel = overdueTasks > 0 ? 'Watching deadlines' : completionRate >= 70 ? 'On track' : 'Building momentum'
  const healthCopy =
    overdueTasks > 0
      ? `${overdueTasks} task${overdueTasks === 1 ? '' : 's'} need attention across the team.`
      : `${completedTasks} completed task${completedTasks === 1 ? '' : 's'} and ${pendingTasks} still moving through delivery.`

  const milestoneSummary = useMemo(() => {
    const active = milestones.filter((milestone) => String(milestone.status || '').toLowerCase() !== 'completed')
    const nextMilestone = active.sort((left, right) => {
      const leftDate = left?.due_date ? new Date(left.due_date).getTime() : Number.POSITIVE_INFINITY
      const rightDate = right?.due_date ? new Date(right.due_date).getTime() : Number.POSITIVE_INFINITY
      return leftDate - rightDate
    })[0]
    return {
      activeCount: active.length,
      nextMilestone,
    }
  }, [milestones])

  const statusTotal = Math.max(1, statusItems.reduce((sum, item) => sum + Number(item.value || 0), 0))
  const priorityTotal = Math.max(1, priorityItems.reduce((sum, item) => sum + Number(item.value || 0), 0))

  const currentRole = resolveMembershipRole(team)
  const canCreateTasks = canCreateTask(currentRole)
  const canInviteMembers = canManageInvitations({ role: currentRole, allowManagerInvites: team?.allow_manager_invites })
  const canManageTeamMembers = canManageMembers(currentRole)
  const canPublishAnnouncements = currentRole === 'admin'

  const handleRetryLoad = () => {
    setRefreshTick((current) => current + 1)
  }

  const handleTogglePin = async () => {
    setPinningTeam(true)
    try {
      const response = await teamsAPI.togglePin(teamId)
      const payload = unwrapData(response)
      setTeam((current) => (current ? { ...current, is_pinned: Boolean(payload?.is_pinned) } : current))
      toast.success(payload?.is_pinned ? 'Team pinned to your workspace.' : 'Team unpinned.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update team pin.')
    } finally {
      setPinningTeam(false)
    }
  }

  const handleCreateAnnouncement = async (event) => {
    event.preventDefault()
    if (!announcementDraft.title.trim() || !announcementDraft.content.trim()) {
      toast.error('Add a title and message for the announcement.')
      return
    }

    setSavingAnnouncement(true)
    try {
      await teamsAPI.createAnnouncement(teamId, {
        title: announcementDraft.title.trim(),
        content: announcementDraft.content.trim(),
      })
      const refreshed = await teamsAPI.getAnnouncements(teamId, { page_size: 10 })
      setAnnouncements(unwrapResults(refreshed))
      setAnnouncementDraft({ title: '', content: '' })
      toast.success('Announcement published.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to publish announcement right now.')
    } finally {
      setSavingAnnouncement(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading team dashboard" description="Collecting workload, deadlines, and activity for this workspace." />
  }

  if (accessDenied) {
    return <Forbidden />
  }

  if (!teamId) {
    return (
      <EmptyState
        eyebrow="Team workspace"
        title="No team selected"
        description="Choose a workspace from your teams list to view dashboard insights."
        action={
          <Link to="/teams" className="btn-primary">
            Open teams
          </Link>
        }
      />
    )
  }

  if (!team && fetchError) {
    return (
      <EmptyState
        eyebrow="Team workspace"
        title="Unable to load team dashboard"
        description={fetchError}
        action={
          <div className="flex flex-wrap items-center justify-center gap-3">
            <button type="button" onClick={handleRetryLoad} className="btn-primary">
              Retry
            </button>
            <Link to="/teams" className="btn-secondary">
              Back to teams
            </Link>
          </div>
        }
      />
    )
  }

  if (!team) {
    return (
      <EmptyState
        eyebrow="Team workspace"
        title="We couldn't load this team"
        description="This workspace may have been removed or is temporarily unavailable."
        action={
          <Link to="/teams" className="btn-primary">
            Back to teams
          </Link>
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      {fetchError ? (
        <section className="rounded-[20px] border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-800">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p>{fetchError}</p>
            <button type="button" onClick={handleRetryLoad} className="rounded-xl border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.15em]">
              Retry load
            </button>
          </div>
        </section>
      ) : null}

      <section className={`${dashboardSurface} overflow-hidden`}>
        <div className="grid gap-8 px-6 py-6 lg:grid-cols-[1.15fr,0.85fr] lg:px-8 lg:py-8">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                to="/teams"
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 transition-colors hover:bg-slate-50"
              >
                Teams
              </Link>
              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                {toSentenceCase(team.my_membership?.role || team.my_role || 'member')}
              </span>
              {team.is_pinned ? (
                <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
                  Pinned workspace
                </span>
              ) : null}
            </div>

            <h1 className="mt-5 font-display text-4xl font-bold tracking-tight text-slate-950">{team.name}</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              {team.description ||
                'A focused collaboration workspace for delivery planning, ownership, and deadline visibility.'}
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <MiniStat label="Members" value={team.member_count || members.length} caption="Active collaborators" />
              <MiniStat
                label="Milestones"
                value={milestoneSummary.activeCount}
                caption={
                  milestoneSummary.nextMilestone
                    ? `Next: ${milestoneSummary.nextMilestone.title}`
                    : 'No active milestone'
                }
              />
              <MiniStat
                label="Permissions"
                value={canCreateTasks ? 'Task control' : 'Member access'}
                caption={`Role: ${toSentenceCase(currentRole || 'member')}`}
              />
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              {canCreateTasks ? (
                <Link to={`/teams/${teamId}`} className="btn-primary">
                  Create task
                </Link>
              ) : (
                <Link to={`/teams/${teamId}`} className="btn-secondary">
                  Open tasks
                </Link>
              )}
              {canInviteMembers ? (
                <Link to={`/teams/${teamId}/invitations`} className="btn-secondary">
                  Invite member
                </Link>
              ) : null}
              {canPublishAnnouncements ? (
                <Link to={`/teams/${teamId}/announcements`} className="btn-secondary">
                  Announcements
                </Link>
              ) : null}
              {canManageTeamMembers ? (
                <Link to={`/teams/${teamId}/settings`} className="btn-ghost">
                  Settings
                </Link>
              ) : (
                <Link to={`/teams/${teamId}/members`} className="btn-ghost">
                  Members
                </Link>
              )}
            </div>
          </div>

          <div className={`${compactSurface} p-5 lg:p-6`}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team health</p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-950">{healthLabel}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{healthCopy}</p>
              </div>
              <CompletionRing value={completionRate} />
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <StatStrip label="Completed" value={completedTasks} tone="bg-emerald-50 text-emerald-700" />
              <StatStrip label="Pending" value={pendingTasks} tone="bg-slate-100 text-slate-700" />
              <StatStrip label="Overdue" value={overdueTasks} tone="bg-amber-50 text-amber-700" />
              <StatStrip label="Active members" value={activeMembers} tone="bg-sky-50 text-sky-700" />
            </div>

            <div className="mt-5">
              <label htmlFor="team-dashboard-search" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Workspace search
              </label>
              <input
                id="team-dashboard-search"
                value={workspaceQuery}
                onChange={(event) => setWorkspaceQuery(event.target.value)}
                className="input-field mt-2"
                placeholder="Search tasks, deadlines, members, activity..."
              />
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleTogglePin}
                disabled={pinningTeam}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700 transition-colors hover:bg-slate-50"
              >
                {pinningTeam ? 'Updating...' : team.is_pinned ? 'Unpin team' : 'Pin team'}
              </button>
              <Link
                to={`/teams/${teamId}/activity`}
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700 transition-colors hover:bg-slate-50"
              >
                Team activity
              </Link>
              <Link
                to="/notifications"
                className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-700 transition-colors hover:bg-slate-50"
              >
                Notifications
              </Link>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <SummaryCard title="Total tasks" value={totalTasks} note="Across this team workspace" />
        <SummaryCard title="Completed tasks" value={completedTasks} note="Done and verified" accent="bg-emerald-50 text-emerald-700" />
        <SummaryCard title="Pending tasks" value={pendingTasks} note="Still moving through delivery" />
        <SummaryCard title="Overdue tasks" value={overdueTasks} note="Requires follow-up" accent="bg-amber-50 text-amber-700" />
        <SummaryCard title="Active members" value={activeMembers} note="Members carrying current load" accent="bg-sky-50 text-sky-700" />
        <SummaryCard title="Completion rate" value={`${completionRate}%`} note="Overall progress" accent="bg-slate-100 text-slate-700" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.08fr,0.92fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Team Progress"
            title="Delivery ratio and momentum"
            action={
              <Link to={`/teams/${teamId}/analytics`} className="text-sm font-semibold text-emerald-700">
                Open analytics
              </Link>
            }
          />

          <div className="mt-5 grid gap-5 lg:grid-cols-[0.68fr,1.32fr]">
            <div className={`${compactSurface} p-5`}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Overall completion</p>
              <div className="mt-4 flex justify-center">
                <CompletionRing value={completionRate} />
              </div>
              <p className="mt-4 text-center text-sm text-slate-600">
                {completedTasks} completed vs {pendingTasks} pending
              </p>
              <div className="mt-4 space-y-2 text-xs text-slate-500">
                <InlineLabel value={`${overdueTasks}`} label="Overdue tasks" />
                <InlineLabel value={`${milestoneSummary.activeCount}`} label="Active milestones" />
              </div>
            </div>

            <div className="space-y-3">
              {statusItems.map((item, index) => (
                <BarMetric key={item.label} label={item.label} value={item.value} items={statusItems} tone={statusPalette[index % statusPalette.length]} />
              ))}
            </div>
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Task Status"
            title="Current distribution"
            action={<span className="text-sm text-slate-500">{statusTotal} tasks represented</span>}
          />
          <div className="mt-5 space-y-4">
            <SegmentedBar items={statusItems} total={statusTotal} palette={statusPalette} />
            <div className="grid gap-3 sm:grid-cols-2">
              {statusItems.map((item, index) => (
                <SegmentCard
                  key={item.label}
                  label={item.label}
                  value={item.value}
                  tone={statusPalette[index % statusPalette.length]}
                  percent={Math.round((item.value / statusTotal) * 100)}
                />
              ))}
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.06fr,0.94fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Workload Distribution" title="Who is overloaded and who has room" />
          <div className="mt-5 space-y-3">
            {workloadItems.length === 0 ? (
              <SectionEmpty title="No workload data yet" description="As tasks are assigned, workload visibility appears here for balancing." />
            ) : (
              workloadItems.map((item) => (
                <WorkloadRow key={item.label} item={item} />
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Members Snapshot"
            title="Team capacity at a glance"
            action={
              <Link to={`/teams/${teamId}/members`} className="text-sm font-semibold text-emerald-700">
                View members
              </Link>
            }
          />

          <div className="mt-5 space-y-3">
            {memberSnapshots.length === 0 ? (
              <SectionEmpty title="No members yet" description="Invite teammates to start planning collaborative work." />
            ) : (
              memberSnapshots.map((member) => (
                <MemberSnapshot key={member.id} member={member} />
              ))
            )}
          </div>
        </section>
      </div>

      <section className={`${dashboardSurface} p-6 lg:p-7`}>
        <SectionHeader
          eyebrow="Upcoming Deadlines"
          title="Today, due soon, and overdue"
          action={
            <Link to={`/teams/${teamId}/calendar`} className="text-sm font-semibold text-emerald-700">
              Open calendar
            </Link>
          }
        />

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <DeadlineGroup title="Overdue" tone="amber" items={groupedDeadlines.overdue} teamId={teamId} />
          <DeadlineGroup title="Due Today" tone="sky" items={groupedDeadlines.today} teamId={teamId} />
          <DeadlineGroup title="Due Soon" tone="slate" items={groupedDeadlines.soon} teamId={teamId} />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.12fr,0.88fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Recent Team Activity"
            title="Latest collaboration events"
            action={
              <Link to={`/teams/${teamId}/activity`} className="text-sm font-semibold text-emerald-700">
                View full feed
              </Link>
            }
          />

          <div className="mt-5 space-y-3">
            {filteredActivity.length === 0 ? (
              <SectionEmpty title="No activity yet" description="Task changes, comments, and assignment events will appear in this feed." />
            ) : (
              filteredActivity.slice(0, 8).map((entry) => <ActivityRow key={entry.id} entry={entry} />)
            )}
          </div>
        </section>

        <section id="team-announcements" className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Announcements" title="Communication panel" />

          {canPublishAnnouncements ? (
            <form onSubmit={handleCreateAnnouncement} className={`${compactSurface} mt-5 space-y-3 p-4`}>
              <input
                value={announcementDraft.title}
                onChange={(event) => setAnnouncementDraft((current) => ({ ...current, title: event.target.value }))}
                className="input-field"
                placeholder="Announcement title"
              />
              <textarea
                value={announcementDraft.content}
                onChange={(event) => setAnnouncementDraft((current) => ({ ...current, content: event.target.value }))}
                className="input-field min-h-[120px]"
                placeholder="Share a milestone, risk, or team update"
              />
              <div className="flex justify-end">
                <button type="submit" disabled={savingAnnouncement} className="btn-primary">
                  {savingAnnouncement ? 'Publishing...' : 'Publish announcement'}
                </button>
              </div>
            </form>
          ) : null}

          <div className="mt-5 space-y-3">
            {announcements.length === 0 ? (
              <SectionEmpty title="No announcements yet" description="Important updates from team leads will appear here." />
            ) : (
              announcements.map((announcement) => <AnnouncementCard key={announcement.id} announcement={announcement} />)
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.08fr,0.92fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Priority Overview"
            title="Task urgency mix"
            action={<span className="text-sm text-slate-500">{priorityTotal} tasks in priorities</span>}
          />
          <div className="mt-5 space-y-4">
            <SegmentedBar items={priorityItems} total={priorityTotal} palette={Object.values(priorityPalette)} />
            <div className="grid gap-3 sm:grid-cols-2">
              {priorityItems.map((item) => (
                <SegmentCard
                  key={item.label}
                  label={item.label}
                  value={item.value}
                  tone={priorityPalette[item.key] || 'bg-slate-500'}
                  percent={Math.round((item.value / priorityTotal) * 100)}
                />
              ))}
            </div>
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Milestones"
            title="Delivery checkpoints"
            action={
              <Link to={`/teams/${teamId}/milestones`} className="text-sm font-semibold text-emerald-700">
                View all
              </Link>
            }
          />

          <div className="mt-5 space-y-3">
            {milestones.length === 0 ? (
              <SectionEmpty title="No milestones yet" description="Create milestones to keep project outcomes visible." />
            ) : (
              milestones.slice(0, 4).map((milestone) => (
                <MilestoneCard key={milestone.id} milestone={milestone} />
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function readPayload(result) {
  if (result.status !== 'fulfilled') return null
  return unwrapData(result.value)
}

function unwrapIfFulfilled(result) {
  if (result.status !== 'fulfilled') return []
  return unwrapResults(result.value)
}

function readCollection(payload, keys = ['results']) {
  if (Array.isArray(payload)) return payload

  if (payload && typeof payload === 'object') {
    for (const key of keys) {
      if (Array.isArray(payload[key])) {
        return payload[key]
      }
    }
  }

  return []
}

function normalizeActivity(activityPayload, fallbackLogs) {
  const entries = readCollection(activityPayload, ['activity', 'results', 'events'])

  if (entries.length) {
    return entries.map((entry, index) => ({
      id: entry.id || `${entry.action || entry.type || 'activity'}-${index}`,
      title: entry.title || entry.target_repr || toSentenceCase(entry.action || entry.type || 'activity'),
      subtitle:
        entry.message ||
        entry.description ||
        buildActivitySubtitle(entry.actor?.name || entry.user?.name || 'Team member', entry.action || entry.type, entry.target_type),
      createdAt: entry.created_at || entry.timestamp || new Date().toISOString(),
      actorId: entry.actor?.id || entry.user?.id || null,
      tone: activityTone(entry.action || entry.type),
    }))
  }

  return fallbackLogs.map((log, index) => ({
    id: log.id || `log-${index}`,
    title: log.target_repr || toSentenceCase(log.action || 'activity'),
    subtitle: buildActivitySubtitle(log.actor?.name || 'System', log.action, log.target_type),
    createdAt: log.created_at,
    actorId: log.actor?.id || null,
    tone: activityTone(log.action),
  }))
}

function buildActivitySubtitle(actorName, action, targetType) {
  const target = toSentenceCase(targetType || 'workspace item')
  return `${actorName} ${describeAction(action)} ${target.toLowerCase()}.`
}

function activityTone(action) {
  if (!action) return 'bg-slate-400'
  const label = String(action).toLowerCase()
  if (label.includes('delete') || label.includes('remove')) return 'bg-amber-500'
  if (label.includes('comment') || label.includes('mention')) return 'bg-sky-500'
  if (label.includes('invite') || label.includes('join')) return 'bg-violet-500'
  return 'bg-emerald-500'
}

function describeAction(action) {
  const label = String(action || '').toLowerCase()

  if (label.includes('create')) return 'created'
  if (label.includes('assign')) return 'updated ownership for'
  if (label.includes('comment')) return 'added feedback to'
  if (label.includes('invite')) return 'sent an invitation for'
  if (label.includes('join')) return 'joined'
  if (label.includes('delete') || label.includes('remove')) return 'removed'
  if (label.includes('status')) return 'updated the status of'

  return 'updated'
}

function normalizePriorityLabel(value) {
  const key = String(value || '').toLowerCase()
  if (key === 'critical') return 'Urgent'
  return toSentenceCase(key || 'low')
}

function isDateOverdue(value) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  return date < new Date()
}

function isTaskOverdue(task) {
  if (task.is_overdue) return true
  if (!task?.due_date || task?.status === 'done') return false
  return isDateOverdue(task.due_date)
}

function isTodayDate(value) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

function isTaskDueSoon(task) {
  if (!task?.due_date || task?.status === 'done') return false
  const date = new Date(task.due_date)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  const diff = date.getTime() - now.getTime()
  return diff > 0 && diff <= 1000 * 60 * 60 * 24 * 3
}

function classifyDeadline(dueDate, status) {
  const normalizedStatus = String(status || '').toLowerCase()
  if (!dueDate || normalizedStatus === 'done') return null
  if (isDateOverdue(dueDate)) return 'overdue'
  if (isTodayDate(dueDate)) return 'today'

  const date = new Date(dueDate)
  if (Number.isNaN(date.getTime())) return null
  const diff = date.getTime() - Date.now()
  if (diff > 0 && diff <= 1000 * 60 * 60 * 24 * 7) return 'soon'
  return null
}

function isRecentlyActive(value) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const diff = Date.now() - date.getTime()
  return diff <= 1000 * 60 * 60 * 24 * 2
}

function CompletionRing({ value }) {
  return (
    <div
      className="flex h-24 w-24 items-center justify-center rounded-full"
      style={{
        background: `conic-gradient(#059669 ${value * 3.6}deg, #e2e8f0 ${value * 3.6}deg 360deg)`,
      }}
    >
      <div className="flex h-[76px] w-[76px] items-center justify-center rounded-full bg-white text-center">
        <div>
          <p className="text-2xl font-bold text-slate-950">{value}%</p>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Complete</p>
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, caption }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-bold text-slate-950">{value}</p>
      <p className="mt-1 line-clamp-2 text-sm text-slate-600">{caption}</p>
    </div>
  )
}

function StatStrip({ label, value, tone }) {
  return (
    <div className={`rounded-2xl px-3 py-3 ${tone}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  )
}

function SummaryCard({ title, value, note, accent = 'bg-slate-100 text-slate-700' }) {
  return (
    <div className={`${dashboardSurface} p-5 transition-transform duration-200 hover:-translate-y-0.5`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-600">{title}</p>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${accent}`}>Overview</span>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}

function SectionHeader({ eyebrow, title, action }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
      </div>
      {action || null}
    </div>
  )
}

function InlineLabel({ value, label }) {
  return (
    <div className="flex items-center justify-between border-t border-slate-200 pt-2">
      <span className="font-semibold text-slate-700">{label}</span>
      <span>{value}</span>
    </div>
  )
}

function BarMetric({ label, value, items, tone = 'bg-emerald-600' }) {
  const maxValue = Math.max(1, ...items.map((item) => item.value))

  return (
    <div className={`${compactSurface} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-950">{label}</p>
        <p className="text-sm font-medium text-slate-500">{value}</p>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-slate-100">
        <div className={`h-2.5 rounded-full ${tone} transition-all duration-700`} style={{ width: `${(value / maxValue) * 100}%` }} />
      </div>
    </div>
  )
}

function SegmentedBar({ items, total, palette }) {
  return (
    <div className="flex h-3 overflow-hidden rounded-full bg-slate-100">
      {items.map((item, index) => (
        <div
          key={item.label}
          className={`${palette[index % palette.length]} transition-all duration-700`}
          style={{ width: `${Math.max(3, (item.value / total) * 100)}%` }}
          title={`${item.label}: ${item.value}`}
        />
      ))}
    </div>
  )
}

function SegmentCard({ label, value, percent, tone }) {
  return (
    <div className={`${subtleSurface} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-950">{label}</p>
        <span className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white ${tone}`}>{percent}%</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
    </div>
  )
}

function WorkloadRow({ item }) {
  return (
    <div className={`${compactSurface} p-4 transition-transform duration-200 hover:-translate-y-0.5`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-950">{item.label}</p>
        <p className="text-xl font-bold text-slate-950">{item.value}</p>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-slate-100">
        <div className="h-2.5 rounded-full bg-emerald-600 transition-all duration-700" style={{ width: item.width }} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
        <span className="rounded-full bg-slate-100 px-2 py-1">Completed: {item.completed ?? 0}</span>
        <span className="rounded-full bg-amber-50 px-2 py-1 text-amber-700">Overdue: {item.overdue ?? 0}</span>
        <span className="rounded-full bg-sky-50 px-2 py-1 text-sky-700">Due soon: {item.dueSoon ?? 0}</span>
      </div>
    </div>
  )
}

function MemberSnapshot({ member }) {
  return (
    <div className={`${compactSurface} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-600 text-sm font-semibold text-white">
            {getInitials(member.user?.name || 'Member')}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-950">{member.user?.name || 'Team member'}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">{toSentenceCase(member.role || 'member')}</p>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
          {member.activityState}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-slate-600">
        <span className="rounded-xl bg-slate-100 px-2 py-2 text-center">Assigned {member.assignedCount}</span>
        <span className="rounded-xl bg-emerald-50 px-2 py-2 text-center text-emerald-700">Done {member.completedCount}</span>
        <span className="rounded-xl bg-amber-50 px-2 py-2 text-center text-amber-700">Overdue {member.overdueCount}</span>
      </div>
    </div>
  )
}

function DeadlineGroup({ title, tone, items, teamId }) {
  const toneMap = {
    amber: 'border-amber-200 bg-amber-50/55 text-amber-700',
    sky: 'border-sky-200 bg-sky-50/50 text-sky-700',
    slate: 'border-slate-200 bg-slate-50/70 text-slate-700',
  }

  return (
    <div className={`${compactSurface} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${toneMap[tone]}`}>{items.length}</span>
      </div>

      <div className="mt-3 space-y-2">
        {items.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-500">No tasks in this bucket.</div>
        ) : (
          items.slice(0, 4).map((item) => (
            <Link key={item.id} to={item.taskId ? `/tasks/${item.taskId}` : `/teams/${teamId}`} className="block rounded-xl border border-slate-200 bg-white px-3 py-3 transition-colors hover:bg-slate-50">
              <p className="truncate text-sm font-semibold text-slate-900">{item.title}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                <span>{formatRelativeDate(item.dueDate)}</span>
                <span>{item.assigneeName || 'Unassigned'}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Start {item.startAt ? formatDate(item.startAt) : 'Not set'} | Due {formatDate(item.dueDate)}
              </p>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}

function ActivityRow({ entry }) {
  return (
    <div className={`${compactSurface} px-4 py-4`}>
      <div className="flex items-start gap-4">
        <div className={`mt-1 h-2.5 w-2.5 rounded-full ${entry.tone}`} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-950">{entry.title}</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">{entry.subtitle}</p>
            </div>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{formatRelativeDate(entry.createdAt)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function AnnouncementCard({ announcement }) {
  return (
    <div className={`${compactSurface} p-4`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-950">{announcement.title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{announcement.content}</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          {formatRelativeDate(announcement.created_at)}
        </span>
      </div>
      <p className="mt-3 text-xs text-slate-500">Published by {announcement.published_by?.name || 'Team admin'}</p>
    </div>
  )
}

function MilestoneCard({ milestone }) {
  const progressValue = clampPercent(milestone.progress?.percentage || 0)
  return (
    <div className={`${compactSurface} p-4`}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">{toSentenceCase(milestone.status || 'active')}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{milestone.title}</p>
      <p className="mt-1 text-sm text-slate-500">Due {milestone.due_date ? formatDate(milestone.due_date) : 'TBD'}</p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-emerald-600" style={{ width: `${progressValue}%` }} />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {milestone.progress?.completed || 0}/{milestone.progress?.total || 0} tasks complete
      </p>
    </div>
  )
}

function SectionEmpty({ title, description }) {
  return (
    <div className="rounded-[18px] border border-dashed border-slate-300 bg-slate-50/80 px-4 py-5 text-center">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </div>
  )
}
