import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { calendarAPI, dashboardAPI, teamsAPI, unwrapData } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'
import { resolveMembershipRole } from '../utils/permissions'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

function downloadTextFile(content, filename, mimeType = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export default function TeamCalendar() {
  const { teamId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [events, setEvents] = useState([])
  const [query, setQuery] = useState('')
  const [googleStatus, setGoogleStatus] = useState(null)
  const [googleCalendars, setGoogleCalendars] = useState([])
  const [selectedCalendarId, setSelectedCalendarId] = useState('')
  const [previewBatchId, setPreviewBatchId] = useState('')
  const [importPreview, setImportPreview] = useState([])
  const [selectedEventIds, setSelectedEventIds] = useState([])
  const [busyAction, setBusyAction] = useState('')

  const role = resolveMembershipRole(team)
  const canManageCalendar = role === 'admin' || role === 'manager'
  const exportOwnTasksOnly = role === 'member'

  const loadCalendar = useCallback(async () => {
    setLoading(true)
    try {
      const [teamResponse, calendarResponse, statusResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        dashboardAPI.getTeamCalendar(teamId, { page_size: 200 }),
        calendarAPI.getGoogleStatus({ scope: 'team', team_id: teamId }),
      ])
      const payload = unwrapData(calendarResponse)
      const items = Array.isArray(payload)
        ? payload
        : Array.isArray(payload?.results)
          ? payload.results
          : Array.isArray(payload?.events)
            ? payload.events
            : []
      const statusPayload = unwrapData(statusResponse) || null
      setTeam(unwrapData(teamResponse))
      setEvents(items)
      setGoogleStatus(statusPayload)
      setSelectedCalendarId(statusPayload?.calendar_id || '')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load team deadlines.')
      setEvents([])
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    loadCalendar()
  }, [loadCalendar])

  useEffect(() => {
    const syncState = searchParams.get('calendar_sync')
    if (!syncState) return
    if (syncState === 'connected') {
      toast.success('Team Google Calendar connected successfully.')
    } else if (syncState === 'failed') {
      toast.error(searchParams.get('reason') || 'Team Google Calendar connection failed.')
    }
    const next = new URLSearchParams(searchParams)
    next.delete('calendar_sync')
    next.delete('reason')
    next.delete('scope')
    next.delete('team_id')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const normalizedEvents = useMemo(
    () =>
      events.map((item) => ({
        id: item.task_id || item.id,
        title: item.title || item.task_title || 'Scheduled task',
        dueDate: item.due_date || item.date || null,
        startAt: item.start_at || item.start_date || null,
        priority: toSentenceCase(item.priority || 'medium'),
        status: toSentenceCase(item.status || 'scheduled'),
        assignee: item.assigned_to_data?.name || item.assigned_to_name || item.assignee?.name || 'Unassigned',
        taskId: item.task_id || item.task || null,
      })),
    [events]
  )

  const filteredEvents = useMemo(() => {
    const input = query.trim().toLowerCase()
    if (!input) return normalizedEvents
    return normalizedEvents.filter((item) => {
      const haystack = `${item.title} ${item.assignee} ${item.priority} ${item.status}`
      return haystack.toLowerCase().includes(input)
    })
  }, [normalizedEvents, query])

  const groupedByDate = useMemo(() => {
    return filteredEvents.reduce((accumulator, event) => {
      const key = event.dueDate ? formatDate(event.dueDate) : 'No due date'
      if (!accumulator[key]) {
        accumulator[key] = []
      }
      accumulator[key].push(event)
      return accumulator
    }, {})
  }, [filteredEvents])

  const overdueItems = filteredEvents.filter((item) => isOverdue(item.dueDate, item.status))
  const dueSoonItems = filteredEvents.filter((item) => isDueSoon(item.dueDate, item.status))
  const dueTodayItems = filteredEvents.filter((item) => isToday(item.dueDate, item.status))

  const handleExport = async () => {
    setBusyAction('export')
    try {
      const response = await calendarAPI.exportTasksICS({
        scope: 'team',
        team_id: teamId,
        task_ids: filteredEvents.map((item) => item.taskId).filter(Boolean),
        include_my_tasks: exportOwnTasksOnly,
      })
      const payload = unwrapData(response) || {}
      downloadTextFile(payload.content || '', payload.filename || 'team-tasks.ics', 'text/calendar;charset=utf-8')
      toast.success('Team calendar export downloaded.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to export team calendar.')
    } finally {
      setBusyAction('')
    }
  }

  const handleImportPreview = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    setBusyAction('preview-import')
    try {
      const formData = new FormData()
      formData.append('scope', 'team')
      formData.append('team_id', teamId)
      formData.append('file', file)
      const response = await calendarAPI.previewICSImport(formData)
      const payload = unwrapData(response) || {}
      const entries = Array.isArray(payload.events) ? payload.events : []
      setPreviewBatchId(payload.batch_id || '')
      setImportPreview(entries)
      setSelectedEventIds(entries.filter((item) => item.is_valid).map((item) => item.event_id))
      toast.success('Team import preview ready.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to preview team import.')
    } finally {
      setBusyAction('')
      event.target.value = ''
    }
  }

  const handleConfirmImport = async () => {
    if (!previewBatchId) return
    setBusyAction('confirm-import')
    try {
      const response = await calendarAPI.confirmImport({
        batch_id: previewBatchId,
        import_all: false,
        event_ids: selectedEventIds,
      })
      const payload = unwrapData(response) || {}
      toast.success(`Imported ${payload.created_count || 0} team tasks.`)
      setPreviewBatchId('')
      setImportPreview([])
      setSelectedEventIds([])
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to import selected team events.')
    } finally {
      setBusyAction('')
    }
  }

  const handleConnectGoogle = async () => {
    setBusyAction('google-connect')
    try {
      const response = await calendarAPI.connectGoogle({
        scope: 'team',
        team_id: teamId,
        return_path: `/teams/${teamId}/calendar`,
      })
      const url = unwrapData(response)?.authorization_url
      if (!url) {
        throw new Error('Missing Google authorization URL.')
      }
      window.location.assign(url)
    } catch (error) {
      toast.error(error?.response?.data?.message || error.message || 'Unable to start Google Calendar connection.')
      setBusyAction('')
    }
  }

  const handleDisconnectGoogle = async () => {
    setBusyAction('google-disconnect')
    try {
      await calendarAPI.disconnectGoogle({ scope: 'team', team_id: teamId })
      toast.success('Team Google Calendar disconnected.')
      setGoogleCalendars([])
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to disconnect team Google Calendar.')
    } finally {
      setBusyAction('')
    }
  }

  const handleLoadGoogleCalendars = async () => {
    setBusyAction('google-calendars')
    try {
      const response = await calendarAPI.listGoogleCalendars({ scope: 'team', team_id: teamId })
      const payload = unwrapData(response) || {}
      setGoogleCalendars(Array.isArray(payload.calendars) ? payload.calendars : [])
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load Google calendars.')
    } finally {
      setBusyAction('')
    }
  }

  const handleSaveCalendarSelection = async () => {
    if (!selectedCalendarId) return
    setBusyAction('google-select')
    try {
      const selectedCalendar = googleCalendars.find((calendar) => calendar.id === selectedCalendarId)
      await calendarAPI.selectGoogleCalendar({
        scope: 'team',
        team_id: teamId,
        calendar_id: selectedCalendarId,
        calendar_name: selectedCalendar?.summary || '',
      })
      toast.success('Team target calendar saved.')
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update Google calendar target.')
    } finally {
      setBusyAction('')
    }
  }

  const handleSyncGoogle = async () => {
    setBusyAction('google-sync')
    try {
      const response = await calendarAPI.syncGoogleTasks({
        scope: 'team',
        team_id: teamId,
        task_ids: filteredEvents.map((item) => item.taskId).filter(Boolean),
        include_my_tasks: exportOwnTasksOnly,
      })
      const payload = unwrapData(response) || {}
      toast.success(
        `Team sync complete. Created ${payload.created_events || 0}, updated ${payload.updated_events || 0}, failed ${payload.failed_events || 0}.`
      )
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Team Google sync failed.')
    } finally {
      setBusyAction('')
    }
  }

  if (loading || !team) {
    return <LoadingState label="Loading team calendar" />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Calendar & deadlines</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} schedule view</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Track today&apos;s tasks, due-soon work, and overdue commitments with role-aware import, export, and sync controls.
            </p>
            <p className="mt-2 text-sm text-slate-500">Role: {toSentenceCase(role || 'member')}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
              <button type="button" onClick={loadCalendar} className="btn-secondary">
                Refresh deadlines
              </button>
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Total scheduled" value={filteredEvents.length} note="Tasks in calendar scope" />
              <SummaryTile label="Due today" value={dueTodayItems.length} note="Immediate focus" />
              <SummaryTile label="Overdue" value={overdueItems.length} note="Needs intervention" tone="text-amber-700" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Calendar operations</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Import, export, and external sync</h2>
            <p className="mt-2 text-sm text-slate-600">
              {canManageCalendar
                ? 'Admins and managers can import team events and manage Google Calendar synchronization.'
                : 'Members can export their allowed tasks. Import and sync controls are managed by admins or managers.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={handleExport} disabled={busyAction !== ''}>
              {busyAction === 'export' ? 'Exporting...' : 'Export .ics'}
            </button>
            {canManageCalendar ? (
              <label className="btn-secondary cursor-pointer">
                <input type="file" accept=".ics,text/calendar" className="hidden" onChange={handleImportPreview} disabled={busyAction !== ''} />
                {busyAction === 'preview-import' ? 'Reading file...' : 'Import .ics'}
              </label>
            ) : null}
          </div>
        </div>

        {canManageCalendar ? (
          <div className="mt-5 rounded-[20px] border border-slate-200 bg-[#fcfcfb] p-4">
            <div className="flex flex-wrap gap-2">
              {!googleStatus?.connected ? (
                <button type="button" className="btn-primary" onClick={handleConnectGoogle} disabled={busyAction !== ''}>
                  {busyAction === 'google-connect' ? 'Redirecting...' : 'Connect Google'}
                </button>
              ) : (
                <>
                  <button type="button" className="btn-secondary" onClick={handleSyncGoogle} disabled={busyAction !== ''}>
                    {busyAction === 'google-sync' ? 'Syncing...' : 'Sync tasks'}
                  </button>
                  <button type="button" className="btn-secondary" onClick={handleDisconnectGoogle} disabled={busyAction !== ''}>
                    {busyAction === 'google-disconnect' ? 'Disconnecting...' : 'Disconnect'}
                  </button>
                </>
              )}
            </div>

            {googleStatus?.connected ? (
              <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-end">
                <label className="w-full text-sm font-medium text-slate-600">
                  Target Google calendar
                  <select
                    value={selectedCalendarId}
                    onChange={(event) => setSelectedCalendarId(event.target.value)}
                    className="input-field mt-2"
                  >
                    <option value="">Select a calendar</option>
                    {googleCalendars.map((calendar) => (
                      <option key={calendar.id} value={calendar.id}>
                        {calendar.summary}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary" onClick={handleLoadGoogleCalendars} disabled={busyAction !== ''}>
                    {busyAction === 'google-calendars' ? 'Loading...' : 'Load calendars'}
                  </button>
                  <button type="button" className="btn-secondary" onClick={handleSaveCalendarSelection} disabled={!selectedCalendarId || busyAction !== ''}>
                    {busyAction === 'google-select' ? 'Saving...' : 'Save target'}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      {canManageCalendar && importPreview.length ? (
        <section className={`${panelClass} p-6 lg:p-7`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Import preview</p>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">Select team events to import</h2>
            </div>
            <button type="button" className="btn-primary" onClick={handleConfirmImport} disabled={busyAction !== '' || !selectedEventIds.length}>
              {busyAction === 'confirm-import' ? 'Importing...' : `Import selected (${selectedEventIds.length})`}
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {importPreview.map((event) => (
              <label key={event.event_id} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedEventIds.includes(event.event_id)}
                  disabled={!event.is_valid}
                  onChange={(changeEvent) => {
                    setSelectedEventIds((current) =>
                      changeEvent.target.checked ? [...current, event.event_id] : current.filter((id) => id !== event.event_id)
                    )
                  }}
                />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{event.summary || 'Untitled event'}</p>
                  <p className="mt-1 text-xs text-slate-600">
                    {event.start_at ? formatDate(event.start_at) : 'No start'} | {event.end_at ? formatDate(event.end_at) : 'No end'}
                  </p>
                  {!event.is_valid ? <p className="mt-1 text-xs font-medium text-rose-600">{event.error}</p> : null}
                  {event.duplicate ? <p className="mt-1 text-xs font-medium text-amber-700">Duplicate title and due date already exists.</p> : null}
                </div>
              </label>
            ))}
          </div>
        </section>
      ) : null}

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Deadline filters</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Calendar feed</h2>
          </div>
          <label className="w-full max-w-md text-sm font-medium text-slate-600">
            Search by title, assignee, status, priority
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-field mt-2"
              placeholder="Search deadline entries"
            />
          </label>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <DeadlineBucket title="Due today" tone="sky" items={dueTodayItems} teamId={teamId} />
          <DeadlineBucket title="Due soon" tone="emerald" items={dueSoonItems} teamId={teamId} />
          <DeadlineBucket title="Overdue" tone="amber" items={overdueItems} teamId={teamId} />
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">By date</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Timeline list</h2>
          </div>
          <p className="text-sm text-slate-500">{Object.keys(groupedByDate).length} date groups</p>
        </div>

        {filteredEvents.length === 0 ? (
          <div className="mt-5">
            <EmptyState title="No dated tasks yet" description="As team tasks get start and due dates, they will appear in this calendar timeline." />
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {Object.entries(groupedByDate).map(([date, items]) => (
              <article key={date} className={`${cardClass} p-4`}>
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-slate-950">{date}</h3>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                    {items.length} tasks
                  </span>
                </div>
                <div className="mt-3 space-y-2">
                  {items.map((item) => (
                    <Link
                      key={item.id}
                      to={item.taskId ? `/tasks/${item.taskId}` : `/teams/${teamId}`}
                      className="block rounded-xl border border-slate-200 bg-white px-3 py-3 transition-colors hover:bg-slate-50"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                          {formatRelativeDate(item.dueDate)}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">
                        {item.assignee} | {item.priority} | {item.status}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Start {item.startAt ? formatDate(item.startAt) : 'Not set'} | Due {item.dueDate ? formatDate(item.dueDate) : 'Not set'}
                      </p>
                    </Link>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
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

function DeadlineBucket({ title, items, tone, teamId }) {
  const toneMap = {
    sky: 'bg-sky-50 text-sky-700 border-sky-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
  }

  return (
    <div className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
        <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${toneMap[tone]}`}>
          {items.length}
        </span>
      </div>
      <div className="mt-3 space-y-2">
        {items.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 px-3 py-3 text-sm text-slate-500">No tasks in this bucket.</p>
        ) : (
          items.slice(0, 4).map((item) => (
            <Link
              key={item.id}
              to={item.taskId ? `/tasks/${item.taskId}` : `/teams/${teamId}`}
              className="block rounded-xl border border-slate-200 bg-white px-3 py-3 transition-colors hover:bg-slate-50"
            >
              <p className="truncate text-sm font-semibold text-slate-900">{item.title}</p>
              <p className="mt-1 text-xs text-slate-500">{item.assignee}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  )
}

function isOverdue(value, status) {
  if (!value || String(status).toLowerCase() === 'done') return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  return date < new Date()
}

function isToday(value, status) {
  if (!value || String(status).toLowerCase() === 'done') return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const now = new Date()
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate()
}

function isDueSoon(value, status) {
  if (!value || String(status).toLowerCase() === 'done') return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  const diff = date.getTime() - Date.now()
  return diff > 0 && diff <= 1000 * 60 * 60 * 24 * 7
}
