import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { invitationsAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, toSentenceCase } from '../utils/formatters'
import { canManageInvitations, resolveMembershipRole } from '../utils/permissions'
import {
  canEditInvitation,
  canManageInvitePolicy,
  canRevokeOrResendInvitation,
  invitationFormSchema,
} from '../utils/invitationFlow'

const roleOptions = ['admin', 'manager', 'member']
const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'

export default function TeamInvitations() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [policySaving, setPolicySaving] = useState(false)
  const [team, setTeam] = useState(null)
  const [invitations, setInvitations] = useState([])
  const [showComposer, setShowComposer] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(invitationFormSchema),
    defaultValues: {
      email: '',
      role: 'member',
      custom_message: '',
    },
  })

  const loadInvitations = async () => {
    setLoading(true)
    try {
      const [teamResponse, invitationsResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        teamsAPI.getInvitations(teamId, { page_size: 100 }),
      ])
      setTeam(unwrapData(teamResponse))
      setInvitations(unwrapResults(invitationsResponse))
    } catch (error) {
      if (error.response?.status === 403) {
        navigate('/403')
        return
      }
      toast.error('Unable to load invitations right now.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInvitations()
  }, [teamId])

  useEffect(() => {
    if (searchParams.get('compose') === '1') {
      setShowComposer(true)
    }

    if (searchParams.get('created') === '1') {
      toast.info('Your team is ready. Invite teammates by email to start collaborating.')
      const nextParams = new URLSearchParams(searchParams)
      nextParams.delete('created')
      setSearchParams(nextParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const onSubmit = async (data) => {
    setSubmitting(true)
    try {
      await teamsAPI.inviteMember(teamId, data)
      toast.success('Invitation sent successfully.')
      reset({ email: '', role: data.role, custom_message: '' })
      setShowComposer(false)
      await loadInvitations()
    } catch (error) {
      const message = error.response?.data?.message || 'Unable to send invitation.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleResend = async (invitationId) => {
    try {
      await invitationsAPI.resend(invitationId)
      toast.success('Invitation resent.')
      await loadInvitations()
    } catch (error) {
      toast.error(error.response?.data?.message || 'Unable to resend invitation.')
    }
  }

  const handleRevoke = async (invitationId) => {
    try {
      await invitationsAPI.revoke(invitationId)
      toast.success('Invitation revoked.')
      await loadInvitations()
    } catch (error) {
      toast.error(error.response?.data?.message || 'Unable to revoke invitation.')
    }
  }

  const handleRoleChange = async (invitationId, role) => {
    try {
      await teamsAPI.updateInvitationRole(teamId, invitationId, { role })
      toast.success('Invitation role updated.')
      await loadInvitations()
    } catch (error) {
      toast.error(error.response?.data?.message || 'Unable to update invitation role.')
    }
  }

  if (loading || !team) {
    return <LoadingState label="Loading invitations" />
  }

  const pendingCount = invitations.filter((invitation) => invitation.status === 'pending').length
  const role = resolveMembershipRole(team) || 'member'
  const canInviteMembers = canManageInvitations({
    role,
    allowManagerInvites: team.allow_manager_invites,
  })
  const canEditPolicy = canManageInvitePolicy(role)

  const openComposer = () => {
    setShowComposer(true)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('compose', '1')
    setSearchParams(nextParams, { replace: true })
  }

  const closeComposer = () => {
    setShowComposer(false)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('compose')
    setSearchParams(nextParams, { replace: true })
  }

  const handlePolicyToggle = async () => {
    if (!canEditPolicy) return
    setPolicySaving(true)
    try {
      const response = await teamsAPI.updateTeam(teamId, {
        allow_manager_invites: !team.allow_manager_invites,
      })
      setTeam(unwrapData(response))
      toast.success('Invite policy updated.')
    } catch (error) {
      toast.error(error.response?.data?.message || 'Unable to update invite policy.')
    } finally {
      setPolicySaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.15fr,0.85fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Invitations</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Invite people to {team.name}</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
              Send secure email invitations, assign roles before access is granted, and keep every outstanding invite visible in one place.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {canInviteMembers ? (
                <button type="button" onClick={openComposer} className="btn-primary">
                  Invite member
                </button>
              ) : null}
              <button type="button" onClick={loadInvitations} className="btn-secondary">
                Refresh list
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <SummaryTile label="Pending" value={pendingCount} note="Awaiting response" />
            <SummaryTile label="Total invites" value={invitations.length} note="Across all statuses" />
            <SummaryTile
              label="Manager invites"
              value={team.allow_manager_invites ? 'On' : 'Off'}
              note={team.allow_manager_invites ? 'Managers can invite' : 'Admins only'}
            />
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Invite policy</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Control who can send workspace invitations</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Admins can always invite. Managers can only send invitations when this team policy is enabled.
            </p>
          </div>

          <div className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-slate-950">Allow manager invites</p>
                <p className="mt-1 text-sm text-slate-500">
                  {team.allow_manager_invites
                    ? 'Managers can invite new members and manage pending invitations.'
                    : 'Only admins can send and manage invitations.'}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={team.allow_manager_invites}
                disabled={!canEditPolicy || policySaving}
                onClick={handlePolicyToggle}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                  team.allow_manager_invites ? 'bg-emerald-600' : 'bg-slate-300'
                } ${!canEditPolicy ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                <span
                  className={`inline-block h-5 w-5 rounded-full bg-white transition-transform ${
                    team.allow_manager_invites ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            <p className="mt-4 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
              Your role: {toSentenceCase(role)}
            </p>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Invitation queue</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Pending, accepted, declined, and revoked invites</h2>
          </div>
          <p className="text-sm text-slate-500">{invitations.length} total records</p>
        </div>

        <div className="mt-5 space-y-3">
          {invitations.length === 0 ? (
            <EmptyState
              title="No invitations yet"
              description="Start by inviting a teammate with their role and an optional message."
              action={
                canInviteMembers ? (
                  <button type="button" onClick={openComposer} className="btn-primary">
                    Invite first member
                  </button>
                ) : null
              }
            />
          ) : (
            invitations.map((invitation) => {
              const isEditable = canInviteMembers && canEditInvitation(invitation)
              const canTakeActions = canInviteMembers && canRevokeOrResendInvitation(invitation)
              return (
                <div key={invitation.id} className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4 transition-colors hover:bg-white">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={invitation.status} />
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                          {toSentenceCase(invitation.role)}
                        </span>
                      </div>
                      <h3 className="mt-3 truncate text-base font-semibold text-slate-950">{invitation.email}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Invited by {invitation.invited_by?.name || 'Unknown'} on {formatDate(invitation.created_at)}.
                        Expires {formatDate(invitation.expires_at)}.
                      </p>
                      {invitation.custom_message ? (
                        <div className="mt-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-600">
                          {invitation.custom_message}
                        </div>
                      ) : null}
                    </div>

                    <div className="grid gap-3 sm:grid-cols-[180px,1fr] xl:min-w-[360px]">
                      <select
                        value={invitation.role}
                        onChange={(event) => handleRoleChange(invitation.id, event.target.value)}
                        disabled={!isEditable}
                        className="input-field"
                      >
                        {roleOptions.map((role) => (
                          <option key={role} value={role}>
                            {toSentenceCase(role)}
                          </option>
                        ))}
                      </select>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleResend(invitation.id)}
                          disabled={!canTakeActions}
                          className="btn-secondary"
                        >
                          Resend
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRevoke(invitation.id)}
                          disabled={!canTakeActions}
                          className="inline-flex items-center rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-700 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Revoke
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </section>

      {showComposer && canInviteMembers ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Invite member</p>
                <h3 className="mt-2 text-2xl font-semibold text-slate-950">Send a secure team invitation</h3>
                <p className="mt-2 text-sm leading-7 text-slate-600">
                  Invite a new or existing teammate by email, assign their role, and optionally include a short note.
                </p>
              </div>
              <button
                type="button"
                onClick={closeComposer}
                className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50"
              >
                <span className="text-lg leading-none">×</span>
              </button>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Email address</label>
                <input
                  {...register('email', { required: 'Email is required' })}
                  type="email"
                  className="input-field"
                  placeholder="teammate@company.com"
                />
                {errors.email ? <p className="mt-2 text-sm text-rose-600">{errors.email.message}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Role</label>
                <select {...register('role')} className="input-field">
                  {roleOptions.map((role) => (
                    <option key={role} value={role}>
                      {toSentenceCase(role)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">Custom message</label>
                <textarea
                  {...register('custom_message')}
                  className="input-field min-h-[140px]"
                  placeholder="Add a short note about what this team works on or what you want them to start with."
                />
                {errors.custom_message ? <p className="mt-2 text-sm text-rose-600">{errors.custom_message.message}</p> : null}
              </div>

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={closeComposer} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Sending invitation...' : 'Send invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}

function StatusBadge({ status }) {
  const toneMap = {
    pending: 'bg-amber-50 text-amber-700',
    accepted: 'bg-emerald-50 text-emerald-700',
    declined: 'bg-slate-100 text-slate-700',
    expired: 'bg-amber-50 text-amber-700',
    revoked: 'bg-rose-50 text-rose-700',
  }

  return (
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${toneMap[status] || toneMap.pending}`}>
      {toSentenceCase(status)}
    </span>
  )
}
