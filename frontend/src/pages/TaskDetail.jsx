import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { attachmentsAPI, commentsAPI, tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { deleteTask, updateTask } from '../features/tasksSlice'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'
import { TASK_FIELD_KEYS } from '../utils/clientConfig.js'
import {
  canAssignTask,
  canChangeTaskStatus,
  canDeleteComment,
  canDeleteTask,
  canManageTask,
  resolveMembershipRole,
} from '../utils/permissions'

const allowedAttachmentExtensions = ['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip']
const maxAttachmentSizeBytes = 10 * 1024 * 1024
const commentReactionOptions = ['👍', '❤️', '🎉', '👀', '🔥']
const labelPalette = ['#10b981', '#0f766e', '#2563eb', '#7c3aed', '#f59e0b', '#ef4444']
const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const compactSurface = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function TaskDetail() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const currentUser = useSelector((state) => state.auth.user)
  const [task, setTask] = useState(null)
  const [comments, setComments] = useState([])
  const [attachments, setAttachments] = useState([])
  const [team, setTeam] = useState(null)
  const [teamMembers, setTeamMembers] = useState([])
  const [teamLabels, setTeamLabels] = useState([])
  const [timeline, setTimeline] = useState([])
  const [timeEntries, setTimeEntries] = useState([])
  const [guestAccess, setGuestAccess] = useState([])
  const [guestEmail, setGuestEmail] = useState('')
  const [guestPermission, setGuestPermission] = useState('view')
  const [dependencySearch, setDependencySearch] = useState('')
  const [dependencyResults, setDependencyResults] = useState([])
  const [dependencyType, setDependencyType] = useState('blocks')
  const [dependencyLoading, setDependencyLoading] = useState(false)
  const [timeEntryNote, setTimeEntryNote] = useState('')
  const [manualStart, setManualStart] = useState('')
  const [manualEnd, setManualEnd] = useState('')
  const [timeEntryBusy, setTimeEntryBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [commentValue, setCommentValue] = useState('')
  const [attachmentFile, setAttachmentFile] = useState(null)
  const [checklistDraft, setChecklistDraft] = useState('')
  const [labelDraft, setLabelDraft] = useState({ name: '', color: labelPalette[0] })
  const [submittingComment, setSubmittingComment] = useState(false)
  const [uploadingAttachment, setUploadingAttachment] = useState(false)
  const [savingAssignment, setSavingAssignment] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)
  const [savingMetaAction, setSavingMetaAction] = useState('')
  const [selectedAssigneeId, setSelectedAssigneeId] = useState('')
  const [statusDraft, setStatusDraft] = useState('todo')
  const [attachmentActionKey, setAttachmentActionKey] = useState('')
  const [historyComment, setHistoryComment] = useState(null)
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm()

  const loadTaskData = useCallback(async () => {
    setLoading(true)
    try {
      const taskResponse = await tasksAPI.getTask(taskId)
      const taskData = unwrapData(taskResponse)
      if (!taskData) {
        navigate('/tasks')
        return
      }

      const [
        commentsResponse,
        attachmentsResponse,
        teamResponse,
        membersResponse,
        labelsResponse,
        timelineResponse,
        timeEntryResponse,
        guestAccessResponse,
      ] = await Promise.all([
        commentsAPI.getComments(taskId, { page_size: 100 }),
        attachmentsAPI.getForTask(taskId),
        teamsAPI.getTeam(taskData.team).catch(() => null),
        teamsAPI.getTeamMembers(taskData.team, { page_size: 100 }).catch(() => null),
        tasksAPI.getLabels({ team: taskData.team, page_size: 100 }).catch(() => null),
        tasksAPI.getTimeline(taskId, { page_size: 20 }).catch(() => null),
        tasksAPI.getTimeEntries(taskId, { page_size: 20 }).catch(() => null),
        tasksAPI.getGuestAccess(taskId).catch(() => null),
      ])

      setTask(taskData)
      setComments(unwrapResults(commentsResponse))
      setAttachments(unwrapResults(attachmentsResponse))
      setTeam(teamResponse ? unwrapData(teamResponse) : null)
      setTeamMembers(membersResponse ? unwrapResults(membersResponse) : [])
      setTeamLabels(labelsResponse ? unwrapResults(labelsResponse) : [])
      setTimeline(timelineResponse ? unwrapResults(timelineResponse) : [])
      setTimeEntries(timeEntryResponse ? unwrapResults(timeEntryResponse) : [])
      setGuestAccess(guestAccessResponse ? unwrapResults(guestAccessResponse) : [])
      setSelectedAssigneeId(taskData.assigned_to || '')
      setStatusDraft(taskData.status)
      reset({
        title: taskData.title,
        description: taskData.description || '',
        priority: taskData.priority,
        [TASK_FIELD_KEYS.startAt]: taskData[TASK_FIELD_KEYS.startAt] ? taskData[TASK_FIELD_KEYS.startAt].slice(0, 16) : '',
        [TASK_FIELD_KEYS.dueAt]: taskData[TASK_FIELD_KEYS.dueAt] ? taskData[TASK_FIELD_KEYS.dueAt].slice(0, 16) : '',
        status: taskData.status,
      })
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Failed to load task.')
      navigate('/tasks')
    } finally {
      setLoading(false)
    }
  }, [navigate, reset, taskId])

  useEffect(() => {
    loadTaskData()
  }, [loadTaskData])

  useEffect(() => {
    if (!dependencySearch.trim() || !task?.team) {
      setDependencyResults([])
      return
    }
    let cancelled = false
    const timer = window.setTimeout(async () => {
      setDependencyLoading(true)
      try {
        const response = await tasksAPI.getTasks({ team: task.team, search: dependencySearch.trim(), page_size: 6 })
        if (!cancelled) {
          setDependencyResults(unwrapResults(response).filter((item) => item.id !== taskId))
        }
      } catch (_error) {
        if (!cancelled) {
          setDependencyResults([])
        }
      } finally {
        if (!cancelled) {
          setDependencyLoading(false)
        }
      }
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [dependencySearch, task?.team, taskId])

  const activeTimeEntry = timeEntries.find((entry) => !entry.end_time)

  const handleStartTimer = async () => {
    if (!taskId) return
    setTimeEntryBusy(true)
    try {
      await tasksAPI.startTimeEntry(taskId)
      await loadTaskData()
      toast.success('Timer started.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to start the timer.')
    } finally {
      setTimeEntryBusy(false)
    }
  }

  const handleStopTimer = async () => {
    if (!activeTimeEntry) return
    setTimeEntryBusy(true)
    try {
      await tasksAPI.stopTimeEntry(activeTimeEntry.id)
      await loadTaskData()
      toast.success('Timer stopped.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to stop the timer.')
    } finally {
      setTimeEntryBusy(false)
    }
  }

  const handleManualEntry = async (event) => {
    event.preventDefault()
    if (!manualStart || !manualEnd) {
      toast.error('Start and end time are required for manual entries.')
      return
    }
    setTimeEntryBusy(true)
    try {
      await tasksAPI.createTimeEntry(taskId, {
        start_time: manualStart,
        end_time: manualEnd,
        notes: timeEntryNote,
      })
      setTimeEntryNote('')
      setManualStart('')
      setManualEnd('')
      await loadTaskData()
      toast.success('Time entry saved.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to save time entry.')
    } finally {
      setTimeEntryBusy(false)
    }
  }

  const handleAddDependency = async (targetId) => {
    try {
      await tasksAPI.createDependency(taskId, { to_task_id: targetId, dependency_type: dependencyType })
      setDependencySearch('')
      setDependencyResults([])
      await loadTaskData()
      toast.success('Dependency created.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to add dependency.')
    }
  }

  const handleRemoveDependency = async (dependencyId) => {
    try {
      await tasksAPI.deleteDependency(dependencyId)
      await loadTaskData()
      toast.success('Dependency removed.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to remove dependency.')
    }
  }

  const handleGuestAccessCreate = async (event) => {
    event.preventDefault()
    if (!guestEmail.trim()) return
    try {
      await tasksAPI.createGuestAccess(taskId, { email: guestEmail.trim(), permission: guestPermission })
      setGuestEmail('')
      setGuestPermission('view')
      await loadTaskData()
      toast.success('Guest access granted.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to grant guest access.')
    }
  }

  const handleGuestAccessRevoke = async (entryId) => {
    try {
      await tasksAPI.revokeGuestAccess(entryId)
      await loadTaskData()
      toast.success('Guest access revoked.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to revoke access.')
    }
  }

  const handleUpdate = async (data) => {
    try {
      await dispatch(
        updateTask({
          id: taskId,
          data: {
            title: data.title,
            description: data.description,
            priority: data.priority,
            [TASK_FIELD_KEYS.startAt]: data[TASK_FIELD_KEYS.startAt] || null,
            [TASK_FIELD_KEYS.dueAt]: data[TASK_FIELD_KEYS.dueAt] || null,
            status: data.status,
          },
        })
      ).unwrap()
      toast.success('Task updated.')
      setIsEditing(false)
      await loadTaskData()
    } catch (error) {
      toast.error(error?.message || 'Failed to update task.')
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return
    }

    try {
      await dispatch(deleteTask(taskId)).unwrap()
      toast.success('Task deleted.')
      navigate('/tasks')
    } catch (error) {
      toast.error('Failed to delete task.')
    }
  }

  const postComment = async (content, parentId = null) => {
    if (!content.trim()) {
      return
    }

    setSubmittingComment(true)
    try {
      if (parentId) {
        await commentsAPI.replyToComment(parentId, { content })
      } else {
        await commentsAPI.createComment(taskId, { content })
        setCommentValue('')
      }
      await loadTaskData()
      toast.success(parentId ? 'Reply added.' : 'Comment added.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Failed to save comment.')
    } finally {
      setSubmittingComment(false)
    }
  }

  const handleCommentSubmit = async (event) => {
    event.preventDefault()
    await postComment(commentValue)
  }

  const handleCommentUpdate = async (commentId, content) => {
    try {
      await commentsAPI.updateComment(commentId, { content })
      await loadTaskData()
      toast.success('Comment updated.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Failed to update comment.')
    }
  }

  const handleCommentDelete = async (commentId) => {
    if (!window.confirm('Delete this comment?')) {
      return
    }

    try {
      await commentsAPI.deleteComment(commentId)
      await loadTaskData()
      toast.success('Comment deleted.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Failed to delete comment.')
    }
  }

  const handleCommentHistory = async (comment) => {
    setHistoryComment(comment)
    setHistoryLoading(true)
    try {
      const response = await commentsAPI.getHistory(comment.id, { page_size: 20 })
      setHistoryItems(unwrapResults(response))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load comment history.')
      setHistoryItems([])
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleCommentReactionToggle = async (commentId, emoji) => {
    try {
      await commentsAPI.toggleReaction(commentId, { emoji })
      await loadTaskData()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update reaction.')
    }
  }

  const handleAttachmentUpload = async (event) => {
    event.preventDefault()
    if (!attachmentFile) {
      return
    }

    const extension = attachmentFile.name.split('.').pop()?.toLowerCase() || ''
    if (!allowedAttachmentExtensions.includes(extension)) {
      toast.error(`Unsupported file type. Allowed: ${allowedAttachmentExtensions.join(', ')}`)
      return
    }

    if (attachmentFile.size > maxAttachmentSizeBytes) {
      toast.error('File size exceeds the 10 MB limit.')
      return
    }

    const formData = new FormData()
    formData.append('file', attachmentFile)

    setUploadingAttachment(true)
    try {
      await attachmentsAPI.uploadForTask(taskId, formData)
      setAttachmentFile(null)
      event.target.reset()
      await loadTaskData()
      toast.success('Attachment uploaded.')
    } catch (error) {
      const message =
        error?.response?.data?.errors?.file?.[0] ||
        error?.response?.data?.message ||
        'Unable to upload attachment.'
      toast.error(message)
    } finally {
      setUploadingAttachment(false)
    }
  }

  const handleAssignmentUpdate = async () => {
    setSavingAssignment(true)
    try {
      await tasksAPI.assignTask(taskId, {
        assigned_to: selectedAssigneeId || null,
      })
      toast.success(selectedAssigneeId ? 'Assignee updated.' : 'Task unassigned.')
      await loadTaskData()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update assignee.')
    } finally {
      setSavingAssignment(false)
    }
  }

  const handleStatusOnlyUpdate = async () => {
    setSavingStatus(true)
    try {
      await dispatch(updateTask({ id: taskId, data: { status: statusDraft } })).unwrap()
      toast.success('Task status updated.')
      await loadTaskData()
    } catch (error) {
      toast.error(error?.message || 'Unable to update task status.')
    } finally {
      setSavingStatus(false)
    }
  }

  const handleAttachmentAccess = async (attachment, mode) => {
    const actionKey = `${attachment.id}:${mode}`
    setAttachmentActionKey(actionKey)

    try {
      const response =
        mode === 'preview'
          ? await attachmentsAPI.previewAttachment(attachment.id)
          : await attachmentsAPI.downloadAttachment(attachment.id)

      const blob = new Blob([response.data], {
        type: response.headers['content-type'] || attachment.mime_type || 'application/octet-stream',
      })
      const blobUrl = window.URL.createObjectURL(blob)

      if (mode === 'preview') {
        const previewWindow = window.open(blobUrl, '_blank', 'noopener,noreferrer')
        if (!previewWindow) {
          window.location.assign(blobUrl)
        }
      } else {
        const downloadLink = document.createElement('a')
        downloadLink.href = blobUrl
        downloadLink.download = attachment.original_name
        document.body.appendChild(downloadLink)
        downloadLink.click()
        document.body.removeChild(downloadLink)
      }

      window.setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60_000)
    } catch (error) {
      toast.error(error?.response?.data?.message || `Unable to ${mode} attachment.`)
    } finally {
      setAttachmentActionKey('')
    }
  }

  const handleAttachmentDelete = async (attachmentId) => {
    if (!window.confirm('Delete this attachment?')) {
      return
    }

    try {
      await attachmentsAPI.deleteAttachment(attachmentId)
      await loadTaskData()
      toast.success('Attachment deleted.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to delete attachment.')
    }
  }

  const handleToggleFavorite = async () => {
    setSavingMetaAction('favorite')
    try {
      await tasksAPI.toggleFavorite(taskId)
      await loadTaskData()
      toast.success(task.is_favorite ? 'Task removed from favorites.' : 'Task added to favorites.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update favorite state.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleToggleWatch = async () => {
    setSavingMetaAction('watch')
    try {
      if (task.is_watching) {
        await tasksAPI.unwatchTask(taskId)
      } else {
        await tasksAPI.watchTask(taskId)
      }
      await loadTaskData()
      toast.success(task.is_watching ? 'Stopped watching this task.' : 'You are now watching this task.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update watcher state.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleLabelsUpdate = async (event) => {
    const selectedIds = Array.from(event.target.selectedOptions, (option) => option.value)
    setSavingMetaAction('labels')
    try {
      await tasksAPI.updateTask(taskId, { labels: selectedIds })
      await loadTaskData()
      toast.success('Task labels updated.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update labels.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleCreateLabel = async (event) => {
    event.preventDefault()
    if (!labelDraft.name.trim()) {
      toast.error('Add a label name first.')
      return
    }

    setSavingMetaAction('create-label')
    try {
      await tasksAPI.createLabel({
        team_id: task.team,
        name: labelDraft.name.trim(),
        color: labelDraft.color,
      })
      setLabelDraft({ name: '', color: labelPalette[0] })
      await loadTaskData()
      toast.success('Label created.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to create label.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleChecklistCreate = async (event) => {
    event.preventDefault()
    if (!checklistDraft.trim()) {
      return
    }

    setSavingMetaAction('checklist-create')
    try {
      await tasksAPI.createChecklistItem(taskId, { title: checklistDraft.trim() })
      setChecklistDraft('')
      await loadTaskData()
      toast.success('Checklist item added.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to add checklist item.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleChecklistToggle = async (item) => {
    setSavingMetaAction(`checklist-${item.id}`)
    try {
      await tasksAPI.updateChecklistItem(item.id, { is_completed: !item.is_completed })
      await loadTaskData()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update checklist item.')
    } finally {
      setSavingMetaAction('')
    }
  }

  const handleChecklistDelete = async (itemId) => {
    setSavingMetaAction(`checklist-delete-${itemId}`)
    try {
      await tasksAPI.deleteChecklistItem(itemId)
      await loadTaskData()
      toast.success('Checklist item removed.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to remove checklist item.')
    } finally {
      setSavingMetaAction('')
    }
  }

  if (loading || !task) {
    return <LoadingState label="Loading task detail" />
  }

  const currentRole = resolveMembershipRole(team)
  const canManage = canManageTask(currentRole)
  const canDeleteCurrentTask = canDeleteTask(currentRole)
  const canAssignCurrentTask = canAssignTask(currentRole)
  const canChangeCurrentTaskStatus = canChangeTaskStatus({
    role: currentRole,
    currentUserId: currentUser?.id,
    assignedToId: task.assigned_to,
  })
  const canUploadAttachments = Boolean(currentRole) && !task.is_archived
  const teamTaskPath = task.team ? `/teams/${task.team}` : '/tasks'
  const teamOverviewPath = task.team ? `/teams/${task.team}/overview` : '/teams'
  const teamCalendarPath = task.team ? `/teams/${task.team}/calendar` : '/calendar'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={teamTaskPath} className="btn-secondary">
          Back to tasks
        </Link>
        <Link to={teamOverviewPath} className="btn-ghost">
          Open team overview
        </Link>
        <Link to={teamCalendarPath} className="btn-ghost">
          Team deadlines
        </Link>
      </div>

      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.15fr,0.85fr] lg:px-8 lg:py-8">
          <div>
            <div className="stat-chip">{toSentenceCase(task.status)}</div>
            <h1 className="mt-4 font-display text-4xl font-bold text-emerald-950">{task.title}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-soft">
              {task.description || 'No detailed description has been added for this task yet.'}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-600">
                Priority: {toSentenceCase(task.priority || 'medium')}
              </span>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                Due: {task.due_date ? formatDate(task.due_date) : 'Not set'}
              </span>
              <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">
                Assignee: {task.assigned_to_data?.name || 'Unassigned'}
              </span>
            </div>
          </div>

          <div className={`${compactSurface} p-5`}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Quick actions</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={handleToggleFavorite} className="btn-secondary" disabled={savingMetaAction === 'favorite'}>
                {savingMetaAction === 'favorite' ? 'Saving...' : task.is_favorite ? 'Favorited' : 'Favorite'}
              </button>
              <button type="button" onClick={handleToggleWatch} className="btn-secondary" disabled={savingMetaAction === 'watch'}>
                {savingMetaAction === 'watch' ? 'Saving...' : task.is_watching ? 'Watching' : 'Watch task'}
              </button>
              {canManage ? (
                <button type="button" onClick={() => setIsEditing((current) => !current)} className="btn-secondary">
                  {isEditing ? 'Close editor' : 'Edit task'}
                </button>
              ) : null}
              {canDeleteCurrentTask ? (
                <button type="button" onClick={handleDelete} className="btn-primary">
                  Delete task
                </button>
              ) : null}
            </div>

            <div className="mt-4 grid gap-2 text-xs text-slate-600">
              <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2">
                <span>Comments</span>
                <strong>{task.comment_count || comments.length}</strong>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2">
                <span>Attachments</span>
                <strong>{task.attachment_count || attachments.length}</strong>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2">
                <span>Watchers</span>
                <strong>{task.watchers?.length || 0}</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="space-y-6">
          {isEditing && canManage ? (
            <form onSubmit={handleSubmit(handleUpdate)} className={`${panelClass} grid gap-4 p-6 lg:p-7`}>
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Title</label>
                <input {...register('title')} className="input-field" />
              </div>
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Description</label>
                <textarea {...register('description')} className="input-field min-h-[160px]" />
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Priority</label>
                  <select {...register('priority')} className="input-field">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Status</label>
                  <select {...register('status')} className="input-field" disabled={!canChangeCurrentTaskStatus}>
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="in_review">In Review</option>
                    <option value="done">Done</option>
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Start time</label>
                  <input type="datetime-local" {...register(TASK_FIELD_KEYS.startAt)} className="input-field" />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-semibold text-emerald-950">Due date</label>
                  <input type="datetime-local" {...register(TASK_FIELD_KEYS.dueAt)} className="input-field" />
                </div>
              </div>
              <div className="flex justify-end">
                <button type="submit" disabled={isSubmitting} className="btn-primary">
                  {isSubmitting ? 'Saving changes...' : 'Save changes'}
                </button>
              </div>
            </form>
          ) : null}

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Conversation</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Comments</h2>
              </div>
              <div className="stat-chip">{comments.length}</div>
            </div>

            <div className="mt-5 space-y-4">
              {comments.length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">
                  No comments yet. Start the conversation for this task.
                </div>
              ) : (
                comments.map((comment) => (
                  <CommentCard
                    key={comment.id}
                    comment={comment}
                    currentUserId={currentUser?.id}
                    currentRole={currentRole}
                    onViewHistory={handleCommentHistory}
                    onReply={postComment}
                    onUpdate={handleCommentUpdate}
                    onDelete={handleCommentDelete}
                    onToggleReaction={handleCommentReactionToggle}
                  />
                ))
              )}
            </div>

            <form onSubmit={handleCommentSubmit} className="mt-5 space-y-3">
              <textarea
                value={commentValue}
                onChange={(event) => setCommentValue(event.target.value)}
                className="input-field min-h-[120px]"
                placeholder="Add a comment or mention a teammate with @handle"
              />
              <button type="submit" disabled={submittingComment} className="btn-primary">
                {submittingComment ? 'Posting comment...' : 'Post comment'}
              </button>
            </form>
          </section>
        </div>

        <div className="space-y-6">
          <section className={`${panelClass} p-6 lg:p-7`}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Task metadata</p>
            <h2 className="mt-2 text-2xl font-bold text-emerald-950">Details</h2>

            <div className="mt-5 space-y-4 text-sm">
              <DetailRow label="Team" value={task.team_name} />
              <DetailRow label="Priority" value={toSentenceCase(task.priority)} />
              <DetailRow label="Status" value={toSentenceCase(task.status)} />
              <DetailRow label="Start time" value={formatDate(task.start_at)} />
              <DetailRow label="Due date" value={formatDate(task.due_date)} />
              <DetailRow label="Created by" value={task.created_by_data?.name || 'Unknown'} />
              <DetailRow label="Assigned to" value={task.assigned_to_data?.name || 'Unassigned'} />
              <DetailRow label="Watchers" value={String(task.watchers?.length || 0)} />
              <DetailRow label="Comments" value={String(task.comment_count || comments.length)} />
              <DetailRow label="Attachments" value={String(task.attachment_count || attachments.length)} />
            </div>

            <div className="mt-5">
              <p className="text-sm font-semibold text-emerald-950">Labels</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {task.labels?.length ? (
                  task.labels.map((label) => (
                    <span
                      key={label.id}
                      className="rounded-full px-3 py-1 text-xs font-semibold text-white"
                      style={{ backgroundColor: label.color || '#10b981' }}
                    >
                      {label.name}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-soft">No labels attached yet.</span>
                )}
              </div>

              <div className="mt-4 space-y-3">
                <select
                  multiple
                  className="input-field min-h-[136px]"
                  value={task.labels?.map((label) => label.id) || []}
                  onChange={handleLabelsUpdate}
                  disabled={savingMetaAction === 'labels'}
                >
                  {teamLabels.map((label) => (
                    <option key={label.id} value={label.id}>
                      {label.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">Hold Ctrl/Cmd to select multiple labels.</p>

                <form onSubmit={handleCreateLabel} className="rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
                  <p className="text-sm font-semibold text-emerald-950">Create a new label</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-[1fr,auto,auto]">
                    <input
                      value={labelDraft.name}
                      onChange={(event) => setLabelDraft((current) => ({ ...current, name: event.target.value }))}
                      className="input-field"
                      placeholder="Customer-facing"
                    />
                    <select
                      value={labelDraft.color}
                      onChange={(event) => setLabelDraft((current) => ({ ...current, color: event.target.value }))}
                      className="input-field"
                    >
                      {labelPalette.map((color) => (
                        <option key={color} value={color}>
                          {color}
                        </option>
                      ))}
                    </select>
                    <button type="submit" disabled={savingMetaAction === 'create-label'} className="btn-secondary">
                      {savingMetaAction === 'create-label' ? 'Creating...' : 'Create label'}
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {canAssignCurrentTask ? (
              <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Assigned teammate</label>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <select
                    value={selectedAssigneeId}
                    onChange={(event) => setSelectedAssigneeId(event.target.value)}
                    className="input-field flex-1"
                  >
                    <option value="">Unassigned</option>
                    {teamMembers.map((membership) => (
                      <option key={membership.id} value={membership.user?.id || ''}>
                        {membership.user?.name || membership.user?.email || 'Team member'}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAssignmentUpdate}
                    disabled={savingAssignment}
                    className="btn-secondary"
                  >
                    {savingAssignment ? 'Updating...' : 'Update assignee'}
                  </button>
                </div>
              </div>
            ) : null}

            {!canManage && canChangeCurrentTaskStatus ? (
              <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Update your task status</label>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <select value={statusDraft} onChange={(event) => setStatusDraft(event.target.value)} className="input-field flex-1">
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="in_review">In Review</option>
                    <option value="done">Done</option>
                  </select>
                  <button
                    type="button"
                    onClick={handleStatusOnlyUpdate}
                    disabled={savingStatus || statusDraft === task.status}
                    className="btn-secondary"
                  >
                    {savingStatus ? 'Updating...' : 'Update status'}
                  </button>
                </div>
              </div>
            ) : null}

            <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-sm font-semibold text-emerald-950">Watchers</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {task.watchers?.length ? (
                  task.watchers.map((watcher) => (
                    <span key={watcher.id} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                      {watcher.user?.name || watcher.user?.email || 'Watcher'}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-500">No watchers yet.</span>
                )}
              </div>
            </div>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Dependencies</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Blocked work and relationships</h2>
              </div>
              <div className="stat-chip">
                {(task.dependencies_incoming || []).length + (task.dependencies_outgoing || []).length}
              </div>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <div className="rounded-[22px] border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Blocked by</p>
                <div className="mt-3 space-y-2">
                  {(task.dependencies_incoming || []).length === 0 ? (
                    <p className="text-sm text-slate-500">No incoming blockers.</p>
                  ) : (
                    task.dependencies_incoming.map((dependency) => (
                      <div key={dependency.id} className="flex items-center justify-between rounded-2xl border border-slate-200 px-3 py-2">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{dependency.from_task_title}</p>
                          <p className="text-xs text-slate-500">Status: {dependency.from_task_status?.replaceAll('_', ' ')}</p>
                        </div>
                        <button type="button" onClick={() => handleRemoveDependency(dependency.id)} className="btn-ghost">
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Blocking</p>
                <div className="mt-3 space-y-2">
                  {(task.dependencies_outgoing || []).length === 0 ? (
                    <p className="text-sm text-slate-500">No outgoing dependencies.</p>
                  ) : (
                    task.dependencies_outgoing.map((dependency) => (
                      <div key={dependency.id} className="flex items-center justify-between rounded-2xl border border-slate-200 px-3 py-2">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{dependency.to_task_title}</p>
                          <p className="text-xs text-slate-500">Status: {dependency.to_task_status?.replaceAll('_', ' ')}</p>
                        </div>
                        <button type="button" onClick={() => handleRemoveDependency(dependency.id)} className="btn-ghost">
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <input
                  value={dependencySearch}
                  onChange={(event) => setDependencySearch(event.target.value)}
                  className="input-field flex-1"
                  placeholder="Search tasks to link as dependencies"
                />
                <select value={dependencyType} onChange={(event) => setDependencyType(event.target.value)} className="input-field">
                  <option value="blocks">Blocks</option>
                  <option value="related_to">Related</option>
                </select>
              </div>
              <div className="mt-4 grid gap-2">
                {dependencyLoading ? (
                  <p className="text-sm text-slate-500">Searching tasks...</p>
                ) : dependencyResults.length ? (
                  dependencyResults.map((candidate) => (
                    <button
                      key={candidate.id}
                      type="button"
                      onClick={() => handleAddDependency(candidate.id)}
                      className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-3 py-2 text-left hover:bg-slate-50"
                    >
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{candidate.title}</p>
                        <p className="text-xs text-slate-500">{candidate.team_name || team?.name || 'Team task'}</p>
                      </div>
                      <span className="text-xs font-semibold text-emerald-700">Link</span>
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">Search for tasks to create a dependency link.</p>
                )}
              </div>
            </div>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Time tracking</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Track effort in real time</h2>
              </div>
              <div className="stat-chip">{task.total_tracked_seconds ? `${Math.round(task.total_tracked_seconds / 60)} min` : '0 min'}</div>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              {activeTimeEntry ? (
                <button type="button" onClick={handleStopTimer} disabled={timeEntryBusy} className="btn-primary">
                  {timeEntryBusy ? 'Stopping...' : 'Stop timer'}
                </button>
              ) : (
                <button type="button" onClick={handleStartTimer} disabled={timeEntryBusy} className="btn-secondary">
                  {timeEntryBusy ? 'Starting...' : 'Start timer'}
                </button>
              )}
              {activeTimeEntry ? (
                <span className="text-sm font-semibold text-emerald-900">
                  Running since {formatDate(activeTimeEntry.start_time)}
                </span>
              ) : (
                <span className="text-sm text-slate-500">No active timer running.</span>
              )}
            </div>

            <form onSubmit={handleManualEntry} className="mt-5 grid gap-3 md:grid-cols-3">
              <label className="text-sm font-semibold text-slate-900">
                Start
                <input
                  type="datetime-local"
                  value={manualStart}
                  onChange={(event) => setManualStart(event.target.value)}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900">
                End
                <input
                  type="datetime-local"
                  value={manualEnd}
                  onChange={(event) => setManualEnd(event.target.value)}
                  className="input-field mt-2"
                />
              </label>
              <label className="text-sm font-semibold text-slate-900 md:col-span-1">
                Notes
                <input
                  value={timeEntryNote}
                  onChange={(event) => setTimeEntryNote(event.target.value)}
                  className="input-field mt-2"
                  placeholder="Optional notes"
                />
              </label>
              <div className="md:col-span-3">
                <button type="submit" disabled={timeEntryBusy} className="btn-primary">
                  {timeEntryBusy ? 'Saving...' : 'Add manual entry'}
                </button>
              </div>
            </form>

            <div className="mt-5 space-y-3">
              {timeEntries.length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">No time entries logged yet.</div>
              ) : (
                timeEntries.map((entry) => (
                  <div key={entry.id} className="glass-panel flex items-center justify-between gap-3 p-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{entry.user?.name || 'Teammate'}</p>
                      <p className="text-xs text-slate-500">
                        {formatDate(entry.start_time)} → {entry.end_time ? formatDate(entry.end_time) : 'In progress'}
                      </p>
                      {entry.notes ? <p className="mt-1 text-xs text-slate-500">{entry.notes}</p> : null}
                    </div>
                    <span className="text-xs font-semibold text-emerald-700">
                      {entry.duration_seconds ? `${Math.round(entry.duration_seconds / 60)} min` : '—'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Guest access</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Invite external reviewers</h2>
              </div>
              <div className="stat-chip">{guestAccess.length}</div>
            </div>

            <form onSubmit={handleGuestAccessCreate} className="mt-5 grid gap-3 md:grid-cols-[1fr,160px,140px]">
              <input
                value={guestEmail}
                onChange={(event) => setGuestEmail(event.target.value)}
                className="input-field"
                placeholder="guest@example.com"
              />
              <select value={guestPermission} onChange={(event) => setGuestPermission(event.target.value)} className="input-field">
                <option value="view">View only</option>
                <option value="comment">Comment</option>
              </select>
              <button type="submit" className="btn-primary">
                Grant access
              </button>
            </form>

            <div className="mt-5 space-y-3">
              {guestAccess.length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">No guest access entries yet.</div>
              ) : (
                guestAccess.map((entry) => (
                  <div key={entry.id} className="glass-panel flex items-center justify-between gap-3 p-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{entry.email}</p>
                      <p className="text-xs text-slate-500">Permission: {entry.permission}</p>
                    </div>
                    <button type="button" onClick={() => handleGuestAccessRevoke(entry.id)} className="btn-ghost">
                      Revoke
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Checklist</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Subtasks and progress</h2>
              </div>
              <div className="stat-chip">
                {(task.checklist_items || []).filter((item) => item.is_completed).length}/{task.checklist_items?.length || 0}
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {(task.checklist_items || []).length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">Break this task into checklist items to make progress visible.</div>
              ) : (
                task.checklist_items.map((item) => (
                  <div key={item.id} className="glass-panel flex items-center justify-between gap-3 p-4">
                    <label className="flex min-w-0 flex-1 items-center gap-3">
                      <input
                        type="checkbox"
                        checked={item.is_completed}
                        onChange={() => handleChecklistToggle(item)}
                        disabled={savingMetaAction === `checklist-${item.id}`}
                      />
                      <span className={`text-sm ${item.is_completed ? 'text-slate-400 line-through' : 'text-slate-800'}`}>
                        {item.title}
                      </span>
                    </label>
                    <button
                      type="button"
                      onClick={() => handleChecklistDelete(item.id)}
                      disabled={savingMetaAction === `checklist-delete-${item.id}`}
                      className="btn-ghost"
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>

            <form onSubmit={handleChecklistCreate} className="mt-5 flex flex-col gap-3 sm:flex-row">
              <input
                value={checklistDraft}
                onChange={(event) => setChecklistDraft(event.target.value)}
                className="input-field flex-1"
                placeholder="Add a checklist item"
              />
              <button type="submit" disabled={savingMetaAction === 'checklist-create'} className="btn-primary">
                {savingMetaAction === 'checklist-create' ? 'Adding...' : 'Add item'}
              </button>
            </form>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Activity</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Task timeline</h2>
              </div>
              <div className="stat-chip">{timeline.length}</div>
            </div>

            <div className="mt-5 space-y-3">
              {timeline.length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">Important changes to this task will appear here.</div>
              ) : (
                timeline.map((entry) => (
                  <div key={entry.id} className="glass-panel p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{toSentenceCase((entry.action || '').replaceAll('_', ' '))}</p>
                        <p className="mt-1 text-sm text-slate-600">
                          {entry.actor?.name || 'System'} • {entry.target_repr || 'Task update'}
                        </p>
                      </div>
                      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                        {formatRelativeDate(entry.created_at)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className={`${panelClass} p-6 lg:p-7`}>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Attachments</p>
            <h2 className="mt-2 text-2xl font-bold text-emerald-950">Files</h2>

            {canUploadAttachments ? (
              <form onSubmit={handleAttachmentUpload} className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4">
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Upload a file</label>
                <input
                  type="file"
                  onChange={(event) => setAttachmentFile(event.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-600"
                />
                <button type="submit" disabled={!attachmentFile || uploadingAttachment} className="btn-primary mt-4">
                  {uploadingAttachment ? 'Uploading...' : 'Upload attachment'}
                </button>
              </form>
            ) : (
              <div className="mt-5 rounded-[24px] border border-slate-200 bg-slate-50/70 p-4 text-sm text-slate-600">
                Attachments can only be uploaded by active team members while the task is not archived.
              </div>
            )}

            <div className="mt-5 space-y-3">
              {attachments.length === 0 ? (
                <div className="rounded-[24px] bg-emerald-50/70 p-5 text-sm text-soft">No attachments uploaded for this task yet.</div>
              ) : (
                attachments.map((attachment) => (
                  <div key={attachment.id} className="glass-panel flex items-start justify-between gap-4 p-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-emerald-950">{attachment.original_name}</p>
                      <p className="mt-1 text-sm text-soft">
                        {attachment.mime_type || 'File'} • {attachment.file_size} bytes
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleAttachmentAccess(attachment, 'preview')}
                        disabled={attachmentActionKey === `${attachment.id}:preview`}
                        className="btn-ghost"
                      >
                        {attachmentActionKey === `${attachment.id}:preview` ? 'Opening...' : 'Preview'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAttachmentAccess(attachment, 'download')}
                        disabled={attachmentActionKey === `${attachment.id}:download`}
                        className="btn-ghost"
                      >
                        {attachmentActionKey === `${attachment.id}:download` ? 'Downloading...' : 'Download'}
                      </button>
                      {attachment.can_delete ? (
                        <button type="button" onClick={() => handleAttachmentDelete(attachment.id)} className="btn-ghost">
                          Delete
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </div>

      {historyComment ? (
        <CommentHistoryModal
          comment={historyComment}
          historyItems={historyItems}
          loading={historyLoading}
          onClose={() => {
            setHistoryComment(null)
            setHistoryItems([])
          }}
        />
      ) : null}
    </div>
  )
}

function CommentCard({ comment, currentUserId, currentRole, onViewHistory, onReply, onUpdate, onDelete, onToggleReaction }) {
  const [replying, setReplying] = useState(false)
  const [editing, setEditing] = useState(false)
  const [replyValue, setReplyValue] = useState('')
  const [editValue, setEditValue] = useState(comment.content)
  const isOwnComment = comment.author_data?.id === currentUserId
  const canDeleteCurrentComment = canDeleteComment({
    role: currentRole,
    currentUserId,
    authorId: comment.author_data?.id,
  })

  const submitReply = async (event) => {
    event.preventDefault()
    await onReply(replyValue, comment.id)
    setReplyValue('')
    setReplying(false)
  }

  const submitEdit = async (event) => {
    event.preventDefault()
    await onUpdate(comment.id, editValue)
    setEditing(false)
  }

  return (
    <div className="glass-panel p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-emerald-950">{comment.author_data?.name || 'Unknown author'}</p>
          <p className="text-xs uppercase tracking-[0.16em] text-soft">{formatDate(comment.created_at)}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => setReplying((current) => !current)} className="btn-ghost">
            Reply
          </button>
          {isOwnComment ? (
            <>
              <button type="button" onClick={() => setEditing((current) => !current)} className="btn-ghost">
                Edit
              </button>
            </>
          ) : null}
          {canDeleteCurrentComment ? (
            <button type="button" onClick={() => onDelete(comment.id)} className="btn-ghost">
              Delete
            </button>
          ) : null}
        </div>
      </div>

      {editing ? (
        <form onSubmit={submitEdit} className="mt-3 space-y-3">
          <textarea value={editValue} onChange={(event) => setEditValue(event.target.value)} className="input-field min-h-[110px]" />
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setEditing(false)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Save edit
            </button>
          </div>
        </form>
      ) : (
        <div className="mt-3">
          <p className="text-sm leading-6 text-soft">{comment.content}</p>
          {comment.is_edited ? (
            <div className="mt-2 flex items-center gap-3">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Edited
              </span>
              {comment.edit_history_count ? (
                <button type="button" onClick={() => onViewHistory(comment)} className="text-xs font-semibold text-emerald-700">
                  View history
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      {comment.mentioned_users?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {comment.mentioned_users.map((user) => (
            <span key={user.id} className="micro-chip">
              @{user.handle}
            </span>
          ))}
        </div>
      ) : null}

      {!comment.is_deleted ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {commentReactionOptions.map((emoji) => {
            const reaction = comment.reactions?.find((item) => item.emoji === emoji)
            const reacted = Boolean(reaction?.reacted)
            const count = reaction?.count || 0

            return (
              <button
                key={emoji}
                type="button"
                onClick={() => onToggleReaction(comment.id, emoji)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors ${
                  reacted
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                <span>{emoji}</span>
                <span>{count}</span>
              </button>
            )
          })}
        </div>
      ) : null}

      {replying ? (
        <form onSubmit={submitReply} className="mt-4 space-y-3 rounded-[20px] border border-slate-200 bg-white/70 p-4">
          <textarea
            value={replyValue}
            onChange={(event) => setReplyValue(event.target.value)}
            className="input-field min-h-[100px]"
            placeholder="Write a reply"
          />
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setReplying(false)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Post reply
            </button>
          </div>
        </form>
      ) : null}

      {comment.replies?.length ? (
        <div className="mt-4 space-y-3 border-l border-emerald-200 pl-4">
          {comment.replies.map((reply) => (
            <CommentCard
              key={reply.id}
              comment={reply}
              currentUserId={currentUserId}
              currentRole={currentRole}
              onReply={onReply}
              onViewHistory={onViewHistory}
              onUpdate={onUpdate}
              onDelete={onDelete}
              onToggleReaction={onToggleReaction}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function DetailRow({ label, value }) {
  return (
    <div className="glass-panel flex items-center justify-between gap-4 px-4 py-3">
      <span className="font-semibold text-emerald-950">{label}</span>
      <span className="text-right text-soft">{value}</span>
    </div>
  )
}

function CommentHistoryModal({ comment, historyItems, loading, onClose }) {
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-emerald-950/12 px-4 py-10 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_32px_120px_rgba(15,23,42,0.22)]" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Comment history</p>
            <h3 className="mt-2 text-2xl font-bold text-emerald-950">{comment.author_data?.name || 'Comment author'}</h3>
          </div>
          <button type="button" onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>

        <div className="mt-5 space-y-3">
          {loading ? (
            <LoadingState label="Loading comment history" />
          ) : historyItems.length === 0 ? (
            <EmptyState title="No edit history" description="This comment has no earlier saved revisions." />
          ) : (
            historyItems.map((item) => (
              <div key={item.id} className="feature-tile">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {formatDate(item.edited_at || item.created_at)}
                </p>
                <p className="mt-3 text-sm leading-6 text-soft">{item.content}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
