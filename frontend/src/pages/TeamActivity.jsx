import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import Forbidden from './Forbidden'
import { auditLogsAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function TeamActivity() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [accessDenied, setAccessDenied] = useState(false)
  const [pageError, setPageError] = useState('')
  const [team, setTeam] = useState(null)
  const [logs, setLogs] = useState([])
  const [query, setQuery] = useState('')
  const [actionFilter, setActionFilter] = useState('all')

  const loadLogs = useCallback(async () => {
    setLoading(true)
    setAccessDenied(false)
    setPageError('')
    try {
      const [teamResponse, logsResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        auditLogsAPI.getForTeam(teamId, { page_size: 120 }),
      ])
      setTeam(unwrapData(teamResponse))
      setLogs(unwrapResults(logsResponse))
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to load the team activity timeline.',
      })
      if (parsed.status === 403) {
        setAccessDenied(true)
      } else {
        setPageError(parsed.message)
        toast.error(parsed.message)
      }
      setTeam(null)
      setLogs([])
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  const actionOptions = useMemo(() => {
    const unique = new Set(logs.map((log) => String(log.action || '').toLowerCase()).filter(Boolean))
    return [...unique]
  }, [logs])

  const filteredLogs = useMemo(() => {
    const input = query.trim().toLowerCase()
    return logs.filter((log) => {
      const action = String(log.action || '').toLowerCase()
      if (actionFilter !== 'all' && action !== actionFilter) return false
      if (!input) return true
      const haystack = `${log.target_repr || ''} ${log.actor?.name || ''} ${log.target_type || ''} ${log.action || ''}`
      return haystack.toLowerCase().includes(input)
    })
  }, [actionFilter, logs, query])

  const recentActors = new Set(filteredLogs.map((log) => log.actor?.id).filter(Boolean)).size

  if (loading) {
    return <LoadingState label="Loading team activity" />
  }

  if (accessDenied) {
    return <Forbidden />
  }

  if (!team) {
    return (
      <EmptyState
        title="Team activity is unavailable"
        description={pageError || 'We could not load this team workspace right now.'}
        action={
          <button type="button" onClick={loadLogs} className="btn-secondary">
            Retry
          </button>
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Activity log</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} team timeline</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Review task updates, membership changes, and workspace actions in a structured chronological stream.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Log entries" value={filteredLogs.length} note="In current filter scope" />
              <SummaryTile label="Unique actors" value={recentActors} note="People making changes" />
              <SummaryTile label="Action types" value={actionOptions.length} note="Kinds of events" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-600">
            Search by actor, action, or target
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-field mt-2"
              placeholder="Search timeline"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Filter by action
            <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} className="input-field mt-2">
              <option value="all">All actions</option>
              {actionOptions.map((action) => (
                <option key={action} value={action}>
                  {toSentenceCase(action)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {filteredLogs.length === 0 ? (
        <EmptyState
          title="No activity in this filter"
          description="Try broadening your filters to see the full team timeline."
        />
      ) : (
        <section className={`${panelClass} p-6 lg:p-7`}>
          <div className="relative space-y-3 pl-4">
            <div className="absolute left-[11px] top-0 h-full w-px bg-emerald-200" />
            {filteredLogs.map((log) => (
              <article key={log.id} className={`${cardClass} relative p-4`}>
                <div className="absolute -left-[24px] top-6 h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                        {toSentenceCase(log.action || 'update')}
                      </span>
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
                        {toSentenceCase(log.target_type || 'resource')}
                      </span>
                    </div>
                    <h3 className="mt-3 text-base font-semibold text-slate-900">{log.target_repr || 'Workspace item'}</h3>
                    <p className="mt-1 text-sm text-slate-600">
                      {log.actor?.name || 'System'} | {formatDate(log.created_at)}
                    </p>
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    {formatRelativeDate(log.created_at)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
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
