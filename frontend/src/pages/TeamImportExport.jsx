import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { tasksAPI, unwrapData } from '../services/api'

export default function TeamImportExport() {
  const { teamId } = useParams()
  const [preview, setPreview] = useState([])
  const [errors, setErrors] = useState([])
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setPreview([])
    setErrors([])
    setFile(null)
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

  if (loading) {
    return <LoadingState label="Preparing import/export tools" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Import / Export"
        title="Move task data safely"
        description="Bring CSV task lists into the workspace or export the current backlog for offline planning."
      />

      <section className="card fade-in">
        <h2 className="text-2xl font-bold text-emerald-950">Import tasks</h2>
        <p className="mt-2 text-sm text-soft">Upload a CSV and preview the rows before you commit them to the team.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input type="file" accept=".csv" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          <button type="button" onClick={handlePreview} className="btn-secondary">
            Preview CSV
          </button>
          <button type="button" onClick={handleImport} className="btn-primary">
            Import tasks
          </button>
        </div>
      </section>

      <section className="card fade-in">
        <h2 className="text-2xl font-bold text-emerald-950">Export tasks</h2>
        <p className="mt-2 text-sm text-soft">Download the team task list as a CSV snapshot.</p>
        <button type="button" onClick={handleExport} className="btn-secondary mt-4">
          Export CSV
        </button>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card fade-in">
          <h3 className="text-xl font-semibold text-emerald-950">Preview rows</h3>
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
        <div className="card fade-in">
          <h3 className="text-xl font-semibold text-emerald-950">Validation issues</h3>
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
      </section>
    </div>
  )
}

