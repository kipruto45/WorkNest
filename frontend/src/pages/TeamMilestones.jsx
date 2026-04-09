import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

const statusOptions = [
  { value: 'planned', label: 'Planned' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
]

const statusMeta = {
  planned: { label: 'Planned', badgeClass: 'bg-slate-100 text-slate-700' },
  in_progress: { label: 'In progress', badgeClass: 'bg-emerald-100 text-emerald-800' },
  completed: { label: 'Completed', badgeClass: 'bg-blue-100 text-blue-800' },
}

export default function TeamMilestones() {
  const { teamId } = useParams()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [milestones, setMilestones] = useState([])
  const [draft, setDraft] = useState({
    title: '',
    description: '',
    due_date: '',
    status: 'planned',
  })
  const [saving, setSaving] = useState(false)
  const highlightedMilestoneId = searchParams.get('milestone') || ''

  const stats = useMemo(
    () => ({
      inProgress: milestones.filter((milestone) => milestone.status === 'in_progress').length,
      completed: milestones.filter((milestone) => milestone.status === 'completed').length,
      planned: milestones.filter((milestone) => milestone.status === 'planned').length,
    }),
    [milestones]
  )

  const loadMilestones = useCallback(async () => {
    setLoading(true)
    try {
      const [teamResponse, milestonesResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        tasksAPI.getMilestones(teamId, { page_size: 50 }),
      ])
      setTeam(unwrapData(teamResponse))
      setMilestones(unwrapResults(milestonesResponse))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load milestones.')
      setTeam(null)
      setMilestones([])
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    if (teamId) {
      loadMilestones()
    }
  }, [loadMilestones, teamId])

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!draft.title.trim()) {
      toast.error('Milestone title is required.')
      return
    }
    setSaving(true)
    try {
      await tasksAPI.createMilestone(teamId, {
        title: draft.title.trim(),
        description: draft.description.trim(),
        due_date: draft.due_date || null,
        status: draft.status,
      })
      setDraft({ title: '', description: '', due_date: '', status: 'planned' })
      await loadMilestones()
      toast.success('Milestone created.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to create milestone.')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (milestone, status) => {
    try {
      await tasksAPI.updateMilestone(teamId, milestone.id, { status })
      await loadMilestones()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update milestone.')
    }
  }

  const handleDelete = async (milestone) => {
    if (!window.confirm(`Delete "${milestone.title}"?`)) return
    try {
      await tasksAPI.deleteMilestone(teamId, milestone.id)
      await loadMilestones()
      toast.success('Milestone deleted.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to delete milestone.')
    }
  }

  if (loading) {
    return <LoadingState label="Loading milestones" />
  }

  if (!teamId) {
    return <EmptyState title="No team selected" description="Pick a workspace to view and manage milestones." />
  }

  const nextMilestone = milestones
    .filter((milestone) => milestone.due_date && milestone.status !== 'completed')
    .sort((first, second) => new Date(first.due_date).getTime() - new Date(second.due_date).getTime())[0]

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Milestones</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {(team?.name || 'Team')} delivery checkpoints
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Track strategic goals, completion progress, and upcoming due dates in one planning surface.
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
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-2">
              <SummaryTile label="Total milestones" value={milestones.length} note="Across this workspace" />
              <SummaryTile label="In progress" value={stats.inProgress} note="Actively in flight" />
              <SummaryTile label="Completed" value={stats.completed} note="Delivered checkpoints" />
              <SummaryTile
                label="Next due"
                value={nextMilestone?.due_date ? formatDate(nextMilestone.due_date) : 'No date'}
                note={nextMilestone?.due_date ? formatRelativeDate(nextMilestone.due_date) : 'Set a milestone deadline'}
              />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <h2 className="text-xl font-semibold text-slate-950">Create a milestone</h2>
        <p className="mt-2 text-sm text-slate-600">Capture measurable outcomes with ownership and delivery dates.</p>
        <form onSubmit={handleCreate} className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-900 md:col-span-2">
            Title
            <input
              value={draft.title}
              onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
              className="input-field mt-2"
              placeholder="Launch release readiness"
            />
          </label>
          <label className="text-sm font-semibold text-slate-900 md:col-span-2">
            Description
            <textarea
              value={draft.description}
              onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
              className="input-field mt-2 min-h-[96px]"
              placeholder="Describe success criteria and key tasks."
            />
          </label>
          <label className="text-sm font-semibold text-slate-900">
            Due date
            <input
              type="datetime-local"
              value={draft.due_date}
              onChange={(event) => setDraft((current) => ({ ...current, due_date: event.target.value }))}
              className="input-field mt-2"
            />
          </label>
          <label className="text-sm font-semibold text-slate-900">
            Status
            <select
              value={draft.status}
              onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value }))}
              className="input-field mt-2"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Creating...' : 'Create milestone'}
            </button>
          </div>
        </form>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Milestone registry</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Delivery checkpoints and linked work</h2>
          </div>
          <p className="text-sm text-slate-500">{milestones.length} total</p>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {milestones.length === 0 ? (
          <EmptyState
            title="No milestones yet"
            description="Create the first milestone to track team-level goals and progress."
          />
        ) : (
          milestones.map((milestone) => (
            <div
              key={milestone.id}
              className={`${cardClass} p-5 transition-shadow hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)] ${
                highlightedMilestoneId === String(milestone.id) ? 'border-emerald-300 shadow-[0_16px_40px_rgba(16,185,129,0.14)]' : ''
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusMeta[milestone.status]?.badgeClass || 'bg-slate-100 text-slate-700'}`}>
                    {statusMeta[milestone.status]?.label || milestone.status}
                  </span>
                  <h3 className="mt-2 text-xl font-semibold text-emerald-950">{milestone.title}</h3>
                  <p className="mt-2 text-sm text-soft">{milestone.description || 'No description provided yet.'}</p>
                </div>
                <button type="button" onClick={() => handleDelete(milestone)} className="btn-ghost">
                  Delete
                </button>
              </div>

              <div className="mt-4">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                  <span>{milestone.progress?.completed || 0} of {milestone.progress?.total || 0} tasks complete</span>
                  <span>{milestone.progress?.percentage || 0}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-100">
                  <div
                    className="h-2 rounded-full bg-emerald-600"
                    style={{ width: `${milestone.progress?.percentage || 0}%` }}
                  />
                </div>
              </div>

              {milestone.linked_tasks?.length ? (
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Linked tasks</p>
                  <div className="mt-3 grid gap-2">
                    {milestone.linked_tasks.map((task) => (
                      <Link
                        key={task.id}
                        to={`/tasks/${task.id}`}
                        className="rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3 transition-colors hover:bg-slate-50"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold text-slate-950">{task.title}</p>
                          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                            {task.status?.replaceAll('_', ' ')}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-slate-500">{task.assignee_name || 'Unassigned'}</p>
                      </Link>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
                <span className="text-slate-500">Due {milestone.due_date ? formatDate(milestone.due_date) : 'No date set'}</span>
                <select
                  value={milestone.status}
                  onChange={(event) => handleStatusChange(milestone, event.target.value)}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"
                >
                  {statusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))
        )}
        </div>
      </section>
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}
