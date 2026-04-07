import { useEffect, useMemo, useState } from 'react'
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

const emptyBuckets = {
  todo: [],
  in_progress: [],
  in_review: [],
  done: [],
}

export default function TeamOverview() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [accessDenied, setAccessDenied] = useState(false)
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
  const [announcementDraft, setAnnouncementDraft] = useState({ title: '', content: '' })
  const [savingAnnouncement, setSavingAnnouncement] = useState(false)
  const [pinningTeam, setPinningTeam] = useState(false)

  useEffect(() => {
    const loadWorkspace = async () => {
      setLoading(true)
      setAccessDenied(false)

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
        ] = await Promise.allSettled([
          dashboardAPI.getTeamSummary(teamId),
          dashboardAPI.getTeamProgress(teamId),
          dashboardAPI.getTeamWorkload(teamId),
          dashboardAPI.getTeamStatusDistribution(teamId),
          dashboardAPI.getTeamPriorityDistribution(teamId),
          dashboardAPI.getTeamCalendar(teamId, { page_size: 20 }),
          dashboardAPI.getTeamActivity(teamId),
          teamsAPI.getAnnouncements(teamId, { page_size: 10 }),
          teamsAPI.getTeamMembers(teamId, { page_size: 50 }),
          tasksAPI.getKanban(teamId),
          teamsAPI.getTimeline(teamId, { page_size: 12 }),
          auditLogsAPI.getForTeam(teamId, { page_size: 12 }),
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
        }
      } finally {
        setLoading(false)
      }
    }

    loadWorkspace()
  }, [teamId])

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
        recentActivity: recentEntry?.subtitle || 'No recent activity recorded',
      }
    })

    const maxAssigned = Math.max(1, ...baseMembers.map((member) => member.assignedCount))

    return baseMembers
      .map((member) => ({
        ...member,
        loadWidth: `${(member.assignedCount / maxAssigned) * 100}%`,
      }))
      .sort((left, right) => right.assignedCount - left.assignedCount || left.overdueCount - right.overdueCount)
  }, [activityEntries, allTasks, members, workload])

  const activeMembers =
    memberActivity.filter((member) => member.assignedCount > 0 || member.completedCount > 0).length ||
    workload.filter((entry) => (entry.assigned_tasks ?? entry.task_count ?? entry.count ?? 0) > 0).length

  const statusItems = useMemo(() => {
    if (statuses.length) {
      return statuses.map((item) => ({
        label: toSentenceCase(item.label || item.status || 'status'),
        value: item.count ?? 0,
      }))
    }

    return [
      { label: 'To Do', value: taskBuckets.todo.length },
      { label: 'In Progress', value: taskBuckets.in_progress.length },
      { label: 'In Review', value: taskBuckets.in_review.length },
      { label: 'Done', value: taskBuckets.done.length },
    ]
  }, [statuses, taskBuckets])

  const priorityItems = useMemo(() => {
    if (priorities.length) {
      return priorities.map((item) => ({
        label: toSentenceCase(item.label || item.priority || 'priority'),
        value: item.count ?? 0,
      }))
    }

    const counts = allTasks.reduce(
      (accumulator, task) => {
        const key = task.priority || 'low'
        accumulator[key] = (accumulator[key] || 0) + 1
        return accumulator
      },
      { low: 0, medium: 0, high: 0, critical: 0 }
    )

    return Object.entries(counts).map(([label, value]) => ({
      label: toSentenceCase(label),
      value,
    }))
  }, [allTasks, priorities])

  const workloadItems = useMemo(() => {
    const items = workload.length
      ? workload.map((entry) => ({
          label: entry.name || entry.user_name || entry.member_name || 'Team member',
          value: entry.assigned_tasks ?? entry.task_count ?? entry.count ?? 0,
          secondary: entry.completed_tasks ?? entry.completed_count ?? null,
        }))
      : memberActivity.map((member) => ({
          label: member.user?.name || 'Unnamed member',
          value: member.assignedCount,
          secondary: member.completedCount,
        }))

    const maxValue = Math.max(1, ...items.map((item) => item.value))

    return items.slice(0, 6).map((item) => ({
      ...item,
      width: `${(item.value / maxValue) * 100}%`,
    }))
  }, [memberActivity, workload])

  const deadlineItems = useMemo(() => {
    const merged = readCollection(calendarItems).length
      ? readCollection(calendarItems).map((item) => ({
          id: item.task_id || item.id || `${item.title}-${item.due_date || item.date}`,
          title: item.title || item.task_title || 'Scheduled work',
          dueDate: item.due_date || item.date,
          priority: item.priority || 'medium',
          status: item.status || 'scheduled',
          teamName: item.team?.name || item.team_name || team?.name,
          taskId: item.task_id || item.task || null,
        }))
      : allTasks
          .filter((task) => task.due_date)
          .map((task) => ({
            id: task.id,
            title: task.title,
            dueDate: task.due_date,
            priority: task.priority,
            status: task.status,
            teamName: team?.name,
            taskId: task.id,
          }))

    return merged
      .sort((left, right) => new Date(left.dueDate) - new Date(right.dueDate))
      .slice(0, 6)
  }, [allTasks, calendarItems, team?.name])

  const healthLabel = overdueTasks > 0 ? 'Watching deadlines' : completionRate >= 70 ? 'On track' : 'Building momentum'
  const healthCopy =
    overdueTasks > 0
      ? `${overdueTasks} task${overdueTasks === 1 ? '' : 's'} need attention across the team.`
      : `${completedTasks} completed task${completedTasks === 1 ? '' : 's'} and ${pendingTasks} still moving through delivery.`
  const currentRole = resolveMembershipRole(team)
  const canCreateTasks = canCreateTask(currentRole)
  const canInviteMembers = canManageInvitations({ role: currentRole, allowManagerInvites: team.allow_manager_invites })
  const canManageTeamMembers = canManageMembers(currentRole)
  const canPublishAnnouncements = currentRole === 'admin'

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
    return <LoadingState label="Loading team dashboard" />
  }

  if (accessDenied) {
    return <Forbidden />
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
      <section className={`${dashboardSurface} overflow-hidden`}>
        <div className="grid gap-8 px-6 py-6 lg:grid-cols-[1.08fr,0.92fr] lg:px-8 lg:py-8">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <Link to="/teams" className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 transition-colors hover:bg-slate-50">
                Teams
              </Link>
              <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                {toSentenceCase(team.my_membership?.role || team.my_role || 'member')}
              </span>
            </div>

            <h1 className="mt-5 font-display text-4xl font-bold tracking-tight text-slate-950">{team.name}</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              {team.description || 'A focused team workspace for tracking priorities, moving work forward, and keeping delivery visible for everyone involved.'}
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}`} className="inline-flex items-center rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700">
                Open board
              </Link>
              <button
                type="button"
                onClick={handleTogglePin}
                disabled={pinningTeam}
                className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50"
              >
                {pinningTeam ? 'Updating...' : team.is_pinned ? 'Unpin team' : 'Pin team'}
              </button>
              {canInviteMembers ? (
                <Link to={`/teams/${teamId}/invitations`} className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50">
                  Invite member
                </Link>
              ) : null}
              {canManageTeamMembers ? (
                <Link to={`/teams/${teamId}/settings`} className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50">
                  Workspace settings
                </Link>
              ) : (
                <Link to={`/teams/${teamId}/members`} className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-50">
                  Team members
                </Link>
              )}
            </div>
          </div>

          <div className={`${compactSurface} p-5 lg:p-6`}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team Health</p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-950">{healthLabel}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{healthCopy}</p>
              </div>
              <div
                className="flex h-24 w-24 items-center justify-center rounded-full"
                style={{
                  background: `conic-gradient(#059669 ${completionRate * 3.6}deg, #e2e8f0 ${completionRate * 3.6}deg 360deg)`,
                }}
              >
                <div className="flex h-[76px] w-[76px] items-center justify-center rounded-full bg-white text-center">
                  <div>
                    <p className="text-2xl font-bold text-slate-950">{completionRate}%</p>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Complete</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <MiniStat label="Members" value={team.member_count || members.length} caption="Active collaborators" />
              <MiniStat label="Active" value={activeMembers} caption="Members carrying work" />
              <MiniStat label="Permissions" value={canCreateTasks ? 'Can manage tasks' : 'Member access'} caption={`Role: ${toSentenceCase(currentRole || 'member')}`} />
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <SummaryCard title="Total Tasks" value={totalTasks} note="Across the team workspace" />
        <SummaryCard title="Completed" value={completedTasks} note="Tasks finished so far" accent="bg-emerald-50 text-emerald-700" />
        <SummaryCard title="Pending" value={pendingTasks} note="Still moving through delivery" />
        <SummaryCard title="Overdue" value={overdueTasks} note="Needs closer attention" accent="bg-amber-50 text-amber-700" />
        <SummaryCard title="Active Members" value={activeMembers} note="Contributors with current load" accent="bg-sky-50 text-sky-700" />
        <SummaryCard title="Completion Rate" value={`${completionRate}%`} note="Overall team delivery rate" accent="bg-slate-100 text-slate-700" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.02fr,0.98fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Announcements" title="Shared team updates" />

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
              <EmptyState
                eyebrow="Announcements"
                title="No announcements yet"
                description="Important team-wide updates will show up here to keep everyone aligned."
              />
            ) : (
              announcements.map((announcement) => (
                <div key={announcement.id} className={`${compactSurface} p-4`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-950">{announcement.title}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{announcement.content}</p>
                    </div>
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {formatRelativeDate(announcement.created_at)}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    Published by {announcement.published_by?.name || 'Team admin'}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Progress"
            title="Delivery status"
            action={<Link to={`/teams/${teamId}/analytics`} className="text-sm font-semibold text-emerald-700">Open analytics</Link>}
          />

          <div className="mt-6 grid gap-5 lg:grid-cols-[0.78fr,1.22fr]">
            <div className={`${compactSurface} p-5`}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Completed vs pending</p>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-600 transition-all duration-700" style={{ width: `${completionRate}%` }} />
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
                <span>{completedTasks} completed</span>
                <span>{pendingTasks} pending</span>
              </div>
            </div>

            <div className="space-y-4">
              {statusItems.map((item) => (
                <BarMetric key={item.label} label={item.label} value={item.value} items={statusItems} />
              ))}
            </div>
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Workload" title="Distribution across the team" />

          <div className="mt-6 space-y-4">
            {workloadItems.length === 0 ? (
              <EmptyState
                eyebrow="Workload"
                title="No workload data yet"
                description="As tasks are assigned, the team workload view will show who is carrying what."
              />
            ) : (
              workloadItems.map((item) => (
                <div key={item.label} className={`${compactSurface} p-4 transition-transform duration-200 hover:-translate-y-0.5`}>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{item.label}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                        {item.secondary !== null ? `${item.secondary} completed` : 'Current assigned load'}
                      </p>
                    </div>
                    <p className="text-xl font-bold text-slate-950">{item.value}</p>
                  </div>
                  <div className="mt-3 h-2.5 rounded-full bg-slate-100">
                    <div className="h-2.5 rounded-full bg-emerald-600 transition-all duration-700" style={{ width: item.width }} />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.18fr,0.82fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Member Activity"
            title="Team productivity and ownership"
            action={<Link to={`/teams/${teamId}/members`} className="text-sm font-semibold text-emerald-700">Manage members</Link>}
          />

          <div className="mt-5 space-y-3">
            {memberActivity.length === 0 ? (
              <EmptyState
                eyebrow="Members"
                title="No member activity yet"
                description="Invite collaborators and start assigning work to build a clear team activity view."
              />
            ) : (
              memberActivity.map((member) => (
                <div key={member.id} className={`${compactSurface} px-4 py-4 transition-colors duration-200 hover:bg-white`}>
                  <div className="grid gap-4 xl:grid-cols-[1.35fr,0.85fr,0.8fr] xl:items-center">
                    <div className="flex items-start gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 font-semibold text-white">
                        {getInitials(member.user?.name || 'Member')}
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-sm font-semibold text-slate-950">{member.user?.name || 'Unnamed member'}</p>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                            {toSentenceCase(member.role || 'member')}
                          </span>
                        </div>
                        <p className="mt-1 text-sm leading-6 text-slate-600">{member.recentActivity}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3 text-center">
                      <MemberPill label="Assigned" value={member.assignedCount} />
                      <MemberPill label="Done" value={member.completedCount} tone="bg-emerald-50 text-emerald-700" />
                      <MemberPill label="Overdue" value={member.overdueCount} tone="bg-amber-50 text-amber-700" />
                    </div>

                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        <span>Current load</span>
                        <span>{member.assignedCount} tasks</span>
                      </div>
                      <div className="mt-2 h-2.5 rounded-full bg-slate-100">
                        <div className="h-2.5 rounded-full bg-slate-900 transition-all duration-700" style={{ width: member.loadWidth }} />
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Deadlines"
            title="Upcoming due dates"
            action={<Link to="/calendar" className="text-sm font-semibold text-emerald-700">Open calendar</Link>}
          />

          <div className="mt-5 space-y-3">
            {deadlineItems.length === 0 ? (
              <EmptyState
                eyebrow="Deadlines"
                title="No deadlines scheduled"
                description="Due dates and upcoming work will appear here as the team plans tasks."
              />
            ) : (
              deadlineItems.map((item) => (
                <Link
                  key={item.id}
                  to={item.taskId ? `/tasks/${item.taskId}` : `/teams/${teamId}`}
                  className={`block rounded-[22px] border px-4 py-4 transition-all duration-200 hover:-translate-y-0.5 ${
                    isDateOverdue(item.dueDate) ? 'border-amber-200 bg-amber-50/60 hover:bg-amber-50' : 'border-slate-200 bg-[#fcfcfb] hover:bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                          {toSentenceCase(item.priority)}
                        </span>
                        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
                          {toSentenceCase(item.status)}
                        </span>
                      </div>
                      <p className="mt-3 truncate text-sm font-semibold text-slate-950">{item.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{item.teamName || team.name}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        {formatRelativeDate(item.dueDate)}
                      </p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{formatDate(item.dueDate)}</p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.04fr,0.96fr]">
        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader
            eyebrow="Recent Activity"
            title="Collaboration timeline"
            action={<Link to={`/teams/${teamId}/activity`} className="text-sm font-semibold text-emerald-700">View full feed</Link>}
          />

          <div className="mt-5 space-y-3">
            {activityEntries.length === 0 ? (
              <EmptyState
                eyebrow="Activity"
                title="No team events yet"
                description="Task updates, assignments, comments, and membership changes will build the team timeline."
              />
            ) : (
              activityEntries.slice(0, 6).map((entry) => (
                <div key={entry.id} className={`${compactSurface} px-4 py-4`}>
                  <div className="flex items-start gap-4">
                    <div className={`mt-1 h-2.5 w-2.5 rounded-full ${entry.tone}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="text-sm font-semibold text-slate-950">{entry.title}</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{entry.subtitle}</p>
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                          {formatRelativeDate(entry.createdAt)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className={`${dashboardSurface} p-6 lg:p-7`}>
          <SectionHeader eyebrow="Status & Priority" title="Task mix across the workspace" />

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <VisualizationCard title="By status" items={statusItems} tone="bg-emerald-600" />
            <VisualizationCard title="By priority" items={priorityItems} tone="bg-slate-900" />
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

function MiniStat({ label, value, caption }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-bold text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{caption}</p>
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

function BarMetric({ label, value, items }) {
  const maxValue = Math.max(1, ...items.map((item) => item.value))

  return (
    <div className={`${compactSurface} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-950">{label}</p>
        <p className="text-sm font-medium text-slate-500">{value}</p>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-slate-100">
        <div className="h-2.5 rounded-full bg-emerald-600 transition-all duration-700" style={{ width: `${(value / maxValue) * 100}%` }} />
      </div>
    </div>
  )
}

function MemberPill({ label, value, tone = 'bg-slate-100 text-slate-700' }) {
  return (
    <div className={`rounded-2xl px-3 py-3 ${tone}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  )
}

function VisualizationCard({ title, items, tone }) {
  const total = items.reduce((sum, item) => sum + item.value, 0)
  const maxValue = Math.max(1, ...items.map((item) => item.value))

  return (
    <div className={`${compactSurface} p-5`}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-sm text-slate-600">{total} tasks represented</p>
        </div>
        <div className={`h-10 w-10 rounded-2xl ${tone}`} />
      </div>

      <div className="mt-5 space-y-4">
        {items.map((item) => (
          <div key={item.label}>
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="font-medium text-slate-700">{item.label}</span>
              <span className="text-slate-500">{item.value}</span>
            </div>
            <div className="mt-2 h-2.5 rounded-full bg-slate-100">
              <div className={`h-2.5 rounded-full ${tone} transition-all duration-700`} style={{ width: `${(item.value / maxValue) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
