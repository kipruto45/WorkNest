import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import Forbidden from './Forbidden'
import { dashboardAPI, tasksAPI, teamsAPI, unwrapData } from '../services/api'
import { clampPercent, formatDate, toSentenceCase } from '../utils/formatters'
import { resolveMembershipRole } from '../utils/permissions'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'
const palette = ['bg-emerald-600', 'bg-sky-600', 'bg-violet-600', 'bg-amber-500', 'bg-slate-500']

export default function TeamAnalytics() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [summary, setSummary] = useState({})
  const [progress, setProgress] = useState({})
  const [workload, setWorkload] = useState([])
  const [statuses, setStatuses] = useState([])
  const [priorities, setPriorities] = useState([])
  const [milestones, setMilestones] = useState([])

  useEffect(() => {
    const loadAnalytics = async () => {
      setLoading(true)
      try {
        const [teamResponse, summaryResponse, progressResponse, workloadResponse, statusResponse, priorityResponse, milestoneResponse] = await Promise.all([
          teamsAPI.getTeam(teamId),
          dashboardAPI.getTeamSummary(teamId),
          dashboardAPI.getTeamProgress(teamId),
          dashboardAPI.getTeamWorkload(teamId),
          dashboardAPI.getTeamStatusDistribution(teamId),
          dashboardAPI.getTeamPriorityDistribution(teamId),
          tasksAPI.getMilestones(teamId, { page_size: 6 }),
        ])

        setTeam(unwrapData(teamResponse))
        setSummary(unwrapData(summaryResponse)?.summary || {})
        setProgress(unwrapData(progressResponse)?.progress || {})
        setWorkload(unwrapData(workloadResponse)?.workload || [])
        setStatuses(unwrapData(statusResponse)?.status_distribution || [])
        setPriorities(unwrapData(priorityResponse)?.priority_distribution || [])
        const milestonePayload = unwrapData(milestoneResponse)
        setMilestones(Array.isArray(milestonePayload) ? milestonePayload : milestonePayload?.results || [])
      } finally {
        setLoading(false)
      }
    }

    loadAnalytics()
  }, [teamId])

  const completionRate = clampPercent(progress.completion_rate ?? summary.completion_rate ?? 0)
  const completedTasks = progress.completed_tasks ?? summary.completed_tasks ?? 0
  const openTasks = progress.open_tasks ?? summary.pending_tasks ?? 0
  const overdueTasks = summary.overdue_tasks ?? 0

  const statusTotal = Math.max(1, statuses.reduce((sum, item) => sum + Number(item.count || 0), 0))
  const priorityTotal = Math.max(1, priorities.reduce((sum, item) => sum + Number(item.count || 0), 0))
  const activeMilestones = milestones.filter((item) => String(item.status || '').toLowerCase() !== 'completed')
  const role = resolveMembershipRole(team)
  const canViewAnalytics = role === 'admin' || role === 'manager'

  if (loading || !team) {
    return <LoadingState label="Loading team analytics" />
  }

  if (!canViewAnalytics) {
    return <Forbidden />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team analytics</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} performance lens</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Understand completion momentum, overdue pressure, workload concentration, and milestone delivery in one premium analytics surface.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
              <Link to={`/teams/${teamId}`} className="btn-secondary">
                Team tasks
              </Link>
            </div>
          </div>
          <div className={`${cardClass} p-5`}>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Overall completion</p>
            <div className="mt-4 h-3 rounded-full bg-slate-100">
              <div className="h-3 rounded-full bg-emerald-600" style={{ width: `${completionRate}%` }} />
            </div>
            <p className="mt-3 text-sm text-slate-600">
              {completedTasks} completed vs {openTasks} open tasks
            </p>
            <p className="mt-2 text-xs text-slate-500">Overdue tasks: {overdueTasks}</p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Completion rate" value={`${completionRate}%`} note="Delivery efficiency" />
        <MetricCard label="Open tasks" value={openTasks} note="Current active queue" />
        <MetricCard label="Completed" value={completedTasks} note="Shipped outcomes" />
        <MetricCard label="Overdue" value={overdueTasks} note="Schedule risk" tone="text-amber-700" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.04fr,0.96fr]">
        <section className={`${panelClass} p-6 lg:p-7`}>
          <SectionTitle title="Status distribution" subtitle="Current task mix by status" />
          {statuses.length === 0 ? (
            <div className="mt-5">
              <EmptyState title="No status data yet" description="Status analytics will appear as team tasks are tracked." />
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              <SegmentedBar items={statuses} total={statusTotal} />
              {statuses.map((item, index) => (
                <BarRow
                  key={`${item.status || item.label}-${index}`}
                  label={toSentenceCase(item.label || item.status || 'status')}
                  value={item.count || 0}
                  total={statusTotal}
                  tone={palette[index % palette.length]}
                />
              ))}
            </div>
          )}
        </section>

        <section className={`${panelClass} p-6 lg:p-7`}>
          <SectionTitle title="Priority distribution" subtitle="Urgency profile across work" />
          {priorities.length === 0 ? (
            <div className="mt-5">
              <EmptyState title="No priority data yet" description="Priority analytics will show after tasks are prioritized." />
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              <SegmentedBar items={priorities} total={priorityTotal} />
              {priorities.map((item, index) => (
                <BarRow
                  key={`${item.priority || item.label}-${index}`}
                  label={toSentenceCase(item.label || item.priority || 'priority')}
                  value={item.count || 0}
                  total={priorityTotal}
                  tone={palette[index % palette.length]}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.12fr,0.88fr]">
        <section className={`${panelClass} p-6 lg:p-7`}>
          <SectionTitle title="Workload by member" subtitle="Assignment pressure across teammates" />
          {workload.length === 0 ? (
            <div className="mt-5">
              <EmptyState title="No workload analytics yet" description="Assign tasks to team members to unlock workload insights." />
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              {workload.slice(0, 10).map((entry) => {
                const assignedCount = entry.assigned_tasks ?? entry.task_count ?? entry.count ?? 0
                const completedCount = entry.completed_tasks ?? entry.completed_count ?? 0
                const overdueCount = entry.overdue_tasks ?? 0
                return (
                  <article key={entry.user_id || entry.member_id || entry.user_name} className={`${cardClass} p-4`}>
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-slate-900">{entry.user_name || entry.member_name || 'Team member'}</p>
                      <span className="text-sm font-semibold text-slate-600">{assignedCount} assigned</span>
                    </div>
                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <Tag label="Completed" value={completedCount} tone="bg-emerald-50 text-emerald-700" />
                      <Tag label="Overdue" value={overdueCount} tone="bg-amber-50 text-amber-700" />
                      <Tag label="Open" value={Math.max(assignedCount - completedCount, 0)} tone="bg-slate-100 text-slate-700" />
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </section>

        <section className={`${panelClass} p-6 lg:p-7`}>
          <SectionTitle title="Milestone performance" subtitle="Checkpoint delivery status" />
          {milestones.length === 0 ? (
            <div className="mt-5">
              <EmptyState title="No milestones yet" description="Create milestones to track project-level outcomes." />
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              {milestones.slice(0, 5).map((milestone) => (
                <article key={milestone.id} className={`${cardClass} p-4`}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-900">{milestone.title}</p>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                      {toSentenceCase(milestone.status || 'planned')}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">Due {milestone.due_date ? formatDate(milestone.due_date) : 'Not set'}</p>
                  <div className="mt-3 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-emerald-600" style={{ width: `${milestone.progress?.percentage || 0}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    {milestone.progress?.completed || 0}/{milestone.progress?.total || 0} tasks complete
                  </p>
                </article>
              ))}
              <div className="pt-2">
                <Link to={`/teams/${teamId}/milestones`} className="text-sm font-semibold text-emerald-700">
                  Open milestone board
                </Link>
              </div>
            </div>
          )}
          <p className="mt-4 text-xs text-slate-500">Active milestones: {activeMilestones.length}</p>
        </section>
      </div>
    </div>
  )
}

function SectionTitle({ title, subtitle }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">{title}</p>
      <p className="mt-2 text-sm text-slate-600">{subtitle}</p>
    </div>
  )
}

function MetricCard({ label, value, note, tone = 'text-slate-950' }) {
  return (
    <article className={`${panelClass} p-5`}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </article>
  )
}

function SegmentedBar({ items, total }) {
  return (
    <div className="flex h-3 overflow-hidden rounded-full bg-slate-100">
      {items.map((item, index) => (
        <div
          key={`${item.status || item.priority || index}`}
          className={`${palette[index % palette.length]}`}
          style={{ width: `${Math.max(4, ((item.count || 0) / total) * 100)}%` }}
        />
      ))}
    </div>
  )
}

function BarRow({ label, value, total, tone }) {
  return (
    <div className={`${cardClass} p-4`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <span className="text-sm text-slate-600">{value}</span>
      </div>
      <div className="mt-3 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${Math.max(2, (value / Math.max(total, 1)) * 100)}%` }} />
      </div>
    </div>
  )
}

function Tag({ label, value, tone }) {
  return (
    <span className={`rounded-lg px-2 py-2 text-center ${tone}`}>
      <strong>{value}</strong> {label}
    </span>
  )
}
