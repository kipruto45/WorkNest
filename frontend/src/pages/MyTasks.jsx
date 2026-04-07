import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { createTask } from '../features/tasksSlice'
import { dashboardAPI, teamsAPI, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

const initialDraft = {
  team_id: '',
  title: '',
  description: '',
  priority: 'medium',
  assigned_to: '',
}

export default function MyTasks() {
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState([])
  const [teams, setTeams] = useState([])
  const [teamMembers, setTeamMembers] = useState([])
  const [showComposer, setShowComposer] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState(initialDraft)
  const currentUser = useSelector((state) => state.auth.user)
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const loadTasks = async () => {
    const response = await dashboardAPI.getPersonalTasks()
    setTasks(unwrapResults(response))
  }

  const loadTeams = async () => {
    const response = await teamsAPI.getTeams({ page_size: 100 })
    const results = unwrapResults(response)
    setTeams(results)

    if (!draft.team_id && results.length) {
      setDraft((current) => ({
        ...current,
        team_id: results[0].id,
        assigned_to: currentUser?.id || '',
      }))
    }
  }

  useEffect(() => {
    const initialize = async () => {
      try {
        await Promise.all([loadTasks(), loadTeams()])
      } finally {
        setLoading(false)
      }
    }

    initialize()
  }, [])

  useEffect(() => {
    const loadMembers = async () => {
      if (!draft.team_id) {
        setTeamMembers([])
        return
      }

      try {
        const response = await teamsAPI.getTeamMembers(draft.team_id, { page_size: 100 })
        setTeamMembers(unwrapResults(response))
      } catch (error) {
        setTeamMembers([])
      }
    }

    loadMembers()
  }, [draft.team_id])

  const stats = useMemo(() => {
    const completed = tasks.filter((task) => task.status === 'done').length
    const inFlight = tasks.filter((task) => task.status === 'in_progress' || task.status === 'in_review').length
    const overdue = tasks.filter((task) => task.is_overdue).length

    return { completed, inFlight, overdue }
  }, [tasks])

  const handleOpenComposer = () => {
    if (!teams.length) {
      toast.info('Create or join a team before adding tasks.')
      return
    }

    setDraft({
      ...initialDraft,
      team_id: draft.team_id || teams[0].id,
      assigned_to: currentUser?.id || '',
    })
    setShowComposer(true)
  }

  const handleCreateTask = async (event) => {
    event.preventDefault()
    if (!draft.team_id || !draft.title.trim()) {
      toast.error('Choose a team and add a task title.')
      return
    }

    setSaving(true)
    try {
      const createdTask = await dispatch(
        createTask({
          team_id: draft.team_id,
          title: draft.title.trim(),
          description: draft.description.trim(),
          priority: draft.priority,
          status: 'todo',
          assigned_to: draft.assigned_to || null,
        })
      ).unwrap()

      toast.success(
        draft.assigned_to && String(draft.assigned_to) !== String(currentUser?.id)
          ? 'Task created and assigned to your teammate.'
          : 'Task created in your queue.'
      )
      setShowComposer(false)
      setDraft(initialDraft)
      await loadTasks()
      navigate(`/tasks/${createdTask.id}`)
    } catch (error) {
      toast.error(error?.message || 'Unable to create task right now.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading your tasks" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="My Tasks"
        title="Personal task queue"
        description="Everything assigned to you across teams, plus a quick way to create work for yourself or hand it directly to a teammate."
        stats={[
          { label: 'Assigned', value: tasks.length, caption: 'All active tasks' },
          { label: 'In flight', value: stats.inFlight, caption: 'Currently moving' },
          { label: 'Completed', value: stats.completed, caption: 'Already closed' },
        ]}
        spotlight={{
          eyebrow: 'Focus',
          title: 'Create personal work or route it to the right owner fast.',
          description: 'This page now doubles as a lightweight task intake surface for day-to-day execution.',
          points: [
            { label: 'Overdue', value: stats.overdue },
            { label: 'Teams available', value: teams.length },
          ],
        }}
        actions={
          <button type="button" onClick={handleOpenComposer} className="btn-primary">
            Add task
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Assigned to you" value={tasks.length} hint="Across all active teams" />
        <StatCard label="In flight" value={stats.inFlight} hint="Currently moving through execution" />
        <StatCard label="Overdue" value={stats.overdue} hint="Needs attention soonest" accent="from-lime-500 to-emerald-600" />
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          title="No tasks assigned yet"
          description="Create a task for yourself or assign one to a teammate. Anything routed to you will appear here with status and due date."
          action={
            <button type="button" onClick={handleOpenComposer} className="btn-primary">
              Add your first task
            </button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {tasks.map((task) => (
            <Link key={task.id} to={`/tasks/${task.id}`} className="feature-tile fade-in">
              <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[1.1fr,0.9fr] lg:items-center">
                <div>
                  <div className="stat-chip">{toSentenceCase(task.priority)}</div>
                  <h3 className="mt-3 text-xl font-bold text-emerald-950">{task.title}</h3>
                  <p className="mt-2 text-sm text-soft">
                    {task.team_name} • {toSentenceCase(task.status)} • Due {formatDate(task.due_date)}
                  </p>
                </div>

                <div className="grid gap-2 text-sm text-soft md:grid-cols-2 lg:min-w-[260px]">
                  <div className="metric-strip">
                    <p className="font-semibold text-emerald-900">Due window</p>
                    <p className="mt-1">{formatRelativeDate(task.due_date)}</p>
                  </div>
                  <div className="metric-strip">
                    <p className="font-semibold text-emerald-900">Latest update</p>
                    <p className="mt-1">{formatDate(task.updated_at, { month: 'short', day: 'numeric' })}</p>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showComposer ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">New task</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">Create work for yourself or your team</h3>
                <p className="mt-2 text-sm leading-7 text-slate-600">
                  Pick a team, write the task clearly, and keep it personal or assign it to another active teammate.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowComposer(false)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
              >
                <span className="text-lg leading-none">×</span>
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="mt-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Team</label>
                <select
                  value={draft.team_id}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      team_id: event.target.value,
                      assigned_to: currentUser?.id || '',
                    }))
                  }
                  className="input-field"
                >
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Task title</label>
                <input
                  value={draft.title}
                  onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                  className="input-field"
                  placeholder="Prepare launch checklist"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Description</label>
                <textarea
                  value={draft.description}
                  onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
                  className="input-field min-h-[140px]"
                  placeholder="Describe the work, expected outcome, and any key context."
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Priority</label>
                  <select
                    value={draft.priority}
                    onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value }))}
                    className="input-field"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Assign to</label>
                  <select
                    value={draft.assigned_to}
                    onChange={(event) => setDraft((current) => ({ ...current, assigned_to: event.target.value }))}
                    className="input-field"
                  >
                    <option value={currentUser?.id || ''}>Me</option>
                    <option value="">Unassigned</option>
                    {teamMembers
                      .filter((membership) => String(membership.user?.id || '') !== String(currentUser?.id || ''))
                      .map((membership) => (
                        <option key={membership.id} value={membership.user?.id || ''}>
                          {membership.user?.name || membership.user?.email || 'Team member'}
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3 text-sm text-slate-600">
                Choose <strong>Me</strong> for a personal task, leave it <strong>Unassigned</strong> for later triage, or route it directly to another teammate.
              </div>

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={() => setShowComposer(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="btn-primary">
                  {saving ? 'Creating task...' : 'Create task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
