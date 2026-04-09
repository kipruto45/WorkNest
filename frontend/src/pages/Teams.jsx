import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import EmptyState from '../components/EmptyState'
import { fetchTeams, createTeam } from '../features/teamsSlice'
import { teamsAPI } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { toSentenceCase } from '../utils/formatters'

export default function Teams() {
  const [showModal, setShowModal] = useState(false)
  const [pinningTeamId, setPinningTeamId] = useState('')
  const { teams, loading } = useSelector((state) => state.teams)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm()

  useEffect(() => {
    dispatch(fetchTeams())
  }, [dispatch])

  const sortedTeams = [...teams].sort((left, right) => {
    if (left.is_pinned === right.is_pinned) {
      return left.name.localeCompare(right.name)
    }
    return left.is_pinned ? -1 : 1
  })

  const onSubmit = async (data) => {
    clearErrors()
    try {
      const team = await dispatch(
        createTeam({
          name: data.name.trim(),
          description: data.description?.trim() || '',
        })
      ).unwrap()
      await dispatch(fetchTeams()).unwrap()
      toast.success('Team created. Invite your teammates by email next.')
      setShowModal(false)
      reset()
      navigate(`/teams/${team.id}/invitations?compose=1&created=1`)
    } catch (error) {
      const apiError =
        typeof error === 'string'
          ? { message: error, fieldErrors: {} }
          : error?.fieldErrors || error?.status
            ? error
            : extractApiError(error, {
                fallbackMessage: 'Failed to create team.',
                forbiddenMessage: 'You are not authorized to create a team.',
                serverMessage: 'Server error while creating team.',
              })

      Object.entries(apiError.fieldErrors || {}).forEach(([field, value]) => {
        const message = Array.isArray(value) ? value[0] : value
        if (field === 'name' || field === 'description') {
          setError(field, { type: 'server', message })
        }
      })

      setError('root', { type: 'server', message: apiError.message })
      console.error('create_team_failed', {
        location: 'teams',
        status: apiError.status,
        requestId: apiError.requestId,
        errors: apiError.errors,
      })
      toast.error(apiError.message)
    }
  }

  const handleOpenModal = () => {
    clearErrors()
    setShowModal(true)
  }

  const handleCloseModal = () => {
    clearErrors()
    reset()
    setShowModal(false)
  }

  const handleTogglePin = async (teamId) => {
    setPinningTeamId(teamId)
    try {
      await teamsAPI.togglePin(teamId)
      await dispatch(fetchTeams()).unwrap()
      toast.success('Team pin updated.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update pin right now.')
    } finally {
      setPinningTeamId('')
    }
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Teams"
        title="Workspace collection"
        description="Every active team, ready for drill-down into overview, board, analytics, members, and invitations."
        stats={[
          { label: 'Active teams', value: teams.length, caption: 'Across your account' },
          { label: 'Visible roles', value: new Set(teams.map((team) => team.my_role)).size || 0, caption: 'Role spread' },
          { label: 'Largest team', value: Math.max(0, ...teams.map((team) => team.member_count || 0)), caption: 'Members in one workspace' },
        ]}
        spotlight={{
          eyebrow: 'Workspace map',
          title: 'Each team should feel like a product surface.',
          description: 'Overview, board, analytics, activity, invitations, and member controls create a stronger demo story than a flat list.',
          points: [
            { label: 'Boards ready', value: teams.length },
            { label: 'Next action', value: teams.length ? 'Open an overview' : 'Create first team' },
          ],
        }}
        actions={
          <button type="button" onClick={handleOpenModal} className="btn-primary">
            Create team
          </button>
        }
      />

      {loading ? (
        <div className="card text-center text-soft">Loading teams...</div>
      ) : teams.length === 0 ? (
        <EmptyState
          title="No teams yet"
          description="Create your first team to start collaborating on boards, tasks, member roles, and shared delivery metrics."
          action={
            <button type="button" onClick={handleOpenModal} className="btn-primary">
              Start with a team
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sortedTeams.map((team) => (
            <div key={team.id} className="feature-tile fade-in">
              <div className="flex items-center justify-between gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 text-xl font-bold text-white">
                  {team.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex items-center gap-2">
                  {team.is_pinned ? <div className="stat-chip">Pinned</div> : null}
                  <div className="stat-chip">{toSentenceCase(team.my_role || 'member')}</div>
                </div>
              </div>
              <h3 className="mt-5 text-2xl font-bold text-emerald-950">{team.name}</h3>
              <p className="mt-2 min-h-[48px] text-sm leading-6 text-soft">
                {team.description || 'No description added yet. Use the overview page to shape this workspace.'}
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="metric-strip">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Members</p>
                    <p className="mt-2 text-2xl font-bold text-emerald-950">{team.member_count}</p>
                  </div>
                </div>
                <div className="metric-strip">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Owner</p>
                    <p className="mt-2 text-base font-bold text-emerald-950">{team.created_by?.name || 'Unknown'}</p>
                  </div>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link to={`/teams/${team.id}/overview`} className="btn-primary">
                  Overview
                </Link>
                <Link to={`/teams/${team.id}`} className="btn-secondary">
                  Board
                </Link>
                <Link to={`/teams/${team.id}/invitations?compose=1`} className="btn-secondary">
                  Invite
                </Link>
                <Link to={`/teams/${team.id}/analytics`} className="btn-ghost">
                  Analytics
                </Link>
                <button
                  type="button"
                  onClick={() => handleTogglePin(team.id)}
                  disabled={pinningTeamId === team.id}
                  className="btn-ghost"
                >
                  {pinningTeamId === team.id ? 'Updating...' : team.is_pinned ? 'Unpin' : 'Pin'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/30 px-4 backdrop-blur-sm">
          <div className="page-shell w-full max-w-xl p-6 md:p-8">
            <h3 className="font-display text-3xl font-bold text-emerald-950">Create a new team</h3>
            <p className="mt-2 text-sm leading-6 text-soft">Start a workspace for shared task planning, invites, and delivery tracking.</p>

            <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Team name</label>
                <input
                  {...register('name', {
                    required: 'Team name is required.',
                    validate: (value) => value.trim().length > 0 || 'Team name is required.',
                  })}
                  className="input-field"
                  placeholder="Growth Squad"
                />
                {errors.name ? <p className="mt-2 text-sm text-red-500">{errors.name.message}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Description</label>
                <textarea {...register('description')} className="input-field min-h-[140px]" placeholder="What does this team own?" />
                {errors.description ? <p className="mt-2 text-sm text-red-500">{errors.description.message}</p> : null}
              </div>

              {errors.root ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {errors.root.message}
                </div>
              ) : null}

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={handleCloseModal} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={isSubmitting} className="btn-primary">
                  {isSubmitting ? 'Creating...' : 'Create team'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
