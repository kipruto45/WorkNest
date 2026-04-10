import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import { hydrateCurrentUser } from '../features/authSlice'
import { invitationsAPI, unwrapData } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, toSentenceCase } from '../utils/formatters'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig'
import { buildInviteLinkAuthHref } from '../utils/invitationFlow'

const panelClass = 'rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_14px_34px_rgba(15,23,42,0.06)]'
const mutedPanel = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4'

function rememberMemberOnboarding(teamId) {
  if (!teamId || typeof window === 'undefined') return
  try {
    const raw = localStorage.getItem(CLIENT_STORAGE_KEYS.memberOnboardingTeams)
    const parsed = raw ? JSON.parse(raw) : {}
    const next = parsed && typeof parsed === 'object' ? parsed : {}
    next[String(teamId)] = true
    localStorage.setItem(CLIENT_STORAGE_KEYS.memberOnboardingTeams, JSON.stringify(next))
  } catch (_error) {
    // Ignore storage failures.
  }
}

function deriveInviteLinkState({ requestState, inviteLink }) {
  if (requestState === 'missing') return 'missing'
  if (requestState === 'invalid') return 'invalid'
  if (requestState === 'error') return 'error'
  if (!inviteLink) return 'loading'
  if (inviteLink?.team?.is_archived) return 'archived'
  if (inviteLink?.status === 'revoked' || inviteLink?.revoked_at) return 'revoked'
  if (inviteLink?.status === 'expired' || inviteLink?.is_expired) return 'expired'
  if (inviteLink?.status === 'maxed_out' || inviteLink?.is_maxed_out) return 'maxed_out'
  if (inviteLink?.viewer_state?.is_already_member) return 'already_member'
  if (!inviteLink?.viewer_state?.is_authenticated) return 'auth_required'
  return 'actionable'
}

function resolveTitle(state) {
  if (state === 'auth_required') return 'Sign in to join this workspace'
  if (state === 'actionable') return 'Accept team invite link'
  if (state === 'already_member') return 'You already have access'
  if (state === 'revoked') return 'This invite link was revoked'
  if (state === 'expired') return 'This invite link expired'
  if (state === 'maxed_out') return 'Invite link usage limit reached'
  if (state === 'archived') return 'Workspace is not accepting joins'
  if (state === 'missing') return 'Invite link token is missing'
  if (state === 'invalid') return 'Invite link not found'
  if (state === 'error') return 'Unable to load invite link'
  return 'Review team invite link'
}

function resolveSubtitle(state) {
  if (state === 'auth_required') return 'Use your account to confirm access and join this team.'
  if (state === 'actionable') return 'Review the workspace and role details before joining.'
  if (state === 'already_member') return 'You can continue directly to the team workspace.'
  if (state === 'revoked') return 'A team admin revoked this link before it was used.'
  if (state === 'expired') return 'Ask a team admin for a newly generated invite link.'
  if (state === 'maxed_out') return 'This link has reached its maximum number of accepted joins.'
  if (state === 'archived') return 'This workspace is archived and no longer allows new memberships.'
  if (state === 'missing') return 'Open the full invite link URL and try again.'
  if (state === 'invalid') return 'The token is invalid or has been removed.'
  if (state === 'error') return 'Please refresh and retry this invite link.'
  return 'Review workspace details before continuing.'
}

export default function InviteLinkResponse() {
  const { token: routeToken = '' } = useParams()
  const [searchParams] = useSearchParams()
  const token = routeToken || searchParams.get('token') || ''
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [requestState, setRequestState] = useState('loading')
  const [inviteLink, setInviteLink] = useState(null)

  const loginHref = buildInviteLinkAuthHref({ token, mode: 'login' })
  const registerHref = buildInviteLinkAuthHref({ token, mode: 'register' })

  useEffect(() => {
    const loadInviteLink = async () => {
      if (!token) {
        setRequestState('missing')
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const response = await invitationsAPI.resolveInviteLink(token)
        setInviteLink(unwrapData(response))
        setRequestState('ready')
      } catch (error) {
        const statusCode = error?.response?.status
        setRequestState(statusCode === 404 ? 'invalid' : 'error')
      } finally {
        setLoading(false)
      }
    }

    loadInviteLink()
  }, [token])

  const state = useMemo(() => deriveInviteLinkState({ requestState, inviteLink }), [inviteLink, requestState])
  const team = inviteLink?.team || null
  const invitedRole = String(inviteLink?.invited_role || inviteLink?.role || 'member').toLowerCase()
  const teamContinueUrl = team?.id ? `/teams/${team.id}/overview` : '/teams'

  const handleAccept = async () => {
    if (!token || !team?.id) return
    setActionLoading(true)
    try {
      await invitationsAPI.acceptInviteLink(token)
      try {
        await dispatch(hydrateCurrentUser()).unwrap()
      } catch (_error) {
        // Ignore bootstrap refresh errors after successful acceptance.
      }
      toast.success('Joined team successfully.')
      if (invitedRole === 'member') {
        rememberMemberOnboarding(team.id)
        navigate(`/teams/${team.id}/overview?onboarding=member`, { replace: true })
        return
      }
      if (invitedRole === 'manager') {
        navigate(`/teams/${team.id}/overview?onboarding=manager`, { replace: true })
        return
      }
      navigate(`/teams/${team.id}/overview`, { replace: true })
    } catch (error) {
      const parsed = extractApiError(error, {
        fallbackMessage: 'Unable to accept this invite link right now.',
      })
      toast.error(parsed.message)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <AuthShell
      title={resolveTitle(state)}
      subtitle={resolveSubtitle(state)}
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
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Loading invite link</p>
          <p className="mt-3 text-sm leading-7 text-slate-600">Verifying workspace context, role assignment, and link availability.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {inviteLink ? (
            <div className={panelClass}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Team invite link</p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-950">{team?.name || 'Workspace invite'}</h2>
                  <p className="mt-2 max-w-xl text-sm leading-7 text-slate-600">
                    Join this workspace as a {toSentenceCase(invitedRole)}.
                  </p>
                </div>
                <StatusPill state={state} />
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <DetailCard label="Role" value={toSentenceCase(invitedRole)} />
                <DetailCard label="Status" value={toSentenceCase(inviteLink.status || 'active').replace('_', ' ')} />
                <DetailCard label="Label" value={inviteLink.label || 'No label'} />
                <DetailCard
                  label="Usage"
                  value={`${inviteLink.current_uses || 0}${inviteLink.max_uses ? ` / ${inviteLink.max_uses}` : ''}`}
                />
                <DetailCard label="Expires" value={inviteLink.expires_at ? formatDate(inviteLink.expires_at) : 'No expiry'} />
                <DetailCard label="Created" value={formatDate(inviteLink.created_at)} />
              </div>
            </div>
          ) : null}

          {state === 'auth_required' ? (
            <div className={panelClass}>
              <p className="text-sm leading-7 text-slate-600">Sign in or create an account to accept this invite link and join the workspace.</p>
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

          {state === 'actionable' ? (
            <div className={panelClass}>
              <p className="text-sm leading-7 text-slate-600">
                This link is active. Accepting will create your team membership using the role shown above.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button type="button" onClick={handleAccept} disabled={actionLoading} className="btn-primary flex-1 justify-center">
                  {actionLoading ? 'Joining workspace...' : 'Join team workspace'}
                </button>
                <Link to="/teams" className="btn-secondary flex-1 justify-center">
                  Cancel
                </Link>
              </div>
            </div>
          ) : null}

          {state === 'already_member' ? (
            <TerminalStateCard
              title="You are already a team member"
              description="Your membership is active. Continue to the workspace to review tasks, deadlines, and updates."
              actionLabel="Open team workspace"
              actionHref={teamContinueUrl}
            />
          ) : null}

          {['revoked', 'expired', 'maxed_out', 'archived', 'missing', 'invalid', 'error'].includes(state) ? (
            <TerminalStateCard
              title={resolveTitle(state)}
              description={resolveSubtitle(state)}
              actionLabel="Open teams"
              actionHref={state === 'missing' || state === 'invalid' ? '/login' : '/teams'}
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

function StatusPill({ state }) {
  const toneMap = {
    actionable: 'bg-emerald-50 text-emerald-700',
    auth_required: 'bg-slate-100 text-slate-700',
    already_member: 'bg-sky-50 text-sky-700',
    revoked: 'bg-rose-50 text-rose-700',
    expired: 'bg-amber-50 text-amber-700',
    maxed_out: 'bg-slate-100 text-slate-700',
    archived: 'bg-slate-100 text-slate-700',
    missing: 'bg-rose-50 text-rose-700',
    invalid: 'bg-rose-50 text-rose-700',
    error: 'bg-rose-50 text-rose-700',
  }
  return (
    <span className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] ${toneMap[state] || toneMap.auth_required}`}>
      {toSentenceCase(state.replace('_', ' '))}
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
