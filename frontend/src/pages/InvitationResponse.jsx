import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import { hydrateCurrentUser, logout } from '../features/authSlice'
import { invitationsAPI, unwrapData } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, toSentenceCase } from '../utils/formatters'
import {
  deriveInvitationViewState,
  resolveInvitationSubtitle,
  resolveInvitationTitle,
} from '../utils/invitationState'
import { buildInvitationAuthHref, buildInvitationPath } from '../utils/invitationFlow'

const panelClass = 'rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_14px_34px_rgba(15,23,42,0.06)]'
const mutedPanel = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4'

export default function InvitationResponse() {
  const { token: routeToken = '' } = useParams()
  const [searchParams] = useSearchParams()
  const token = routeToken || searchParams.get('token') || ''
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { user } = useSelector((state) => state.auth)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState('')
  const [invitation, setInvitation] = useState(null)
  const [requestState, setRequestState] = useState('loading')

  const invitationPath = token ? buildInvitationPath(token) : '/invitations'
  const loginHref = buildInvitationAuthHref({ token, mode: 'login' })
  const registerHref = buildInvitationAuthHref({ token, mode: 'register' })

  useEffect(() => {
    const loadInvitation = async () => {
      if (!token) {
        setRequestState('missing')
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const response = await invitationsAPI.getInvitation(token)
        setInvitation(unwrapData(response))
        setRequestState('ready')
      } catch (error) {
        setRequestState(error.response?.status === 404 ? 'invalid' : 'error')
      } finally {
        setLoading(false)
      }
    }

    loadInvitation()
  }, [token])

  const invitationStatus = invitation?.status || 'pending'
  const invitedEmail = invitation?.email || ''
  const currentEmail = user?.email || ''
  const team = invitation?.team || null
  const isTeamArchived = Boolean(team?.is_archived)

  const derivedState = useMemo(
    () =>
      deriveInvitationViewState({
        requestState,
        invitation: invitation
          ? {
              ...invitation,
              status: invitationStatus,
              team: { ...(invitation.team || {}), is_archived: isTeamArchived },
            }
          : invitation,
        currentEmail,
      }),
    [currentEmail, invitation, invitationStatus, isTeamArchived, requestState]
  )

  const handleAction = async (intent) => {
    if (!token) return
    setActionLoading(intent)
    try {
      if (intent === 'accept') {
        await invitationsAPI.accept(token)
        try {
          await dispatch(hydrateCurrentUser()).unwrap()
        } catch (_error) {
          // The invitation is already accepted; a transient bootstrap refresh should not block access.
        }
        toast.success('Invitation accepted.')
        setInvitation((current) => (current ? { ...current, status: 'accepted' } : current))
        if (team?.id) {
          navigate(`/teams/${team.id}/overview`, { replace: true })
          return
        }
      } else {
        await invitationsAPI.decline(token)
        toast.success('Invitation declined.')
        setInvitation((current) => (current ? { ...current, status: 'declined' } : current))
      }
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to process the invitation right now.',
      })
      toast.error(parsed.message)
      if (error.response?.status === 403) {
        setRequestState('ready')
      }
    } finally {
      setActionLoading('')
    }
  }

  const handleSignOut = async () => {
    await dispatch(logout()).unwrap()
    navigate(loginHref)
  }

  const teamContinueUrl = team?.id ? `/teams/${team.id}/overview` : '/teams'

  return (
    <AuthShell
      title={resolveInvitationTitle(derivedState)}
      subtitle={resolveInvitationSubtitle(derivedState, invitation)}
      footer={
        <p>
          Need help?{' '}
          <a className="font-semibold text-emerald-700 hover:text-emerald-800" href="mailto:supportworknest@gmail.com">
            Contact support
          </a>
        </p>
      }
    >
      {loading ? (
        <div className={panelClass}>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Loading invitation</p>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            Checking the invite token, team details, and the account that should accept it.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {invitation ? (
            <div className={panelClass}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team invitation</p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-950">{team?.name || 'Workspace invite'}</h2>
                  <p className="mt-2 max-w-xl text-sm leading-7 text-slate-600">
                    {invitation.invited_by?.name || 'A teammate'} invited you to join as a {toSentenceCase(invitation.role)}.
                  </p>
                </div>
                <StatusPill status={derivedState} />
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <DetailCard label="Invited email" value={invitedEmail} />
                <DetailCard label="Role" value={toSentenceCase(invitation.role)} />
                <DetailCard label="Invited by" value={invitation.invited_by?.name || 'A teammate'} />
                <DetailCard label="Expires" value={formatDate(invitation.expires_at)} />
              </div>

              {invitation.custom_message ? (
                <div className={`${mutedPanel} mt-4`}>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Message from the inviter</p>
                  <p className="mt-3 text-sm leading-7 text-slate-700">{invitation.custom_message}</p>
                </div>
              ) : null}
            </div>
          ) : null}

          {derivedState === 'auth_required' ? (
            <div className={panelClass}>
              <p className="text-sm leading-7 text-slate-600">
                Sign in with <span className="font-semibold text-slate-950">{invitedEmail}</span> to review and accept this invitation.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <Link to={loginHref} className="btn-primary flex-1 justify-center">
                  Sign in to continue
                </Link>
                <Link to={registerHref} className="btn-secondary flex-1 justify-center">
                  Create account
                </Link>
              </div>
            </div>
          ) : null}

          {derivedState === 'mismatch' ? (
            <div className={panelClass}>
              <p className="text-sm leading-7 text-slate-600">
                This invitation was sent to <span className="font-semibold text-slate-950">{invitedEmail}</span>, but you are
                signed in as <span className="font-semibold text-slate-950">{currentEmail}</span>.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button type="button" onClick={handleSignOut} className="btn-primary flex-1 justify-center">
                  Sign out and continue
                </button>
                <Link to={teamContinueUrl} className="btn-secondary flex-1 justify-center">
                  Back to workspace
                </Link>
              </div>
            </div>
          ) : null}

          {derivedState === 'actionable' ? (
            <div className={panelClass}>
              <p className="text-sm leading-7 text-slate-600">
                You are signed in with the correct email. Accepting will add you to the team and take you into the workspace.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => handleAction('accept')}
                  disabled={actionLoading !== ''}
                  className="btn-primary flex-1 justify-center"
                >
                  {actionLoading === 'accept' ? 'Accepting...' : 'Accept invitation'}
                </button>
                <button
                  type="button"
                  onClick={() => handleAction('decline')}
                  disabled={actionLoading !== ''}
                  className="btn-secondary flex-1 justify-center"
                >
                  {actionLoading === 'decline' ? 'Declining...' : 'Decline invitation'}
                </button>
              </div>
            </div>
          ) : null}

          {derivedState === 'accepted' ? (
            <TerminalStateCard
              title="You’ve joined the team"
              description="Your membership is active now. Continue into the workspace to see tasks, members, and shared progress."
              actionLabel="Continue to team"
              actionHref={teamContinueUrl}
            />
          ) : null}

          {derivedState === 'declined' ? (
            <TerminalStateCard
              title="Invitation declined"
              description="This invitation has been declined. If you still need access, ask a team admin to send a new one."
              actionLabel="Open teams"
              actionHref="/teams"
            />
          ) : null}

          {['expired', 'revoked', 'archived', 'invalid', 'missing', 'error'].includes(derivedState) ? (
            <TerminalStateCard
              title={resolveInvitationTitle(derivedState)}
              description={resolveInvitationSubtitle(derivedState, invitation)}
              actionLabel={derivedState === 'invalid' || derivedState === 'missing' ? 'Go to login' : 'Open teams'}
              actionHref={derivedState === 'invalid' || derivedState === 'missing' ? '/login' : '/teams'}
            />
          ) : null}
        </div>
      )}
    </AuthShell>
  )
}

function DetailCard({ label, value }) {
  return (
    <div className={mutedPanel}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-900">{value || 'Not available'}</p>
    </div>
  )
}

function StatusPill({ status }) {
  const toneMap = {
    actionable: 'bg-emerald-50 text-emerald-700',
    auth_required: 'bg-slate-100 text-slate-700',
    mismatch: 'bg-amber-50 text-amber-700',
    accepted: 'bg-emerald-50 text-emerald-700',
    declined: 'bg-slate-100 text-slate-700',
    expired: 'bg-amber-50 text-amber-700',
    revoked: 'bg-rose-50 text-rose-700',
    archived: 'bg-slate-100 text-slate-700',
    invalid: 'bg-rose-50 text-rose-700',
    missing: 'bg-rose-50 text-rose-700',
    error: 'bg-rose-50 text-rose-700',
  }

  return (
    <span className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] ${toneMap[status] || toneMap.auth_required}`}>
      {toSentenceCase(status.replace('_', ' '))}
    </span>
  )
}

function TerminalStateCard({ title, description, actionLabel, actionHref }) {
  return (
    <div className={panelClass}>
      <h3 className="text-xl font-semibold text-slate-950">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-slate-600">{description}</p>
      <Link to={actionHref} className="btn-primary mt-5 inline-flex justify-center">
        {actionLabel}
      </Link>
    </div>
  )
}
