import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHero from '../components/PageHero'
import { teamsAPI, unwrapData } from '../services/api'
import { canManageMembers, resolveMembershipRole } from '../utils/permissions'
import { formatDate, toSentenceCase } from '../utils/formatters'

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
  const canManageWorkspace = canManageMembers(currentRole)

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
      <PageHero
        eyebrow="Team Settings"
        title={`${team.name} workspace settings`}
        description="Review ownership, invitation policy, naming, and lifecycle controls for this team workspace."
        stats={[
          { label: 'Role', value: toSentenceCase(currentRole || 'member'), caption: 'Your workspace access' },
          { label: 'Members', value: team.member_count || 0, caption: 'Current collaborators' },
          { label: 'Invite policy', value: team.allow_manager_invites ? 'Managers can invite' : 'Admins only', caption: 'Current policy' },
        ]}
        actions={
          <>
            <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
              Back to overview
            </Link>
            {canManageWorkspace ? (
              <button type="submit" form="team-settings-form" className="btn-primary" disabled={isSubmitting || saving}>
                {saving || isSubmitting ? 'Saving changes...' : 'Save settings'}
              </button>
            ) : null}
          </>
        }
        aside={canManageWorkspace ? 'Admin controls enabled' : 'Read-only for your current role'}
      />

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Workspace profile</h2>
          <p className="mt-2 text-sm text-soft">Keep the team identity and invite policy current across the real backend workspace.</p>

          <form id="team-settings-form" onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Team name</label>
              <input {...register('name')} disabled={!canManageWorkspace} className="input-field" />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Description</label>
              <textarea {...register('description')} disabled={!canManageWorkspace} className="input-field min-h-[160px]" />
            </div>

            <label className="feature-tile flex items-start justify-between gap-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">Allow manager invites</p>
                <p className="mt-1 text-sm text-soft">Permit managers to send and manage invitations without admin involvement.</p>
              </div>
              <input
                type="checkbox"
                {...register('allow_manager_invites')}
                disabled={!canManageWorkspace}
                className="mt-1 h-5 w-5 rounded border-emerald-200"
              />
            </label>
          </form>
        </section>

        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Workspace lifecycle</h2>
          <p className="mt-2 text-sm text-soft">Archive a finished workspace first, then delete it permanently if needed.</p>

          <div className="mt-6 grid gap-4">
            <div className="feature-tile">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Created</p>
              <p className="mt-3 text-lg font-bold text-emerald-950">{formatDate(team.created_at)}</p>
            </div>
            <div className="feature-tile">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Last updated</p>
              <p className="mt-3 text-lg font-bold text-emerald-950">{formatDate(team.updated_at)}</p>
            </div>
            <div className="feature-tile">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Archive state</p>
              <p className="mt-3 text-lg font-bold text-emerald-950">{team.is_archived ? 'Archived' : 'Active workspace'}</p>
              {team.archived_at ? <p className="mt-2 text-sm text-soft">Archived {formatDate(team.archived_at)}</p> : null}
            </div>
          </div>

          <div className="mt-6 grid gap-3">
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
              <div className="rounded-[24px] border border-slate-200 bg-slate-50/70 p-4 text-sm text-slate-600">
                Only team admins can change workspace settings, archive a team, or delete an archived workspace.
              </div>
            )}
          </div>
        </section>

        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Workflow tools</h2>
          <p className="mt-2 text-sm text-soft">Jump to automation rules and data import/export when you need deeper control.</p>
          <div className="mt-6 grid gap-3">
            <Link to={`/teams/${teamId}/automation`} className="feature-tile flex items-start justify-between gap-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">Automation rules</p>
                <p className="mt-1 text-sm text-soft">Define triggers and actions for your workflow.</p>
              </div>
              <span className="text-xs font-semibold text-emerald-700">Open</span>
            </Link>
            <Link to={`/teams/${teamId}/import-export`} className="feature-tile flex items-start justify-between gap-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">Import / Export</p>
                <p className="mt-1 text-sm text-soft">Move CSV task data in or out safely.</p>
              </div>
              <span className="text-xs font-semibold text-emerald-700">Open</span>
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}
