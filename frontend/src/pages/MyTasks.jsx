import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { createTask } from '../features/tasksSlice'
import { tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

const initialDraft = {
  team_id: '',
  title: '',
  description: '',
  priority: 'medium',
  assigned_to: '',
  estimated_minutes: '',
  planned_for_date: '',
  due_date: '',
  blocked_reason: '',
  recurrence_pattern: 'none',
  recurrence_interval: 1,
  source_template: '',
  save_as_template: false,
  template_name: '',
}

const builtInViews = [
  { key: 'all', label: 'My work', filters: {} },
  { key: 'my_day', label: 'My day', filters: { my_day: true, ordering: 'planned_for_date' } },
  { key: 'due_today', label: 'Due today', filters: { due_today: true, ordering: 'due_date' } },
  { key: 'blocked', label: 'Blocked', filters: { blocked: true, ordering: '-updated_at' } },
]

function readSavedViewsCache() {
  try {
    const rawValue = localStorage.getItem(CLIENT_STORAGE_KEYS.savedViews)
    if (!rawValue) return []
    const parsed = JSON.parse(rawValue)
    return Array.isArray(parsed) ? parsed : []
  } catch (_error) {
    return []
  }
}

function writeSavedViewsCache(savedViews) {
  try {
    localStorage.setItem(CLIENT_STORAGE_KEYS.savedViews, JSON.stringify(savedViews))
    return true
  } catch (_error) {
    return false
  }
}

function formatEstimate(minutes) {
  if (!minutes) return 'No estimate'
  if (minutes < 60) return `${minutes} min`
  const hours = minutes / 60
  if (Number.isInteger(hours)) return `${hours} hr`
  return `${hours.toFixed(1)} hr`
}

function toDateInputValue(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toISOString().slice(0, 10)
}

function toDateTimeInputValue(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function daysFromToday(value) {
  if (!value) return null
  const target = new Date(value)
  target.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.max(0, Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)))
}

export default function MyTasks() {
  const [loading, setLoading] = useState(true)
  const [tasks, setTasks] = useState([])
  const [teams, setTeams] = useState([])
  const [teamMembers, setTeamMembers] = useState([])
  const [templates, setTemplates] = useState([])
  const [savedViews, setSavedViews] = useState(() => readSavedViewsCache())
  const [showComposer, setShowComposer] = useState(false)
  const [saving, setSaving] = useState(false)
  const [templateCreating, setTemplateCreating] = useState(false)
  const [focusMode, setFocusMode] = useState(false)
  const [activeViewKey, setActiveViewKey] = useState('all')
  const [selectedTaskIds, setSelectedTaskIds] = useState([])
  const [bulkDraft, setBulkDraft] = useState({ action: 'status', status: 'in_progress', assigned_to: '' })
  const [draft, setDraft] = useState(initialDraft)
  const currentUser = useSelector((state) => state.auth.user)
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const activeBuiltInView = builtInViews.find((view) => view.key === activeViewKey) || builtInViews[0]
  const activeSavedView = savedViews.find((view) => `saved:${view.id}` === activeViewKey) || null
  const activeFilters = activeSavedView?.filters || activeBuiltInView.filters

  const loadTasks = async (filters = activeFilters) => {
    const response = await tasksAPI.getMyTasks(filters)
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

  const loadTemplates = async (teamId = '') => {
    const response = await tasksAPI.getTemplates(teamId ? { team: teamId, page_size: 50 } : { page_size: 50 })
    setTemplates(unwrapResults(response))
  }

  const loadSavedViews = async () => {
    try {
      const response = await tasksAPI.getSavedViews({ layout: 'list', page_size: 50 })
      const results = unwrapResults(response)
      setSavedViews(results)
      writeSavedViewsCache(results)
      return results
    } catch (_error) {
      const cachedViews = readSavedViewsCache()
      setSavedViews(cachedViews)
      return cachedViews
    }
  }

  useEffect(() => {
    const initialize = async () => {
      setLoading(true)
      try {
        await Promise.all([loadTeams(), loadSavedViews()])
      } finally {
        setLoading(false)
      }
    }

    initialize()
  }, [])

  useEffect(() => {
    if (!loading) {
      loadTasks(activeFilters).catch(() => setTasks([]))
    }
  }, [activeViewKey, loading])

  useEffect(() => {
    if (draft.team_id) {
      loadTemplates(draft.team_id).catch(() => setTemplates([]))
    }
  }, [draft.team_id])

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

  const visibleTasks = useMemo(() => {
    if (!focusMode) return tasks

    return tasks.filter((task) => {
      const plannedToday = task.planned_for_date && toDateInputValue(task.planned_for_date) === toDateInputValue(new Date())
      const urgent = task.is_overdue || task.priority === 'high' || task.priority === 'critical'
      return plannedToday || urgent
    })
  }, [focusMode, tasks])

  const stats = useMemo(() => {
    const completed = tasks.filter((task) => task.status === 'done').length
    const inFlight = tasks.filter((task) => task.status === 'in_progress' || task.status === 'in_review').length
    const overdue = tasks.filter((task) => task.is_overdue).length
    const plannedToday = tasks.filter((task) => task.planned_for_date && toDateInputValue(task.planned_for_date) === toDateInputValue(new Date())).length
    const totalEstimateMinutes = tasks.reduce((sum, task) => sum + Number(task.estimated_minutes || 0), 0)

    return { completed, inFlight, overdue, plannedToday, totalEstimateMinutes }
  }, [tasks])

  const highlightedTemplates = useMemo(() => templates.slice(0, 4), [templates])

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

  const applyTemplateToDraft = (templateId) => {
    const template = templates.find((item) => item.id === templateId)
    if (!template) return

    setDraft((current) => ({
      ...current,
      source_template: template.id,
      title: template.title || current.title,
      description: template.description || '',
      priority: template.priority || 'medium',
      estimated_minutes: template.estimated_minutes || '',
      blocked_reason: template.blocked_reason || '',
      recurrence_pattern: template.recurrence_pattern || 'none',
      recurrence_interval: template.recurrence_interval || 1,
      assigned_to: template.assigned_to || currentUser?.id || '',
      template_name: current.template_name || template.name,
    }))
  }

  const handleCreateFromTemplate = async (template) => {
    try {
      const createdTask = await tasksAPI.createFromTemplate(template.id, {})
      const task = unwrapData(createdTask)
      toast.success(`Created "${template.title}" from template.`)
      await loadTasks()
      navigate(`/tasks/${task.id}`)
    } catch (error) {
      toast.error('Unable to create a task from this template right now.')
    }
  }

  const handleSaveCurrentView = async () => {
    const defaultName = activeSavedView?.name || activeBuiltInView.label
    const name = window.prompt('Name this saved view', defaultName)
    if (!name?.trim()) return

    const derivedTeamId =
      activeSavedView?.team ||
      activeFilters.team ||
      (draft.team_id || '')

    const payload = {
      name: name.trim(),
      layout: 'list',
      filters: activeFilters,
      team_id: derivedTeamId || null,
      is_default: false,
    }

    try {
      await tasksAPI.createSavedView(payload)
      await loadSavedViews()
      toast.success('Saved view added to your workspace.')
    } catch (error) {
      const currentCachedViews = readSavedViewsCache()
      const fallbackId = `local-${Date.now()}`
      const nextView = {
        id: fallbackId,
        name: payload.name,
        layout: payload.layout,
        filters: payload.filters,
        is_default: payload.is_default,
        team: payload.team_id,
        team_name: teams.find((team) => String(team.id) === String(payload.team_id))?.name || null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      const filteredCachedViews = currentCachedViews.filter(
        (view) => !(view.name === nextView.name && String(view.team || '') === String(nextView.team || ''))
      )
      const nextCachedViews = [nextView, ...filteredCachedViews]
      writeSavedViewsCache(nextCachedViews)
      setSavedViews(nextCachedViews)
      setActiveViewKey(`saved:${fallbackId}`)
      toast.success('Saved view stored on this device. Cloud sync will retry when the workspace API is available.')
    }
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
          estimated_minutes: draft.estimated_minutes ? Number(draft.estimated_minutes) : null,
          planned_for_date: draft.planned_for_date || null,
          due_date: draft.due_date || null,
          blocked_reason: draft.blocked_reason.trim(),
          recurrence_pattern: draft.recurrence_pattern,
          recurrence_interval: Number(draft.recurrence_interval || 1),
          source_template: draft.source_template || null,
        })
      ).unwrap()

      if (draft.save_as_template && draft.template_name.trim()) {
        setTemplateCreating(true)
        await tasksAPI.createTemplate({
          team_id: draft.team_id,
          name: draft.template_name.trim(),
          title: draft.title.trim(),
          description: draft.description.trim(),
          priority: draft.priority,
          estimated_minutes: draft.estimated_minutes ? Number(draft.estimated_minutes) : null,
          planned_offset_days: daysFromToday(draft.planned_for_date),
          due_offset_days: daysFromToday(draft.due_date),
          blocked_reason: draft.blocked_reason.trim(),
          recurrence_pattern: draft.recurrence_pattern,
          recurrence_interval: Number(draft.recurrence_interval || 1),
          assigned_to: draft.assigned_to || null,
        })
        await loadTemplates(draft.team_id)
      }

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
      setTemplateCreating(false)
    }
  }

  const handleToggleSelectedTask = (taskId) => {
    setSelectedTaskIds((current) =>
      current.includes(taskId) ? current.filter((id) => id !== taskId) : [...current, taskId]
    )
  }

  const handleBulkAction = async () => {
    if (!selectedTaskIds.length) {
      return
    }

    try {
      await tasksAPI.bulkAction({
        task_ids: selectedTaskIds,
        action: bulkDraft.action,
        status: bulkDraft.action === 'status' ? bulkDraft.status : undefined,
        assigned_to: bulkDraft.action === 'assign' ? bulkDraft.assigned_to || null : undefined,
      })
      setSelectedTaskIds([])
      toast.success('Bulk action applied.')
      await loadTasks()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to apply bulk action.')
    }
  }

  if (loading) {
    return <LoadingState label="Loading your tasks" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="My Tasks"
        title="Personal execution center"
        description="Plan your day, save your favorite work views, launch recurring work, and turn repeatable execution into reusable templates."
        stats={[
          { label: 'Assigned', value: tasks.length, caption: 'All active tasks' },
          { label: 'Planned today', value: stats.plannedToday, caption: 'Scheduled for focus' },
          { label: 'Templates', value: templates.length, caption: 'Reusable work patterns' },
        ]}
        spotlight={{
          eyebrow: 'Momentum',
          title: focusMode ? 'Focus mode is on' : 'Use focus mode to narrow the noise.',
          description: focusMode
            ? 'Only the work planned for today and the tasks that need immediate attention stay visible.'
            : 'Switch on focus mode when you want to zoom in on overdue items, high-priority work, and tasks planned for today.',
          points: [
            { label: 'Overdue', value: stats.overdue },
            { label: 'Estimated load', value: formatEstimate(stats.totalEstimateMinutes) },
          ],
        }}
        actions={
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => setFocusMode((current) => !current)} className="btn-secondary">
              {focusMode ? 'Exit focus mode' : 'Focus mode'}
            </button>
            <button type="button" onClick={handleSaveCurrentView} className="btn-secondary">
              Save current view
            </button>
            <button type="button" onClick={handleOpenComposer} className="btn-primary">
              Add task
            </button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-3">
        {builtInViews.map((view) => (
          <button
            key={view.key}
            type="button"
            onClick={() => setActiveViewKey(view.key)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
              activeViewKey === view.key
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            {view.label}
          </button>
        ))}
        {savedViews.map((view) => (
          <button
            key={view.id}
            type="button"
            onClick={() => setActiveViewKey(`saved:${view.id}`)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
              activeViewKey === `saved:${view.id}`
                ? 'bg-emerald-700 text-white'
                : 'border border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
            }`}
          >
            {view.name}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Assigned to you" value={tasks.length} hint="Across all active teams" />
        <StatCard label="In flight" value={stats.inFlight} hint="Currently moving through execution" />
        <StatCard label="Planned today" value={stats.plannedToday} hint="Items in your day plan" />
        <StatCard label="Estimated load" value={formatEstimate(stats.totalEstimateMinutes)} hint="Current active workload" accent="from-lime-500 to-emerald-600" />
      </div>

      <section className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Templates</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Repeatable work patterns</h2>
          </div>
          <p className="text-sm text-slate-500">{templates.length} template{templates.length === 1 ? '' : 's'} available</p>
        </div>

        {highlightedTemplates.length ? (
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {highlightedTemplates.map((template) => (
              <div key={template.id} className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{template.name}</p>
                    <h3 className="mt-2 text-lg font-semibold text-slate-950">{template.title}</h3>
                  </div>
                  <span className="stat-chip">{toSentenceCase(template.priority)}</span>
                </div>
                <p className="mt-3 text-sm text-slate-600">
                  {formatEstimate(template.estimated_minutes)} • {template.recurrence_pattern === 'none' ? 'One-time' : `${toSentenceCase(template.recurrence_pattern)} recurring`}
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button type="button" onClick={() => handleCreateFromTemplate(template)} className="btn-primary">
                    Create from template
                  </button>
                  <button type="button" onClick={() => { setShowComposer(true); applyTemplateToDraft(template.id) }} className="btn-secondary">
                    Edit before creating
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-5 rounded-[22px] border border-dashed border-slate-200 bg-[#fcfcfb] p-5 text-sm text-slate-600">
            Save a draft as a template to build a reusable library for recurring onboarding, reviews, follow-ups, or launch rituals.
          </div>
        )}
      </section>

      {selectedTaskIds.length ? (
        <section className="card fade-in">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Bulk actions</p>
              <h3 className="mt-2 text-xl font-semibold text-slate-950">{selectedTaskIds.length} tasks selected</h3>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <select
                value={bulkDraft.action}
                onChange={(event) => setBulkDraft((current) => ({ ...current, action: event.target.value }))}
                className="input-field"
              >
                <option value="status">Change status</option>
                <option value="assign">Assign teammate</option>
                <option value="archive">Archive tasks</option>
              </select>
              {bulkDraft.action === 'status' ? (
                <select
                  value={bulkDraft.status}
                  onChange={(event) => setBulkDraft((current) => ({ ...current, status: event.target.value }))}
                  className="input-field"
                >
                  <option value="todo">To Do</option>
                  <option value="in_progress">In Progress</option>
                  <option value="in_review">In Review</option>
                  <option value="done">Done</option>
                </select>
              ) : bulkDraft.action === 'assign' ? (
                <select
                  value={bulkDraft.assigned_to}
                  onChange={(event) => setBulkDraft((current) => ({ ...current, assigned_to: event.target.value }))}
                  className="input-field"
                >
                  <option value="">Unassigned</option>
                  {teamMembers.map((membership) => (
                    <option key={membership.id} value={membership.user?.id || ''}>
                      {membership.user?.name || membership.user?.email || 'Team member'}
                    </option>
                  ))}
                </select>
              ) : (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                  Tasks will be archived.
                </div>
              )}
              <button type="button" onClick={handleBulkAction} className="btn-primary">
                Apply
              </button>
              <button type="button" onClick={() => setSelectedTaskIds([])} className="btn-secondary">
                Clear
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {visibleTasks.length === 0 ? (
        <EmptyState
          title={focusMode ? 'No focus tasks right now' : 'No tasks in this view yet'}
          description={
            focusMode
              ? 'You have no overdue, high-priority, or today-planned tasks at the moment.'
              : 'Create a task, apply a different saved view, or generate one from a template to get moving.'
          }
          action={
            <button type="button" onClick={handleOpenComposer} className="btn-primary">
              Add your first task
            </button>
          }
        />
      ) : (
        <div className="grid gap-4">
          {visibleTasks.map((task) => (
            <div key={task.id} className="feature-tile fade-in">
              <div className="mb-4 flex items-center justify-between gap-3">
                <label className="inline-flex items-center gap-2 text-sm font-medium text-slate-600">
                  <input
                    type="checkbox"
                    checked={selectedTaskIds.includes(task.id)}
                    onChange={() => handleToggleSelectedTask(task.id)}
                  />
                  Select
                </label>
                <Link to={`/tasks/${task.id}`} className="btn-ghost">
                  Open detail
                </Link>
              </div>
              <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[1.2fr,0.8fr] lg:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="stat-chip">{toSentenceCase(task.priority)}</div>
                    {task.recurrence_pattern && task.recurrence_pattern !== 'none' ? (
                      <div className="stat-chip bg-emerald-100 text-emerald-800">{toSentenceCase(task.recurrence_pattern)}</div>
                    ) : null}
                    {task.blocked_reason ? <div className="stat-chip bg-amber-100 text-amber-800">Blocked</div> : null}
                    {task.is_favorite ? <div className="stat-chip bg-amber-100 text-amber-800">Favorite</div> : null}
                  </div>
                  <h3 className="mt-3 text-xl font-bold text-emerald-950">{task.title}</h3>
                  <p className="mt-2 text-sm text-soft">
                    {task.team_name} • {toSentenceCase(task.status)} • Due {formatDate(task.due_date)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-600">
                    <span>Estimate: {formatEstimate(task.estimated_minutes)}</span>
                    <span>Planned: {task.planned_for_date ? formatDate(task.planned_for_date) : 'Not scheduled'}</span>
                    <span>Watchers: {task.watcher_count || 0}</span>
                  </div>
                  {task.labels?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {task.labels.map((label) => (
                        <span
                          key={label.id}
                          className="rounded-full px-3 py-1 text-xs font-semibold text-white"
                          style={{ backgroundColor: label.color || '#10b981' }}
                        >
                          {label.name}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {task.blocked_reason ? <p className="mt-3 text-sm font-medium text-amber-700">Blocked: {task.blocked_reason}</p> : null}
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
            </div>
          ))}
        </div>
      )}

      {showComposer ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">New task</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">Create modern task flows</h3>
                <p className="mt-2 text-sm leading-7 text-slate-600">
                  Plan work with estimates, schedule it into your day, add recurring rules, and optionally save the pattern as a reusable template.
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
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Team</label>
                  <select
                    value={draft.team_id}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        team_id: event.target.value,
                        assigned_to: currentUser?.id || '',
                        source_template: '',
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
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Start from template</label>
                  <select
                    value={draft.source_template}
                    onChange={(event) => applyTemplateToDraft(event.target.value)}
                    className="input-field"
                  >
                    <option value="">No template</option>
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </div>
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
                  className="input-field min-h-[120px]"
                  placeholder="Describe the work, expected outcome, and any key context."
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Estimate (min)</label>
                  <input
                    type="number"
                    min="1"
                    value={draft.estimated_minutes}
                    onChange={(event) => setDraft((current) => ({ ...current, estimated_minutes: event.target.value }))}
                    className="input-field"
                    placeholder="90"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">My day</label>
                  <input
                    type="date"
                    value={draft.planned_for_date}
                    onChange={(event) => setDraft((current) => ({ ...current, planned_for_date: event.target.value }))}
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Due date</label>
                  <input
                    type="datetime-local"
                    value={toDateTimeInputValue(draft.due_date)}
                    onChange={(event) => setDraft((current) => ({ ...current, due_date: event.target.value }))}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
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

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Repeats</label>
                  <select
                    value={draft.recurrence_pattern}
                    onChange={(event) => setDraft((current) => ({ ...current, recurrence_pattern: event.target.value }))}
                    className="input-field"
                  >
                    <option value="none">Does not repeat</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-semibold text-slate-900">Repeat interval</label>
                  <input
                    type="number"
                    min="1"
                    value={draft.recurrence_interval}
                    onChange={(event) => setDraft((current) => ({ ...current, recurrence_interval: event.target.value }))}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Blocked reason</label>
                <input
                  value={draft.blocked_reason}
                  onChange={(event) => setDraft((current) => ({ ...current, blocked_reason: event.target.value }))}
                  className="input-field"
                  placeholder="Waiting on design review, approval, or external dependency"
                />
              </div>

              <div className="rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-4">
                <label className="flex items-center gap-3 text-sm font-medium text-slate-800">
                  <input
                    type="checkbox"
                    checked={draft.save_as_template}
                    onChange={(event) => setDraft((current) => ({ ...current, save_as_template: event.target.checked }))}
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  Save this setup as a reusable template
                </label>
                {draft.save_as_template ? (
                  <input
                    value={draft.template_name}
                    onChange={(event) => setDraft((current) => ({ ...current, template_name: event.target.value }))}
                    className="input-field mt-3"
                    placeholder="Weekly ops review"
                  />
                ) : null}
              </div>

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={() => setShowComposer(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={saving || templateCreating} className="btn-primary">
                  {saving ? 'Creating task...' : templateCreating ? 'Saving template...' : 'Create task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
