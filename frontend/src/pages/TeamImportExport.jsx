import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { tasksAPI, teamsAPI, unwrapData } from '../services/api'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function TeamImportExport() {
  const { teamId } = useParams()
  const [team, setTeam] = useState(null)
  const [preview, setPreview] = useState([])
  const [errors, setErrors] = useState([])
  const [file, setFile] = useState(null)
  const [initialLoading, setInitialLoading] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setPreview([])
    setErrors([])
    setFile(null)
    const loadTeam = async () => {
      if (!teamId) {
        setInitialLoading(false)
        setTeam(null)
        return
      }
      setInitialLoading(true)
      try {
        const response = await teamsAPI.getTeam(teamId)
        setTeam(unwrapData(response))
      } catch (error) {
        setTeam(null)
      } finally {
        setInitialLoading(false)
      }
    }
    loadTeam()
  }, [teamId])

  const handlePreview = async () => {
    if (!file) {
      toast.error('Select a CSV file to preview.')
      return
    }
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('team_id', teamId)
      formData.append('file', file)
      const response = await tasksAPI.importTasks(formData, { dry_run: true })
      const payload = unwrapData(response)
      setPreview(payload?.rows || [])
      setErrors(payload?.errors || [])
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to generate preview.')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file) {
      toast.error('Select a CSV file to import.')
      return
    }
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('team_id', teamId)
      formData.append('file', file)
      const response = await tasksAPI.importTasks(formData)
      const payload = unwrapData(response)
      toast.success(`Imported ${payload?.created || 0} tasks.`)
      setPreview([])
      setErrors(payload?.errors || [])
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to import tasks.')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    setLoading(true)
    try {
      const response = await tasksAPI.exportTasks({ team: teamId })
      const payload = unwrapData(response)
      const blob = new Blob([payload?.content || ''], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = payload?.filename || 'tasks-export.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      toast.success('CSV export ready.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to export tasks.')
    } finally {
      setLoading(false)
    }
  }

  if (!teamId) {
    return <EmptyState title="No team selected" description="Choose a team workspace to import or export tasks." />
  }

  if (initialLoading) {
    return <LoadingState label="Loading import and export tools" />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Import / Export</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {(team?.name || 'Team')} data transfer center
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Validate CSV rows before import, review issues early, and export an exact snapshot of current team tasks.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}`} className="btn-secondary">
                Team tasks
              </Link>
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Selected file" value={file?.name || 'None'} note="CSV file to process" />
              <SummaryTile label="Preview rows" value={preview.length} note="Rows parsed in dry run" />
              <SummaryTile label="Validation issues" value={errors.length} note="Rows requiring fixes" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <h2 className="text-xl font-semibold text-slate-950">Import tasks</h2>
        <p className="mt-2 text-sm text-slate-600">Upload a CSV and run a dry-run preview before importing to production data.</p>
        <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
          <input
            type="file"
            accept=".csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 md:max-w-[420px]"
          />
          <button type="button" onClick={handlePreview} className="btn-secondary" disabled={loading}>
            {loading ? 'Working...' : 'Preview CSV'}
          </button>
          <button type="button" onClick={handleImport} className="btn-primary" disabled={loading}>
            {loading ? 'Working...' : 'Import tasks'}
          </button>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <h2 className="text-xl font-semibold text-slate-950">Export tasks</h2>
        <p className="mt-2 text-sm text-slate-600">Download the current team backlog as a CSV snapshot for external analysis.</p>
        <button type="button" onClick={handleExport} className="btn-secondary mt-4" disabled={loading}>
          {loading ? 'Preparing...' : 'Export CSV'}
        </button>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="grid gap-4 lg:grid-cols-2">
        <div className={`${cardClass} p-5`}>
          <h3 className="text-xl font-semibold text-slate-950">Preview rows</h3>
          {preview.length === 0 ? (
            <EmptyState title="No preview yet" description="Upload a CSV and run preview to see task rows." />
          ) : (
            <div className="mt-4 space-y-3">
              {preview.map((row, index) => (
                <div key={`${row.title}-${index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <p className="text-sm font-semibold text-slate-900">{row.title}</p>
                  <p className="text-xs text-slate-500">{row.status} • {row.priority}</p>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className={`${cardClass} p-5`}>
          <h3 className="text-xl font-semibold text-slate-950">Validation issues</h3>
          {errors.length === 0 ? (
            <EmptyState title="No errors" description="Any CSV validation errors will appear here." />
          ) : (
            <div className="mt-4 space-y-3">
              {errors.map((error, index) => (
                <div key={`${error.row}-${index}`} className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Row {error.row}: {error.error}
                </div>
              ))}
            </div>
          )}
        </div>
        </div>
      </section>
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 truncate text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}
