import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import { createTeam } from '../features/teamsSlice'
import { extractApiError } from '../utils/apiErrors'

const teamSetupSchema = z.object({
  name: z.string().trim().min(2, 'Team name must be at least 2 characters long.').max(160, 'Team name cannot exceed 160 characters.'),
  description: z.string().trim().max(2000, 'Description cannot exceed 2000 characters.').optional().default(''),
  allow_manager_invites: z.boolean().optional().default(false),
})

export default function TeamSetup() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { user } = useSelector((state) => state.auth)
  const [saving, setSaving] = useState(false)

  const {
    register,
    handleSubmit,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(teamSetupSchema),
    defaultValues: {
      name: '',
      description: '',
      allow_manager_invites: true,
    },
  })

  useEffect(() => {
    if (user?.account_type && user.account_type !== 'team') {
      navigate('/dashboard', { replace: true })
      return
    }
    if (user?.default_team_id) {
      navigate(`/teams/${user.default_team_id}/overview`, { replace: true })
    }
  }, [navigate, user?.account_type, user?.default_team_id])

  const onSubmit = async (data) => {
    setSaving(true)
    clearErrors()
    try {
      const team = await dispatch(
        createTeam({
          name: data.name.trim(),
          description: data.description?.trim() || '',
          allow_manager_invites: Boolean(data.allow_manager_invites),
        })
      ).unwrap()
      toast.success('Team workspace created. Invite your teammates next.')
      navigate(`/teams/${team.id}/invitations?compose=1&created=1`, { replace: true })
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to create your team right now.',
      })
      Object.entries(parsed.fieldErrors || {}).forEach(([field, message]) => {
        const value = Array.isArray(message) ? message[0] : message
        if (value) {
          setError(field, { message: value })
        }
      })
      setError('root', { message: parsed.message })
      toast.error(parsed.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Team setup"
        title="Create your first workspace"
        description="Start with a single workspace, invite teammates later, and build a shared execution rhythm."
      />

      <div className="grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
        <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4">
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-900">Team name</label>
            <input {...register('name')} className="input-field" placeholder="Growth Squad" />
            {errors.name ? <p className="mt-2 text-sm text-red-500">{errors.name.message}</p> : null}
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-900">Short description</label>
            <textarea
              {...register('description')}
              className="input-field min-h-[120px]"
              placeholder="What does this team own and deliver?"
            />
            {errors.description ? <p className="mt-2 text-sm text-red-500">{errors.description.message}</p> : null}
          </div>
          <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-600">
            <input type="checkbox" {...register('allow_manager_invites')} className="mt-1 h-4 w-4 rounded border-emerald-200" />
            <span>
              Allow managers to invite teammates after setup.
              <span className="mt-1 block text-xs text-slate-500">Admins can always manage invitations. You can change this policy later.</span>
            </span>
          </label>
          {errors.root ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{errors.root.message}</div>
          ) : null}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm text-slate-600">
            We will take you straight into invitations after setup so your workspace becomes collaborative immediately.
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Guided next step</span>
          </div>
          <button type="submit" disabled={saving} className="btn-primary w-full justify-center">
            {saving ? 'Creating workspace...' : 'Create team workspace'}
          </button>
        </form>

        <div className="space-y-4">
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-[0_12px_30px_rgba(15,23,42,0.06)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">What you get</p>
            <h3 className="mt-3 text-xl font-semibold text-slate-950">A shared collaboration hub</h3>
            <ul className="mt-4 space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Team dashboards with status, workload, and progress.
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Member assignments, roles, and invitations.
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-emerald-500" />
                Scheduled deadlines with timeline visibility.
              </li>
            </ul>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-[#fcfcfb] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Next up</p>
            <p className="mt-3 text-sm text-slate-600">
              After setup, we will open your invitation workspace so you can bring in teammates before planning the first shared tasks.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
