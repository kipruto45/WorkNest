import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { DndContext, closestCenter, DragOverlay } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import TaskCard from '../components/TaskCard'
import { createTask, fetchKanban, updateTask } from '../features/tasksSlice'
import { fetchTeams } from '../features/teamsSlice'
import { teamsAPI, unwrapResults } from '../services/api'
import { canChangeTaskStatus, canCreateTask, resolveMembershipRole } from '../utils/permissions'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'
const viewModes = ['board', 'list', 'timeline']
const sortOptions = ['due_asc', 'due_desc', 'priority', 'title']

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'in_review', title: 'Review' },
  { id: 'blocked', title: 'Blocked' },
  { id: 'done', title: 'Done' },
]

function combineDateTime(dateValue, timeValue) {
  if (!dateValue && !timeValue) return null
  const datePart = dateValue || new Date().toISOString().slice(0, 10)
  const timePart = timeValue || '09:00'
  return `${datePart}T${timePart}`
}

function isOverdue(task) {
  if (task.status === 'done' || !task.due_date) return false
  const date = new Date(task.due_date)
  if (Number.isNaN(date.getTime())) return false
  return date.getTime() < Date.now()
}

function dueTime(task) {
  const date = new Date(task.due_date || 0)
  return Number.isNaN(date.getTime()) ? Number.MAX_SAFE_INTEGER : date.getTime()
}

function priorityRank(priority) {
  const value = String(priority || '').toLowerCase()
  if (value === 'critical') return 0
  if (value === 'high') return 1
  if (value === 'medium') return 2
  return 3
}

export default function TeamBoard() {
  const { teamId } = useParams()
  const dispatch = useDispatch()
  const { kanban } = useSelector((state) => state.tasks)
  const { teams } = useSelector((state) => state.teams)
  const currentUser = useSelector((state) => state.auth.user)

  const [showModal, setShowModal] = useState(false)
  const [activeId, setActiveId] = useState(null)
  const [teamMembers, setTeamMembers] = useState([])
  const [viewMode, setViewMode] = useState('board')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [assigneeFilter, setAssigneeFilter] = useState('all')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [sortBy, setSortBy] = useState('due_asc')
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    priority: 'medium',
    assigned_to: '',
    start_date: '',
    start_time: '',
    due_date: '',
    due_time: '',
    notes: '',
    blocked_reason: '',
  })

  const currentTeam = teams.find((team) => team.id === teamId)
  const currentRole = resolveMembershipRole(currentTeam)
  const canCreateTasks = canCreateTask(currentRole)

  useEffect(() => {
    dispatch(fetchTeams())
    if (teamId) {
      dispatch(fetchKanban(teamId))
    }
  }, [dispatch, teamId])

  useEffect(() => {
    const loadTeamMembers = async () => {
      if (!teamId) return
      try {
        const response = await teamsAPI.getTeamMembers(teamId, { page_size: 100 })
        setTeamMembers(unwrapResults(response))
      } catch (_error) {
        setTeamMembers([])
      }
    }
    loadTeamMembers()
  }, [teamId])

  const allTasks = useMemo(() => {
    const base = [
      ...(kanban.todo || []),
      ...(kanban.in_progress || []),
      ...(kanban.in_review || []),
      ...(kanban.done || []),
      ...(kanban.blocked || []),
    ]
    const uniqueMap = new Map(base.map((task) => [task.id, task]))
    return [...uniqueMap.values()]
  }, [kanban])

  const filteredTasks = useMemo(() => {
    const input = search.trim().toLowerCase()
    let items = [...allTasks]

    if (input) {
      items = items.filter((task) => {
        const haystack = `${task.title || ''} ${task.description || ''} ${task.priority || ''} ${task.status || ''}`
        return haystack.toLowerCase().includes(input)
      })
    }

    if (statusFilter !== 'all') {
      items = items.filter((task) => (task.status || 'todo') === statusFilter)
    }
    if (priorityFilter !== 'all') {
      items = items.filter((task) => (task.priority || 'low') === priorityFilter)
    }
    if (assigneeFilter !== 'all') {
      items = items.filter((task) => String(task.assigned_to || '') === assigneeFilter)
    }
    if (overdueOnly) {
      items = items.filter((task) => isOverdue(task))
    }

    items.sort((left, right) => {
      if (sortBy === 'due_desc') return dueTime(right) - dueTime(left)
      if (sortBy === 'priority') return priorityRank(left.priority) - priorityRank(right.priority)
      if (sortBy === 'title') return String(left.title || '').localeCompare(String(right.title || ''))
      return dueTime(left) - dueTime(right)
    })

    return items
  }, [allTasks, assigneeFilter, overdueOnly, priorityFilter, search, sortBy, statusFilter])

  const groupedByStatus = useMemo(() => {
    const groups = {
      todo: [],
      in_progress: [],
      in_review: [],
      blocked: [],
      done: [],
    }
    for (const task of filteredTasks) {
      const key = groups[task.status] ? task.status : 'todo'
      groups[key].push(task)
    }
    return groups
  }, [filteredTasks])

  const timelineGroups = useMemo(() => {
    return filteredTasks.reduce((accumulator, task) => {
      const key = task.due_date ? formatDate(task.due_date) : 'No due date'
      if (!accumulator[key]) accumulator[key] = []
      accumulator[key].push(task)
      return accumulator
    }, {})
  }, [filteredTasks])

  const statusCounts = useMemo(
    () =>
      columns.map((column) => ({
        ...column,
        count: groupedByStatus[column.id]?.length || 0,
      })),
    [groupedByStatus]
  )

  const activeTask = activeId ? allTasks.find((task) => task.id === activeId) : null

  const getStatusForTaskId = (taskId) => {
    for (const column of columns) {
      if (groupedByStatus[column.id]?.some((task) => task.id === taskId)) {
        return column.id
      }
    }
    return null
  }

  const handleDragStart = (event) => {
    setActiveId(event.active.id)
  }

  const handleDragEnd = async (event) => {
    const { active, over } = event
    setActiveId(null)
    if (!over) return

    const taskId = active.id
    const targetStatus = columns.some((column) => column.id === over.id) ? over.id : getStatusForTaskId(over.id)
    if (!targetStatus) return
    const task = allTasks.find((item) => item.id === taskId)
    if (!task) return

    if (
      !canChangeTaskStatus({
        role: currentRole,
        currentUserId: currentUser?.id,
        assignedToId: task.assigned_to,
      })
    ) {
      toast.error('You do not have permission to move this task.')
      return
    }

    const currentStatus = task.status || getStatusForTaskId(task.id)
    if (currentStatus === targetStatus) return

    try {
      await dispatch(updateTask({ id: taskId, data: { status: targetStatus } })).unwrap()
      await dispatch(fetchKanban(teamId))
      toast.success('Task status updated.')
    } catch (_error) {
      toast.error('Failed to move task.')
    }
  }

  const handleCreateTask = async (event) => {
    event.preventDefault()
    if (!canCreateTasks) {
      toast.error('You do not have permission to create tasks in this team.')
      return
    }

    try {
      const combinedDescription = [newTask.description.trim(), newTask.notes.trim() ? `Notes: ${newTask.notes.trim()}` : '']
        .filter(Boolean)
        .join('\n\n')

      await dispatch(
        createTask({
          team_id: teamId,
          title: newTask.title.trim(),
          description: combinedDescription,
          priority: newTask.priority,
          status: 'todo',
          assigned_to: newTask.assigned_to || null,
          start_at: combineDateTime(newTask.start_date, newTask.start_time),
          due_date: combineDateTime(newTask.due_date, newTask.due_time),
          blocked_reason: newTask.blocked_reason.trim(),
        })
      ).unwrap()

      toast.success('Task created.')
      setShowModal(false)
      setNewTask({
        title: '',
        description: '',
        priority: 'medium',
        assigned_to: '',
        start_date: '',
        start_time: '',
        due_date: '',
        due_time: '',
        notes: '',
        blocked_reason: '',
      })
      dispatch(fetchKanban(teamId))
    } catch (error) {
      toast.error(error?.message || 'Failed to create task.')
    }
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.12fr,0.88fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team tasks</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{currentTeam?.name || 'Team workspace'} task center</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Manage board flow, scan deadlines, and pivot between board, list, and timeline views without leaving the workspace.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
              {canCreateTasks ? (
                <button type="button" onClick={() => setShowModal(true)} className="btn-primary">
                  Create task
                </button>
              ) : null}
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Total tasks" value={allTasks.length} note="Across all statuses" />
              <SummaryTile label="In progress" value={statusCounts.find((item) => item.id === 'in_progress')?.count || 0} note="Active execution" />
              <SummaryTile label="Overdue" value={allTasks.filter((task) => isOverdue(task)).length} note="Needs intervention" tone="text-amber-700" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm font-medium text-slate-600">
              Search
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="input-field mt-2"
                placeholder="Search task title or description"
              />
            </label>
            <label className="text-sm font-medium text-slate-600">
              Sort
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)} className="input-field mt-2">
                <option value="due_asc">Due date (soonest)</option>
                <option value="due_desc">Due date (latest)</option>
                <option value="priority">Priority (urgent first)</option>
                <option value="title">Title (A-Z)</option>
              </select>
            </label>
            <label className="text-sm font-medium text-slate-600">
              Status
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="input-field mt-2">
                <option value="all">All statuses</option>
                {columns.map((column) => (
                  <option key={column.id} value={column.id}>
                    {column.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-slate-600">
              Priority
              <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} className="input-field mt-2">
                <option value="all">All priorities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Urgent</option>
              </select>
            </label>
            <label className="text-sm font-medium text-slate-600">
              Assignee
              <select value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)} className="input-field mt-2">
                <option value="all">All members</option>
                {teamMembers.map((membership) => (
                  <option key={membership.id} value={membership.user?.id || ''}>
                    {membership.user?.name || membership.user?.email || 'Team member'}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-3 rounded-[18px] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm font-medium text-slate-600">
              <input type="checkbox" checked={overdueOnly} onChange={(event) => setOverdueOnly(event.target.checked)} className="h-4 w-4" />
              Show only overdue tasks
            </label>
          </div>

          <div className={`${cardClass} p-4`}>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">View mode</p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {viewModes.map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setViewMode(mode)}
                  className={`rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] transition-colors ${
                    viewMode === mode ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
            <p className="mt-4 text-sm text-slate-600">{filteredTasks.length} tasks in current filter scope.</p>
          </div>
        </div>
      </section>

      {filteredTasks.length === 0 ? (
        <EmptyState
          title="No tasks match current filters"
          description="Adjust filters or create a new task to start filling this workspace."
          action={
            canCreateTasks ? (
              <button type="button" onClick={() => setShowModal(true)} className="btn-primary">
                Create first task
              </button>
            ) : null
          }
        />
      ) : null}

      {viewMode === 'board' && filteredTasks.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <DndContext collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
            {columns.map((column) => (
              <section key={column.id} className={`${panelClass} flex min-h-[520px] flex-col p-4`}>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-600">{column.title}</h2>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                    {groupedByStatus[column.id]?.length || 0}
                  </span>
                </div>
                <SortableContext items={groupedByStatus[column.id]?.map((task) => task.id) || []} strategy={verticalListSortingStrategy}>
                  <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
                    {groupedByStatus[column.id]?.map((task) => (
                      <TaskCard key={task.id} task={task} />
                    ))}
                  </div>
                </SortableContext>
              </section>
            ))}
            <DragOverlay>{activeTask ? <TaskCard task={activeTask} isDragging /> : null}</DragOverlay>
          </DndContext>
        </div>
      ) : null}

      {viewMode === 'list' && filteredTasks.length > 0 ? (
        <section className={`${panelClass} p-4`}>
          <div className="grid gap-2">
            <div className="grid grid-cols-[1.8fr,1fr,0.9fr,0.9fr,1fr,1fr] gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              <span>Task</span>
              <span>Assignee</span>
              <span>Status</span>
              <span>Priority</span>
              <span>Start</span>
              <span>Due</span>
            </div>
            {filteredTasks.map((task) => (
              <Link
                key={task.id}
                to={`/tasks/${task.id}`}
                className={`grid grid-cols-[1.8fr,1fr,0.9fr,0.9fr,1fr,1fr] gap-2 rounded-xl border px-3 py-3 text-sm transition-colors hover:bg-slate-50 ${
                  isOverdue(task) ? 'border-amber-200 bg-amber-50/40' : 'border-slate-200 bg-white'
                }`}
              >
                <div className="min-w-0">
                  <p className="truncate font-semibold text-slate-900">{task.title}</p>
                  <p className="mt-1 truncate text-xs text-slate-500">{task.description || 'No description'}</p>
                </div>
                <span className="truncate text-slate-600">{task.assigned_to_data?.name || 'Unassigned'}</span>
                <span className="text-slate-600">{toSentenceCase(task.status || 'todo')}</span>
                <span className="text-slate-600">{toSentenceCase(task.priority || 'medium')}</span>
                <span className="text-slate-600">{task.start_at ? formatDate(task.start_at) : 'Not set'}</span>
                <span className="text-slate-600">{task.due_date ? formatDate(task.due_date) : 'Not set'}</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {viewMode === 'timeline' && filteredTasks.length > 0 ? (
        <section className={`${panelClass} p-6`}>
          <div className="space-y-4">
            {Object.entries(timelineGroups).map(([date, items]) => (
              <article key={date} className={`${cardClass} p-4`}>
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-slate-950">{date}</h3>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                    {items.length}
                  </span>
                </div>
                <div className="mt-3 space-y-2">
                  {items.map((task) => (
                    <Link key={task.id} to={`/tasks/${task.id}`} className="block rounded-xl border border-slate-200 bg-white px-3 py-3 transition-colors hover:bg-slate-50">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{task.title}</p>
                        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                          {task.due_date ? formatRelativeDate(task.due_date) : 'No due date'}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {task.assigned_to_data?.name || 'Unassigned'} | {toSentenceCase(task.status || 'todo')} | {toSentenceCase(task.priority || 'medium')}
                      </p>
                    </Link>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {showModal && canCreateTasks ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/10 px-4 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Create task</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">Add a new team task</h3>
                <p className="mt-2 text-sm leading-7 text-slate-600">Capture the work item, owner, schedule, and context in one focused form.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
              >
                <span className="text-lg leading-none">x</span>
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="mt-6 grid gap-4 md:grid-cols-2">
              <label className="text-sm font-semibold text-slate-900 md:col-span-2">
                Title
                <input
                  value={newTask.title}
                  onChange={(event) => setNewTask((current) => ({ ...current, title: event.target.value }))}
                  className="input-field mt-2"
                  placeholder="Launch onboarding flow"
                  required
                />
              </label>
              <label className="text-sm font-semibold text-slate-900 md:col-span-2">
                Description
                <textarea
                  value={newTask.description}
                  onChange={(event) => setNewTask((current) => ({ ...current, description: event.target.value }))}
                  className="input-field mt-2 min-h-[120px]"
                  placeholder="What should be delivered and why?"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Assignee
                <select
                  value={newTask.assigned_to}
                  onChange={(event) => setNewTask((current) => ({ ...current, assigned_to: event.target.value }))}
                  className="input-field mt-2"
                >
                  <option value="">Unassigned</option>
                  {teamMembers.map((membership) => (
                    <option key={membership.id} value={membership.user?.id || ''}>
                      {membership.user?.name || membership.user?.email || 'Team member'}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Priority
                <select
                  value={newTask.priority}
                  onChange={(event) => setNewTask((current) => ({ ...current, priority: event.target.value }))}
                  className="input-field mt-2"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Urgent</option>
                </select>
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Start date
                <input
                  type="date"
                  value={newTask.start_date}
                  onChange={(event) => setNewTask((current) => ({ ...current, start_date: event.target.value }))}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Start time
                <input
                  type="time"
                  value={newTask.start_time}
                  onChange={(event) => setNewTask((current) => ({ ...current, start_time: event.target.value }))}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Due date
                <input
                  type="date"
                  value={newTask.due_date}
                  onChange={(event) => setNewTask((current) => ({ ...current, due_date: event.target.value }))}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900">
                Due time
                <input
                  type="time"
                  value={newTask.due_time}
                  onChange={(event) => setNewTask((current) => ({ ...current, due_time: event.target.value }))}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900 md:col-span-2">
                Notes
                <textarea
                  value={newTask.notes}
                  onChange={(event) => setNewTask((current) => ({ ...current, notes: event.target.value }))}
                  className="input-field mt-2 min-h-[96px]"
                  placeholder="Optional handoff or implementation notes"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900 md:col-span-2">
                Blocked reason (optional)
                <input
                  value={newTask.blocked_reason}
                  onChange={(event) => setNewTask((current) => ({ ...current, blocked_reason: event.target.value }))}
                  className="input-field mt-2"
                  placeholder="Dependency, approval, or external blocker"
                />
              </label>

              <div className="md:col-span-2 flex flex-wrap justify-end gap-3">
                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create task
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
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
