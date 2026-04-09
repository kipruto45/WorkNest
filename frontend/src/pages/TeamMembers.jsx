import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { dashboardAPI, tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate, getInitials, toSentenceCase } from '../utils/formatters'
import { canManageMembers, resolveMembershipRole } from '../utils/permissions'

const roleOptions = ['admin', 'manager', 'member']
const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

function isTaskOverdue(task) {
  if (!task?.due_date || task.status === 'done') return false
  const dueDate = new Date(task.due_date)
  if (Number.isNaN(dueDate.getTime())) return false
  return dueDate.getTime() < Date.now()
}

export default function TeamMembers() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [members, setMembers] = useState([])
  const [workload, setWorkload] = useState([])
  const [kanban, setKanban] = useState({ todo: [], in_progress: [], in_review: [], done: [] })
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [activityFilter, setActivityFilter] = useState('all')

  const loadMembers = useCallback(async () => {
    setLoading(true)
    try {
      const [teamResponse, membersResponse, workloadResponse, kanbanResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        teamsAPI.getTeamMembers(teamId, { page_size: 100 }),
        dashboardAPI.getTeamWorkload(teamId),
        tasksAPI.getKanban(teamId),
      ])
      setTeam(unwrapData(teamResponse))
      setMembers(unwrapResults(membersResponse))
      setWorkload(unwrapData(workloadResponse)?.workload || [])

      const board = unwrapData(kanbanResponse) || {}
      setKanban({
        todo: board.todo?.tasks || [],
        in_progress: board.in_progress?.tasks || [],
        in_review: board.in_review?.tasks || [],
        done: board.done?.tasks || [],
      })
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load members.')
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  const allTasks = useMemo(
    () => [...kanban.todo, ...kanban.in_progress, ...kanban.in_review, ...kanban.done],
    [kanban]
  )

  const memberRows = useMemo(() => {
    return members.map((membership) => {
      const user = membership.user || {}
      const assignedTasks = allTasks.filter((task) => String(task.assigned_to || '') === String(user.id || ''))
      const completed = assignedTasks.filter((task) => task.status === 'done').length
      const overdue = assignedTasks.filter((task) => isTaskOverdue(task)).length
      const inProgress = assignedTasks.filter((task) => task.status === 'in_progress').length
      const workloadEntry = workload.find((entry) => String(entry.user_id || entry.member_id || '') === String(user.id || ''))
      const recentActivityAt = workloadEntry?.last_activity_at || membership.joined_at || null

      return {
        id: membership.id,
        role: membership.role,
        user,
        joinedAt: membership.joined_at,
        assignedCount: assignedTasks.length || workloadEntry?.task_count || workloadEntry?.assigned_tasks || 0,
        overdueCount: overdue || workloadEntry?.overdue_tasks || 0,
        completedCount: completed || workloadEntry?.completed_count || workloadEntry?.completed_tasks || 0,
        inProgressCount: inProgress,
        recentActivityAt,
      }
    })
  }, [allTasks, members, workload])

  const filteredRows = useMemo(() => {
    const input = query.trim().toLowerCase()
    return memberRows.filter((row) => {
      if (roleFilter !== 'all' && row.role !== roleFilter) return false
      if (activityFilter === 'active' && row.assignedCount === 0 && row.completedCount === 0) return false
      if (activityFilter === 'overloaded' && row.assignedCount < 5 && row.overdueCount < 2) return false
      if (!input) return true
      const haystack = `${row.user?.name || ''} ${row.user?.email || ''} ${row.role || ''}`
      return haystack.toLowerCase().includes(input)
    })
  }, [activityFilter, memberRows, query, roleFilter])

  const currentRole = resolveMembershipRole(team)
  const canManage = canManageMembers(currentRole)
  const overloaded = memberRows.filter((row) => row.assignedCount >= 5 || row.overdueCount >= 2).length
  const lightlyLoaded = memberRows.filter((row) => row.assignedCount <= 1).length

  const handleRoleChange = async (memberId, role) => {
    try {
      await teamsAPI.updateMemberRole(teamId, memberId, { role })
      toast.success('Member role updated.')
      await loadMembers()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update role right now.')
    }
  }

  const handleRemove = async (memberId) => {
    if (!window.confirm('Remove this member from the team?')) return
    try {
      await teamsAPI.removeMember(teamId, memberId)
      toast.success('Member removed from team.')
      await loadMembers()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to remove member right now.')
    }
  }

  if (loading || !team) {
    return <LoadingState label="Loading team members" />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Members</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} team roster</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Manage roles, scan workloads, and identify where balancing effort is needed before deadlines slip.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {canManage ? (
                <Link to={`/teams/${teamId}/invitations?compose=1`} className="btn-primary">
                  Invite member
                </Link>
              ) : null}
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Back to dashboard
              </Link>
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Members" value={members.length} note="Active collaborators" />
              <SummaryTile label="Overloaded" value={overloaded} note="High current pressure" tone="text-amber-700" />
              <SummaryTile label="Light load" value={lightlyLoaded} note="Could take more work" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm font-medium text-slate-600">
            Search
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-field mt-2"
              placeholder="Name or email"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Role
            <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} className="input-field mt-2">
              <option value="all">All roles</option>
              {roleOptions.map((role) => (
                <option key={role} value={role}>
                  {toSentenceCase(role)}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-medium text-slate-600">
            Activity
            <select value={activityFilter} onChange={(event) => setActivityFilter(event.target.value)} className="input-field mt-2">
              <option value="all">All</option>
              <option value="active">Active members</option>
              <option value="overloaded">Overloaded members</option>
            </select>
          </label>
        </div>
      </section>

      {filteredRows.length === 0 ? (
        <EmptyState
          title="No members match these filters"
          description="Try adjusting role/activity filters or search terms."
        />
      ) : (
        <section className="grid gap-4">
          {filteredRows.map((row) => (
            <article key={row.id} className={`${panelClass} p-5`}>
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex items-start gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-600 font-semibold text-white">
                    {getInitials(row.user?.name || 'Member')}
                  </div>
                  <div>
                    <p className="text-base font-semibold text-slate-950">{row.user?.name || 'Unnamed member'}</p>
                    <p className="mt-1 text-sm text-slate-600">{row.user?.email || 'No email available'}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Joined {formatDate(row.joinedAt)} | Last activity {formatRelativeDate(row.recentActivityAt)}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2 text-center">
                  <MemberPill label="Assigned" value={row.assignedCount} />
                  <MemberPill label="In progress" value={row.inProgressCount} tone="bg-sky-50 text-sky-700" />
                  <MemberPill label="Done" value={row.completedCount} tone="bg-emerald-50 text-emerald-700" />
                  <MemberPill label="Overdue" value={row.overdueCount} tone="bg-amber-50 text-amber-700" />
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  {canManage ? (
                    <>
                      <select
                        value={row.role}
                        onChange={(event) => handleRoleChange(row.id, event.target.value)}
                        className="input-field min-w-[170px]"
                      >
                        {roleOptions.map((role) => (
                          <option key={role} value={role}>
                            {toSentenceCase(role)}
                          </option>
                        ))}
                      </select>
                      <button type="button" onClick={() => handleRemove(row.id)} className="btn-secondary">
                        Remove
                      </button>
                    </>
                  ) : (
                    <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
                      {toSentenceCase(row.role)}
                    </span>
                  )}
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}

function SummaryTile({ label, value, note, tone = 'text-slate-950' }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}

function MemberPill({ label, value, tone = 'bg-slate-100 text-slate-700' }) {
  return (
    <div className={`rounded-xl px-3 py-3 ${tone}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em]">{label}</p>
      <p className="mt-1 text-lg font-bold">{value}</p>
    </div>
  )
}
