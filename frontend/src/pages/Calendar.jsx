import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHero from '../components/PageHero'
import { calendarAPI, dashboardAPI, unwrapData } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'

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

export default function Calendar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [events, setEvents] = useState([])
  const [googleStatus, setGoogleStatus] = useState(null)
  const [googleCalendars, setGoogleCalendars] = useState([])
  const [selectedCalendarId, setSelectedCalendarId] = useState('')
  const [previewBatchId, setPreviewBatchId] = useState('')
  const [importPreview, setImportPreview] = useState([])
  const [selectedEventIds, setSelectedEventIds] = useState([])
  const [busyAction, setBusyAction] = useState('')

  const loadCalendar = useCallback(async () => {
    setLoading(true)
    try {
      const [eventsResponse, statusResponse] = await Promise.all([
        dashboardAPI.getPersonalCalendar(),
        calendarAPI.getGoogleStatus({ scope: 'personal' }),
      ])
      const eventPayload = unwrapData(eventsResponse)
      const statusPayload = unwrapData(statusResponse)
      setEvents(Array.isArray(eventPayload) ? eventPayload : [])
      setGoogleStatus(statusPayload || null)
      setSelectedCalendarId(statusPayload?.calendar_id || '')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load personal calendar.')
      setEvents([])
      setGoogleStatus(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCalendar()
  }, [loadCalendar])

  useEffect(() => {
    const syncState = searchParams.get('calendar_sync')
    if (!syncState) return
    if (syncState === 'connected') {
      toast.success('Google Calendar connected successfully.')
    } else if (syncState === 'failed') {
      toast.error(searchParams.get('reason') || 'Google Calendar connection failed.')
    }
    const next = new URLSearchParams(searchParams)
    next.delete('calendar_sync')
    next.delete('reason')
    next.delete('scope')
    next.delete('team_id')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const dueThisWeekCount = useMemo(() => {
    const now = new Date()
    const weekAhead = new Date()
    weekAhead.setDate(now.getDate() + 7)
    return events.filter((event) => {
      const dueDate = new Date(event.due_date)
      return !Number.isNaN(dueDate.getTime()) && dueDate >= now && dueDate <= weekAhead
    }).length
  }, [events])

  const groupedEvents = useMemo(() => {
    return events.reduce((accumulator, event) => {
      const key = formatDate(event.due_date)
      accumulator[key] = accumulator[key] || []
      accumulator[key].push(event)
      return accumulator
    }, {})
  }, [events])

  const handleExport = async () => {
    setBusyAction('export')
    try {
      const taskIds = events.map((event) => event.task_id).filter(Boolean)
      const response = await calendarAPI.exportTasksICS({
        scope: 'personal',
        task_ids: taskIds.length ? taskIds : undefined,
      })
      const payload = unwrapData(response) || {}
      downloadTextFile(payload.content || '', payload.filename || 'personal-tasks.ics', 'text/calendar;charset=utf-8')
      toast.success('Calendar export downloaded.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Calendar export failed.')
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
      formData.append('scope', 'personal')
      formData.append('file', file)
      const response = await calendarAPI.previewICSImport(formData)
      const payload = unwrapData(response) || {}
      const entries = Array.isArray(payload.events) ? payload.events : []
      setPreviewBatchId(payload.batch_id || '')
      setImportPreview(entries)
      setSelectedEventIds(entries.filter((item) => item.is_valid).map((item) => item.event_id))
      toast.success('Calendar import preview ready.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to preview calendar import.')
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
      toast.success(`Imported ${payload.created_count || 0} tasks.`)
      setPreviewBatchId('')
      setImportPreview([])
      setSelectedEventIds([])
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to import selected events.')
    } finally {
      setBusyAction('')
    }
  }

  const handleConnectGoogle = async () => {
    setBusyAction('google-connect')
    try {
      const response = await calendarAPI.connectGoogle({
        scope: 'personal',
        return_path: '/calendar',
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
      await calendarAPI.disconnectGoogle({ scope: 'personal' })
      toast.success('Google Calendar disconnected.')
      setGoogleCalendars([])
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to disconnect Google Calendar.')
    } finally {
      setBusyAction('')
    }
  }

  const handleLoadGoogleCalendars = async () => {
    setBusyAction('google-calendars')
    try {
      const response = await calendarAPI.listGoogleCalendars({ scope: 'personal' })
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
        scope: 'personal',
        calendar_id: selectedCalendarId,
        calendar_name: selectedCalendar?.summary || '',
      })
      toast.success('Google target calendar saved.')
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
      const taskIds = events.map((item) => item.task_id).filter(Boolean)
      const response = await calendarAPI.syncGoogleTasks({
        scope: 'personal',
        task_ids: taskIds.length ? taskIds : undefined,
        include_completed: true,
      })
      const payload = unwrapData(response) || {}
      toast.success(
        `Google sync complete. Created ${payload.created_events || 0}, updated ${payload.updated_events || 0}, failed ${payload.failed_events || 0}.`
      )
      await loadCalendar()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Google sync failed.')
    } finally {
      setBusyAction('')
    }
  }

  if (loading) {
    return <LoadingState label="Loading personal calendar" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Personal workspace"
        title="Calendar and sync center"
        description="Export, import, and sync personal tasks with your external calendar while keeping due dates in one clear timeline."
      />

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Overview</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Personal schedule metrics</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={handleExport} className="btn-secondary" disabled={busyAction !== ''}>
              {busyAction === 'export' ? 'Exporting...' : 'Export .ics'}
            </button>
            <label className="btn-secondary cursor-pointer">
              <input type="file" accept=".ics,text/calendar" className="hidden" onChange={handleImportPreview} disabled={busyAction !== ''} />
              {busyAction === 'preview-import' ? 'Reading file...' : 'Import .ics'}
            </label>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <SummaryTile label="Tracked deadlines" value={events.length} note="Personal tasks in calendar feed" />
          <SummaryTile label="Due this week" value={dueThisWeekCount} note="Immediate focus range" />
          <SummaryTile
            label="Google sync"
            value={googleStatus?.connected ? 'Connected' : 'Not connected'}
            note={googleStatus?.calendar_name || 'No external calendar selected'}
          />
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Google Calendar</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Connection and sync</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use one-way sync from WorkNest to Google Calendar and choose exactly which calendar receives your tasks.
            </p>
          </div>
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
        </div>

        {googleStatus?.connected ? (
          <div className="mt-5 rounded-[20px] border border-slate-200 bg-[#fcfcfb] p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
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
            {googleStatus?.last_synced_at ? (
              <p className="mt-3 text-sm text-slate-500">Last synced {formatRelativeDate(googleStatus.last_synced_at)}.</p>
            ) : null}
          </div>
        ) : null}
      </section>

      {importPreview.length ? (
        <section className={`${panelClass} p-6 lg:p-7`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Import preview</p>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">Select events to import</h2>
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
                  {event.duplicate ? <p className="mt-1 text-xs font-medium text-amber-700">Already exists in your task list.</p> : null}
                </div>
              </label>
            ))}
          </div>
        </section>
      ) : null}

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Deadline timeline</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Your upcoming tasks</h2>
          </div>
          <Link to="/tasks" className="text-sm font-semibold text-emerald-700">
            Open my tasks
          </Link>
        </div>

        {events.length === 0 ? (
          <div className="mt-5">
            <EmptyState title="No personal deadlines yet" description="Create personal tasks with dates and they will appear in this calendar feed." />
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {Object.entries(groupedEvents).map(([date, items]) => (
              <article key={date} className="rounded-[20px] border border-slate-200 bg-[#fcfcfb] p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-base font-semibold text-slate-950">{date}</h3>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                    {items.length} items
                  </span>
                </div>
                <div className="mt-3 space-y-2">
                  {items.map((item) => (
                    <Link
                      key={item.task_id || `${item.title}-${item.due_date}`}
                      to={item.task_id ? `/tasks/${item.task_id}` : '/tasks'}
                      className="block rounded-xl border border-slate-200 bg-white px-3 py-3 transition-colors hover:bg-slate-50"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{formatRelativeDate(item.due_date)}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600">{toSentenceCase(item.status || 'scheduled')}</p>
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

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}
