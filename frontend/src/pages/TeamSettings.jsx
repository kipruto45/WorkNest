import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import Forbidden from './Forbidden'
import { teamsAPI, unwrapData } from '../services/api'
import { resolveMembershipRole } from '../utils/permissions'
import { formatDate, toSentenceCase } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function TeamSettings() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [saving, setSaving] = useState(false)
  const [archiving, setArchiving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm({
    defaultValues: {
      name: '',
      description: '',
      allow_manager_invites: false,
    },
  })

  useEffect(() => {
    const loadTeam = async () => {
      setLoading(true)
      try {
        const response = await teamsAPI.getTeam(teamId)
        const nextTeam = unwrapData(response)
        setTeam(nextTeam)
        reset({
          name: nextTeam?.name || '',
          description: nextTeam?.description || '',
          allow_manager_invites: Boolean(nextTeam?.allow_manager_invites),
        })
      } catch (error) {
        if (error.response?.status === 404) {
          navigate('/teams')
          return
        }
        toast.error(error?.response?.data?.message || 'Unable to load team settings right now.')
      } finally {
        setLoading(false)
      }
    }

    loadTeam()
  }, [navigate, reset, teamId])

  if (loading) {
    return <LoadingState label="Loading team settings" />
  }

  if (!team) {
    return <EmptyState title="Team unavailable" description="This workspace could not be loaded." />
  }

  const currentRole = resolveMembershipRole(team)
  const canManageWorkspace = currentRole === 'admin'

  if (!canManageWorkspace) {
    return <Forbidden />
  }

  const onSubmit = async (data) => {
    if (!canManageWorkspace) {
      toast.error('Only team admins can update workspace settings.')
      return
    }

    setSaving(true)
    try {
      const response = await teamsAPI.updateTeam(teamId, data)
      const updatedTeam = unwrapData(response)
      setTeam(updatedTeam)
      reset({
        name: updatedTeam?.name || '',
        description: updatedTeam?.description || '',
        allow_manager_invites: Boolean(updatedTeam?.allow_manager_invites),
      })
      toast.success('Workspace settings updated.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to save workspace settings.')
    } finally {
      setSaving(false)
    }
  }

  const handleArchive = async () => {
    if (!canManageWorkspace) {
      toast.error('Only team admins can archive a workspace.')
      return
    }
    if (!window.confirm('Archive this team? Active workspace pages will no longer stay available.')) {
      return
    }
    setArchiving(true)
    try {
      await teamsAPI.archiveTeam(teamId)
      toast.success('Team archived successfully.')
      navigate('/archive')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to archive this team.')
    } finally {
      setArchiving(false)
    }
  }

  const handleDelete = async () => {
    if (!canManageWorkspace) {
      toast.error('Only team admins can delete a workspace.')
      return
    }
    if (!window.confirm('Delete this archived team permanently? This cannot be undone.')) {
      return
    }
    setDeleting(true)
    try {
      await teamsAPI.deleteTeam(teamId)
      toast.success('Archived team deleted.')
      navigate('/teams')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Archive the team before deleting it permanently.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.12fr,0.88fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team settings</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} workspace controls</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Manage team profile, invitation permissions, and workspace lifecycle controls from one secure and structured page.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
              {canManageWorkspace ? (
                <button type="submit" form="team-settings-form" className="btn-primary" disabled={isSubmitting || saving}>
                  {saving || isSubmitting ? 'Saving changes...' : 'Save settings'}
                </button>
              ) : null}
            </div>
          </div>

          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Role" value={toSentenceCase(currentRole || 'member')} note={canManageWorkspace ? 'Admin controls enabled' : 'Read-only view'} />
              <SummaryTile label="Members" value={team.member_count || 0} note="Current collaborators" />
              <SummaryTile label="Invite policy" value={team.allow_manager_invites ? 'Managers can invite' : 'Admins only'} note="Workspace membership control" />
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.12fr,0.88fr]">
        <section className={`${panelClass} p-6 lg:p-7`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workspace profile</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">Name, description, and invite behavior</h2>
          <form id="team-settings-form" onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-4">
            <label className="block text-sm font-semibold text-slate-900">
              Team name
              <input {...register('name')} disabled={!canManageWorkspace} className="input-field mt-2" />
            </label>
            <label className="block text-sm font-semibold text-slate-900">
              Description
              <textarea {...register('description')} disabled={!canManageWorkspace} className="input-field mt-2 min-h-[140px]" />
            </label>
            <label className="flex items-start gap-3 rounded-[20px] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-700">
              <input type="checkbox" {...register('allow_manager_invites')} disabled={!canManageWorkspace} className="mt-1 h-4 w-4 rounded border-slate-300" />
              <span>
                <strong>Allow manager invites</strong>
                <span className="mt-1 block text-xs text-slate-500">
                  When enabled, managers can send and manage invitations without admin intervention.
                </span>
              </span>
            </label>
          </form>
        </section>

        <section className={`${panelClass} p-6 lg:p-7`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workspace summary</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">Lifecycle and policy snapshot</h2>

          <div className="mt-5 grid gap-3">
            <SummaryBlock label="Created" value={formatDate(team.created_at)} />
            <SummaryBlock label="Last updated" value={formatDate(team.updated_at)} />
            <SummaryBlock label="Archive state" value={team.is_archived ? 'Archived workspace' : 'Active workspace'} />
            {team.archived_at ? <SummaryBlock label="Archived on" value={formatDate(team.archived_at)} /> : null}
          </div>

          <div className="mt-5 grid gap-3">
            <Link to={`/teams/${teamId}/automation`} className={`${cardClass} flex items-start justify-between gap-3 p-4 transition-colors hover:bg-white`}>
              <div>
                <p className="text-sm font-semibold text-slate-900">Automation rules</p>
                <p className="mt-1 text-sm text-slate-500">Configure workflow triggers and actions.</p>
              </div>
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Open</span>
            </Link>
            <Link to={`/teams/${teamId}/import-export`} className={`${cardClass} flex items-start justify-between gap-3 p-4 transition-colors hover:bg-white`}>
              <div>
                <p className="text-sm font-semibold text-slate-900">Import / Export</p>
                <p className="mt-1 text-sm text-slate-500">Move workspace data safely in or out.</p>
              </div>
              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Open</span>
            </Link>
          </div>
        </section>
      </div>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">Danger zone</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">Archive or permanently remove workspace</h2>
        <p className="mt-2 text-sm text-slate-600">
          Archive first to prevent active usage. Permanent deletion is only available for archived workspaces and cannot be undone.
        </p>

        <div className="mt-5 flex flex-wrap gap-3">
          {canManageWorkspace ? (
            <>
              {!team.is_archived ? (
                <button type="button" onClick={handleArchive} disabled={archiving} className="btn-secondary">
                  {archiving ? 'Archiving workspace...' : 'Archive workspace'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="inline-flex items-center justify-center rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-100"
                >
                  {deleting ? 'Deleting workspace...' : 'Delete archived workspace'}
                </button>
              )}
            </>
          ) : (
            <span className="rounded-xl border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-600">Admin access required</span>
          )}
        </div>
      </section>
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}

function SummaryBlock({ label, value }) {
  return (
    <div className={`${cardClass} p-4`}>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-base font-semibold text-slate-900">{value}</p>
    </div>
  )
}
