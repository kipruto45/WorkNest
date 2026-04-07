import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { DndContext, closestCenter, DragOverlay } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import TaskCard from '../components/TaskCard'
import { fetchKanban, updateTask, createTask } from '../features/tasksSlice'
import { fetchTeams } from '../features/teamsSlice'
import { teamsAPI, unwrapResults } from '../services/api'
import { canChangeTaskStatus, canCreateTask, resolveMembershipRole } from '../utils/permissions'
import { toSentenceCase } from '../utils/formatters'

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'in_review', title: 'In Review' },
  { id: 'done', title: 'Done' },
]

export default function TeamBoard() {
  const { teamId } = useParams()
  const dispatch = useDispatch()
  const { kanban } = useSelector((state) => state.tasks)
  const { teams } = useSelector((state) => state.teams)
  const currentUser = useSelector((state) => state.auth.user)
  const [showModal, setShowModal] = useState(false)
  const [newTask, setNewTask] = useState({
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
  })
  const [activeId, setActiveId] = useState(null)
  const [teamMembers, setTeamMembers] = useState([])

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
      } catch (error) {
        setTeamMembers([])
      }
    }

    loadTeamMembers()
  }, [teamId])

  const allTasks = useMemo(
    () => [...kanban.todo, ...kanban.in_progress, ...kanban.in_review, ...kanban.done],
    [kanban]
  )

  const getStatusForTaskId = (taskId) => {
    const matchingColumn = columns.find((column) => kanban[column.id]?.some((task) => task.id === taskId))
    return matchingColumn?.id || null
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
    const currentStatus = getStatusForTaskId(taskId)
    const task = allTasks.find((item) => item.id === taskId)

    if (!targetStatus || currentStatus === targetStatus) return
    if (
      !task ||
      !canChangeTaskStatus({
        role: currentRole,
        currentUserId: currentUser?.id,
        assignedToId: task.assigned_to,
      })
    ) {
      toast.error('You do not have permission to move this task.')
      return
    }

    try {
      await dispatch(updateTask({ id: taskId, data: { status: targetStatus } })).unwrap()
      await dispatch(fetchKanban(teamId))
      toast.success('Task status updated.')
    } catch (error) {
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
      await dispatch(
        createTask({
          ...newTask,
          team_id: teamId,
          status: 'todo',
          assigned_to: newTask.assigned_to || null,
          estimated_minutes: newTask.estimated_minutes ? Number(newTask.estimated_minutes) : null,
          planned_for_date: newTask.planned_for_date || null,
          due_date: newTask.due_date || null,
          blocked_reason: newTask.blocked_reason?.trim() || '',
          recurrence_interval: Number(newTask.recurrence_interval || 1),
        })
      ).unwrap()
      toast.success('Task created.')
      setShowModal(false)
      setNewTask({
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
      })
      dispatch(fetchKanban(teamId))
    } catch (error) {
      toast.error('Failed to create task.')
    }
  }

  const activeTask = activeId ? allTasks.find((task) => task.id === activeId) : null

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Kanban Board"
        title={currentTeam?.name || 'Team board'}
        description="Move work through the delivery pipeline with a clearer visual rhythm and calmer, greener interface."
        stats={[
          { label: 'To do', value: kanban.todo.length, caption: 'Queued work' },
          { label: 'In progress', value: kanban.in_progress.length, caption: 'Active delivery' },
          { label: 'Done', value: kanban.done.length, caption: 'Closed tasks' },
        ]}
        spotlight={{
          eyebrow: 'Flow',
          title: 'The board is the live heartbeat of the workspace.',
          description: 'The kanban surface is designed to feel clean and deliberate while still being easy to demo with drag-and-drop.',
          points: [
            { label: 'Review lane', value: kanban.in_review.length },
            { label: 'Members', value: currentTeam?.member_count || 0 },
          ],
        }}
        actions={
          <>
            <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
              Overview
            </Link>
            {canCreateTasks ? (
              <button type="button" onClick={() => setShowModal(true)} className="btn-primary">
                Add task
              </button>
            ) : null}
          </>
        }
        aside={`${currentTeam?.member_count || 0} members in workspace`}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DndContext collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          {columns.map((column) => (
            <div key={column.id} className="feature-tile flex min-h-[520px] flex-col fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Stage</p>
                  <h3 className="mt-2 text-xl font-bold text-emerald-950">{column.title}</h3>
                </div>
                <div className="stat-chip">{kanban[column.id]?.length || 0}</div>
              </div>

              <SortableContext items={kanban[column.id]?.map((task) => task.id) || []} strategy={verticalListSortingStrategy}>
                <div className="mt-5 flex-1 space-y-3 overflow-y-auto">
                  {kanban[column.id]?.map((task) => (
                    <TaskCard key={task.id} task={task} />
                  ))}
                  {kanban[column.id]?.length === 0 ? (
                    <div className="rounded-[24px] border border-dashed border-emerald-200 bg-emerald-50/60 p-5 text-sm text-soft">
                      No tasks in {toSentenceCase(column.id)} yet.
                    </div>
                  ) : null}
                </div>
              </SortableContext>
            </div>
          ))}
          <DragOverlay>{activeTask ? <TaskCard task={activeTask} isDragging /> : null}</DragOverlay>
        </DndContext>
      </div>

      {showModal && canCreateTasks ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/30 px-4 backdrop-blur-sm">
          <div className="page-shell w-full max-w-xl p-6 md:p-8">
            <h3 className="font-display text-3xl font-bold text-emerald-950">Create a new task</h3>
            <p className="mt-2 text-sm text-soft">Add a clear piece of work and place it at the start of the board.</p>

            <form onSubmit={handleCreateTask} className="mt-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Title</label>
                <input
                  value={newTask.title}
                  onChange={(event) => setNewTask({ ...newTask, title: event.target.value })}
                  className="input-field"
                  placeholder="Launch onboarding flow"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(event) => setNewTask({ ...newTask, description: event.target.value })}
                  className="input-field min-h-[140px]"
                  placeholder="What should be delivered and why?"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Priority</label>
                <select
                  value={newTask.priority}
                  onChange={(event) => setNewTask({ ...newTask, priority: event.target.value })}
                  className="input-field"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Assign to</label>
                <select
                  value={newTask.assigned_to}
                  onChange={(event) => setNewTask({ ...newTask, assigned_to: event.target.value })}
                  className="input-field"
                >
                  <option value="">Unassigned</option>
                  {teamMembers.map((membership) => (
                    <option key={membership.id} value={membership.user?.id || ''}>
                      {membership.user?.name || membership.user?.email || 'Team member'}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-soft">Managers and admins can assign new tasks to active team members.</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Estimate (min)</label>
                  <input
                    type="number"
                    min="1"
                    value={newTask.estimated_minutes}
                    onChange={(event) => setNewTask({ ...newTask, estimated_minutes: event.target.value })}
                    className="input-field"
                    placeholder="90"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Planned for</label>
                  <input
                    type="date"
                    value={newTask.planned_for_date}
                    onChange={(event) => setNewTask({ ...newTask, planned_for_date: event.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Due date</label>
                  <input
                    type="datetime-local"
                    value={newTask.due_date}
                    onChange={(event) => setNewTask({ ...newTask, due_date: event.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Repeats</label>
                  <select
                    value={newTask.recurrence_pattern}
                    onChange={(event) => setNewTask({ ...newTask, recurrence_pattern: event.target.value })}
                    className="input-field"
                  >
                    <option value="none">Does not repeat</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Repeat interval</label>
                  <input
                    type="number"
                    min="1"
                    value={newTask.recurrence_interval}
                    onChange={(event) => setNewTask({ ...newTask, recurrence_interval: event.target.value })}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Blocked reason</label>
                <input
                  value={newTask.blocked_reason}
                  onChange={(event) => setNewTask({ ...newTask, blocked_reason: event.target.value })}
                  className="input-field"
                  placeholder="Waiting on review, dependency, or approval"
                />
              </div>

              <div className="flex flex-wrap justify-end gap-3">
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
