import { useCallback, useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { invitationsAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, toSentenceCase } from '../utils/formatters'
import { canManageInvitations, resolveMembershipRole } from '../utils/permissions'
import {
  buildInvitationPath,
  buildInviteLinkUrl,
  canEditInvitation,
  canManageInvitePolicy,
  canRevokeOrResendInvitation,
  invitationFormSchema,
  inviteLinkFormSchema,
  canCreateInviteLink,
} from '../utils/invitationFlow'

const roleOptions = ['admin', 'manager', 'member']
const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'

export default function TeamInvitations() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitMode, setSubmitMode] = useState('send')
  const [policySaving, setPolicySaving] = useState(false)
  const [team, setTeam] = useState(null)
  const [invitations, setInvitations] = useState([])
  const [inviteLinks, setInviteLinks] = useState([])
  const [showComposer, setShowComposer] = useState(false)
  const [showLinkComposer, setShowLinkComposer] = useState(false)
  const [pageError, setPageError] = useState('')
  const {
    register,
    handleSubmit,
    reset,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(invitationFormSchema),
    defaultValues: {
      email: '',
      role: 'member',
      custom_message: '',
    },
  })

  const {
    register: linkRegister,
    handleSubmit: linkHandleSubmit,
    reset: linkReset,
    setError: linkSetError,
    clearErrors: linkClearErrors,
    formState: { errors: linkErrors },
  } = useForm({
    resolver: zodResolver(inviteLinkFormSchema),
    defaultValues: {
      role: 'member',
      label: '',
      expires_at: null,
      max_uses: null,
    },
  })

  const loadInvitations = useCallback(async () => {
    setLoading(true)
    setPageError('')
    const [teamResult, invitationsResult, inviteLinksResult] = await Promise.allSettled([
      teamsAPI.getTeam(teamId),
      teamsAPI.getInvitations(teamId, { page_size: 100 }),
      invitationsAPI.getInviteLinks(teamId),
    ])

    if (teamResult.status === 'fulfilled') {
      setTeam(unwrapData(teamResult.value))
    } else {
      const parsed = extractApiError(teamResult.reason, {
        fallbackMessage: 'Unable to load this team workspace.',
      })
      if (parsed.status === 403) {
        navigate('/403')
        setLoading(false)
        return
      }
      setTeam(null)
      setInvitations([])
      setPageError(parsed.message)
      toast.error(parsed.message)
      setLoading(false)
      return
    }

    if (invitationsResult.status === 'fulfilled') {
      setInvitations(unwrapResults(invitationsResult.value))
    } else {
      const parsed = extractApiError(invitationsResult.reason, {
        fallbackMessage: 'Unable to load invitations right now.',
      })
      if (parsed.status === 403) {
        navigate('/403')
        setLoading(false)
        return
      }
      setInvitations([])
      setPageError(parsed.message)
      toast.error(parsed.message)
    }

    if (inviteLinksResult.status === 'fulfilled') {
      setInviteLinks(unwrapResults(inviteLinksResult.value))
    } else {
      setInviteLinks([])
    }

    setLoading(false)
  }, [navigate, teamId])

  useEffect(() => {
    loadInvitations()
  }, [loadInvitations])

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
    clearErrors()
    try {
      const response = await teamsAPI.inviteMember(teamId, data)
      const invitation = unwrapData(response) || {}
      const copied = submitMode === 'copy' ? await copyInviteLink(invitation) : false

      if (copied) {
        toast.success('Invite link generated and copied to clipboard.')
      } else {
        toast.success('Invitation sent successfully.')
      }
      reset({ email: '', role: data.role, custom_message: '' })
      setShowComposer(false)
      await loadInvitations()
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to send invitation.',
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
      setSubmitting(false)
      setSubmitMode('send')
    }
  }

  const handleResend = async (invitationId) => {
    try {
      await invitationsAPI.resend(invitationId)
      toast.success('Invitation resent.')
      await loadInvitations()
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to resend invitation.' }).message)
    }
  }

  const handleRevoke = async (invitationId) => {
    try {
      await invitationsAPI.revoke(invitationId)
      toast.success('Invitation revoked.')
      await loadInvitations()
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to revoke invitation.' }).message)
    }
  }

  const handleRoleChange = async (invitationId, role) => {
    try {
      await teamsAPI.updateInvitationRole(teamId, invitationId, { role })
      toast.success('Invitation role updated.')
      await loadInvitations()
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to update invitation role.' }).message)
    }
  }

  const onLinkSubmit = async (data) => {
    setSubmitting(true)
    linkClearErrors()
    try {
      const response = await invitationsAPI.createInviteLink(teamId, data)
      const inviteLink = unwrapData(response)
      if (inviteLink?.invite_link) {
        await navigator.clipboard.writeText(inviteLink.invite_link)
        toast.success('Invite link created and copied to clipboard.')
      } else {
        toast.success('Invite link created.')
      }
      linkReset({ role: 'member', label: '', expires_at: null, max_uses: null })
      setShowLinkComposer(false)
      await loadInvitations()
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to create invite link.',
      })
      Object.entries(parsed.fieldErrors || {}).forEach(([field, message]) => {
        const value = Array.isArray(message) ? message[0] : message
        if (value) {
          linkSetError(field, { message: value })
        }
      })
      linkSetError('root', { message: parsed.message })
      toast.error(parsed.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleLinkRevoke = async (linkId) => {
    try {
      await invitationsAPI.revokeInviteLink(teamId, linkId)
      toast.success('Invite link revoked.')
      await loadInvitations()
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to revoke invite link.' }).message)
    }
  }

  const handleLinkRegenerate = async (linkId) => {
    try {
      await invitationsAPI.regenerateInviteLink(teamId, linkId)
      toast.success('Invite link regenerated.')
      await loadInvitations()
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to regenerate invite link.' }).message)
    }
  }

  const handleLinkCopy = async (linkId) => {
    try {
      await invitationsAPI.copyInviteLink(teamId, linkId)
      toast.success('Link copied to clipboard.')
    } catch (error) {
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to copy link.' }).message)
    }
  }

  const sortedInvitations = useMemo(() => {
    const statusRank = { pending: 0, expired: 1, declined: 2, revoked: 3, accepted: 4 }
    return [...invitations].sort((left, right) => {
      const leftRank = statusRank[left.status] ?? 99
      const rightRank = statusRank[right.status] ?? 99
      if (leftRank !== rightRank) {
        return leftRank - rightRank
      }
      return new Date(right.created_at || 0).getTime() - new Date(left.created_at || 0).getTime()
    })
  }, [invitations])

  if (loading) {
    return <LoadingState label="Loading invitations" />
  }

  if (!team) {
    return (
      <div className="space-y-6">
        <EmptyState
          title="Invitations are unavailable"
          description={pageError || 'We could not load this team workspace right now.'}
          action={
            <button type="button" onClick={loadInvitations} className="btn-secondary">
              Retry
            </button>
          }
        />
      </div>
    )
  }
  const pendingCount = invitations.filter((invitation) => invitation.status === 'pending').length
  const role = resolveMembershipRole(team) || 'member'
  const isPersonalWorkspace = Boolean(team?.is_personal)
  const canInviteMembers = !isPersonalWorkspace && canManageInvitations({
    role,
    allowManagerInvites: team.allow_manager_invites,
  })
  const canEditPolicy = !isPersonalWorkspace && canManageInvitePolicy(role)
  const canCreateLink = !isPersonalWorkspace && canCreateInviteLink(role)

  const openComposer = () => {
    clearErrors()
    setShowComposer(true)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('compose', '1')
    setSearchParams(nextParams, { replace: true })
  }

  const closeComposer = () => {
    clearErrors()
    reset({ email: '', role: 'member', custom_message: '' })
    setShowComposer(false)
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('compose')
    setSearchParams(nextParams, { replace: true })
  }

  const openLinkComposer = () => {
    linkClearErrors()
    setShowLinkComposer(true)
  }

  const closeLinkComposer = () => {
    linkClearErrors()
    linkReset({ role: 'member', label: '', expires_at: null, max_uses: null })
    setShowLinkComposer(false)
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
      toast.error(extractApiError(error, { fallbackMessage: 'Unable to update invite policy.' }).message)
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

      {pageError ? (
        <section className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
          {pageError}
        </section>
      ) : null}

      {isPersonalWorkspace ? (
        <section className={`${panelClass} p-6 lg:p-7`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">Owner-only workspace</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">Personal workspaces stay private</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
            This workspace belongs to your individual account and does not support invitations. Create a shared team workspace when you are ready to collaborate with other people.
          </p>
          <div className="mt-5">
            <button type="button" onClick={() => navigate('/teams')} className="btn-secondary">
              Open teams
            </button>
          </div>
        </section>
      ) : null}

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
            sortedInvitations.map((invitation) => {
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

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Invite links</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Shareable invite links</h2>
          </div>
          <p className="text-sm text-slate-500">{inviteLinks.length} total links</p>
        </div>

        <div className="mt-5 space-y-3">
          {inviteLinks.length === 0 ? (
            <EmptyState
              title="No invite links yet"
              description="Create a shareable link to let people join your team with one click."
              action={
                canCreateLink ? (
                  <button type="button" onClick={openLinkComposer} className="btn-primary">
                    Create first link
                  </button>
                ) : null
              }
            />
          ) : (
            inviteLinks.map((link) => {
              const canAct = canCreateLink && link.status === 'active'
              return (
                <div key={link.id} className="rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4 transition-colors hover:bg-white">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <LinkStatusBadge status={link.status} />
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                          {toSentenceCase(link.role)}
                        </span>
                      </div>
                      <h3 className="mt-3 truncate text-base font-semibold text-slate-950">
                        {link.label || 'Unnamed link'}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Created {formatDate(link.created_at)}.
                        {link.expires_at ? ` Expires ${formatDate(link.expires_at)}.` : ' No expiry.'}
                        {link.max_uses ? ` Max ${link.max_uses} uses.` : ''}
                      </p>
                      <p className="mt-1 text-sm text-slate-500">
                        Used {link.current_uses} {link.max_uses ? `/ ${link.max_uses}` : ''} times
                      </p>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-[140px,1fr]">
                      <button
                        type="button"
                        onClick={() => handleLinkCopy(link.id)}
                        disabled={!canAct}
                        className="btn-secondary"
                      >
                        Copy link
                      </button>

                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleLinkRegenerate(link.id)}
                          disabled={!canAct}
                          className="btn-secondary"
                        >
                          Regenerate
                        </button>
                        <button
                          type="button"
                          onClick={() => handleLinkRevoke(link.id)}
                          disabled={!canAct}
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

        {canCreateLink && inviteLinks.length > 0 && (
          <div className="mt-5">
            <button type="button" onClick={openLinkComposer} className="btn-secondary">
              Create new link
            </button>
          </div>
        )}
      </section>

      {showComposer && canInviteMembers ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emerald-950/10 px-4 backdrop-blur-sm">
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
                {errors.role ? <p className="mt-2 text-sm text-rose-600">{errors.role.message}</p> : null}
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

              {errors.root ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errors.root.message}
                </div>
              ) : null}

              <div className="flex flex-wrap justify-end gap-3">
                <button type="button" onClick={closeComposer} className="btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  onClick={() => setSubmitMode('copy')}
                  disabled={submitting}
                  className="btn-secondary"
                >
                  {submitting && submitMode === 'copy' ? 'Generating link...' : 'Generate link & copy'}
                </button>
                <button
                  type="submit"
                  onClick={() => setSubmitMode('send')}
                  disabled={submitting}
                  className="btn-primary"
                >
                  {submitting && submitMode === 'send' ? 'Sending invitation...' : 'Send invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}

async function copyInviteLink(invitation) {
  const inviteLink = String(invitation?.invitation_link || '').trim()
  const token = String(invitation?.token || '').trim()
  const fallbackLink = token ? `${window.location.origin}${buildInvitationPath(token)}` : ''
  const linkToCopy = inviteLink || fallbackLink
  if (!linkToCopy) return false

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(linkToCopy)
      return true
    }
  } catch (_error) {
    // Fallback below.
  }

  const textArea = document.createElement('textarea')
  textArea.value = linkToCopy
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.opacity = '0'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  const copied = document.execCommand('copy')
  document.body.removeChild(textArea)
  return copied
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

function LinkStatusBadge({ status }) {
  const toneMap = {
    active: 'bg-emerald-50 text-emerald-700',
    expired: 'bg-amber-50 text-amber-700',
    revoked: 'bg-rose-50 text-rose-700',
    maxed_out: 'bg-slate-100 text-slate-700',
  }

  return (
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${toneMap[status] || toneMap.active}`}>
      {toSentenceCase(status || 'active')}
    </span>
  )
}
