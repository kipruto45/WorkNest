import { useEffect, useMemo, useState } from 'react'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { notificationsAPI, teamsAPI, unwrapData, unwrapResults, usersAPI } from '../services/api'
import { extractApiError } from '../utils/apiErrors'
import { formatDate, toSentenceCase } from '../utils/formatters'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const insetPanelClass = 'rounded-[20px] border border-slate-200 bg-[#fcfcfb] p-4'

const audienceOptions = [
  { id: 'all_users', label: 'All Users', description: 'Broadcast to every active user account.' },
  { id: 'single_user', label: 'Single User', description: 'Deliver a direct update to one user.' },
  { id: 'selected_users', label: 'Selected Users', description: 'Choose specific individuals to notify.' },
  { id: 'single_team', label: 'Single Team', description: 'Send a workspace-wide update to one team.' },
  { id: 'selected_teams', label: 'Selected Teams', description: 'Choose multiple teams to receive this message.' },
]

const channelOptions = [
  { id: 'in_app', label: 'In-app only' },
  { id: 'email', label: 'Email only' },
  { id: 'sms', label: 'SMS only' },
  { id: 'email_and_in_app', label: 'Email + In-app' },
  { id: 'sms_and_in_app', label: 'SMS + In-app' },
  { id: 'email_and_sms', label: 'Email + SMS' },
  { id: 'all', label: 'All channels' },
]

const buildCommunicationToastMessage = (communication) => {
  if (!communication) {
    return 'Communication sent successfully.'
  }

  const recipientCount = communication.recipient_count ?? 0
  const failedSmsCount = communication.failed_sms_count ?? 0
  const deliveredInApp = communication.delivered_in_app_count ?? 0
  const deliveredEmail = communication.delivered_email_count ?? 0
  const deliveredSms = communication.delivered_sms_count ?? 0

  if (communication.status === 'partial_failure') {
    return `Communication sent to ${recipientCount} recipients. SMS failed for ${failedSmsCount}.`
  }

  if (communication.status === 'failed') {
    return 'Communication was created, but delivery failed.'
  }

  return `Communication queued for ${recipientCount} recipients across ${[deliveredInApp && 'in-app', deliveredEmail && 'email', deliveredSms && 'SMS'].filter(Boolean).join(', ') || 'the selected channels'}.`
}

export default function AdminCommunications() {
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [communications, setCommunications] = useState([])
  const [audienceType, setAudienceType] = useState('all_users')
  const [channelType, setChannelType] = useState('email_and_in_app')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [ctaLabel, setCtaLabel] = useState('')
  const [ctaLink, setCtaLink] = useState('')
  const [userQuery, setUserQuery] = useState('')
  const [teamQuery, setTeamQuery] = useState('')
  const [userResults, setUserResults] = useState([])
  const [teamResults, setTeamResults] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [selectedTeams, setSelectedTeams] = useState([])
  const [confirmBroadcast, setConfirmBroadcast] = useState(false)
  const [searchingUsers, setSearchingUsers] = useState(false)
  const [searchingTeams, setSearchingTeams] = useState(false)

  useEffect(() => {
    const fetchCommunications = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await notificationsAPI.getAdminCommunications({ page_size: 12 })
        const payload = unwrapData(response)
        setCommunications(payload?.results || payload || [])
      } catch (requestError) {
        setError(requestError?.response?.data?.message || 'Unable to load communications right now.')
      } finally {
        setLoading(false)
      }
    }

    fetchCommunications()
  }, [])

  useEffect(() => {
    if (!['selected_users', 'single_user'].includes(audienceType)) {
      setUserQuery('')
      setUserResults([])
      return undefined
    }

    const trimmed = userQuery.trim()
    if (!trimmed) {
      setUserResults([])
      return undefined
    }

    const timeoutId = window.setTimeout(async () => {
      setSearchingUsers(true)
      try {
        const response = await usersAPI.searchAdminUsers({ q: trimmed, page_size: 8, is_active: true })
        const results = unwrapResults(response).filter(
          (candidate) => !selectedUsers.some((selected) => selected.id === candidate.id)
        )
        setUserResults(results)
      } catch (requestError) {
        toast.error(requestError?.response?.data?.message || 'Unable to search users right now.')
      } finally {
        setSearchingUsers(false)
      }
    }, 240)

    return () => window.clearTimeout(timeoutId)
  }, [audienceType, userQuery, selectedUsers])

  useEffect(() => {
    if (!['single_team', 'selected_teams'].includes(audienceType)) {
      setTeamQuery('')
      setTeamResults([])
      return undefined
    }

    const trimmed = teamQuery.trim()
    if (!trimmed) {
      setTeamResults([])
      return undefined
    }

    const timeoutId = window.setTimeout(async () => {
      setSearchingTeams(true)
      try {
        const response = await teamsAPI.searchAdminTeams({ q: trimmed, page_size: 8 })
        const results = unwrapResults(response).filter(
          (candidate) => !selectedTeams.some((selected) => selected.id === candidate.id)
        )
        setTeamResults(results)
      } catch (requestError) {
        toast.error(requestError?.response?.data?.message || 'Unable to search teams right now.')
      } finally {
        setSearchingTeams(false)
      }
    }, 240)

    return () => window.clearTimeout(timeoutId)
  }, [audienceType, teamQuery, selectedTeams])

  const handleSelectUser = (user) => {
    if (audienceType === 'single_user') {
      setSelectedUsers([user])
      setUserResults([])
      setUserQuery('')
      return
    }
    setSelectedUsers((current) => [...current, user])
    setUserResults([])
    setUserQuery('')
  }

  const handleSelectTeam = (team) => {
    if (audienceType === 'single_team') {
      setSelectedTeams([team])
      setTeamResults([])
      setTeamQuery('')
      return
    }
    setSelectedTeams((current) => [...current, team])
    setTeamResults([])
    setTeamQuery('')
  }

  const handleRemoveUser = (id) => setSelectedUsers((current) => current.filter((item) => item.id !== id))
  const handleRemoveTeam = (id) => setSelectedTeams((current) => current.filter((item) => item.id !== id))

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmedTitle = title.trim()
    const trimmedMessage = message.trim()
    const smsSelectedForSubmit = ['sms', 'sms_and_in_app', 'email_and_sms', 'all'].includes(channelType)

    if (!trimmedTitle || !trimmedMessage) {
      toast.error('Add a title and message before sending.')
      return
    }

    if (audienceType === 'selected_users' && selectedUsers.length === 0) {
      toast.error('Select at least one user.')
      return
    }
    if (audienceType === 'single_user' && selectedUsers.length !== 1) {
      toast.error('Select exactly one user.')
      return
    }
    if (audienceType === 'selected_teams' && selectedTeams.length === 0) {
      toast.error('Select at least one team.')
      return
    }
    if (audienceType === 'single_team' && selectedTeams.length !== 1) {
      toast.error('Select exactly one team.')
      return
    }
    if (smsSelectedForSubmit && !confirmBroadcast) {
      toast.error('Confirm the SMS broadcast before sending.')
      return
    }

    setSending(true)
    try {
      const payload = {
        audience_type: audienceType,
        channel_type: channelType,
        title: trimmedTitle,
        message: trimmedMessage,
        user_ids: ['selected_users', 'single_user'].includes(audienceType) ? selectedUsers.map((user) => user.id) : [],
        team_ids: ['selected_teams', 'single_team'].includes(audienceType) ? selectedTeams.map((team) => team.id) : [],
        cta_label: ctaLabel.trim(),
        cta_link: ctaLink.trim(),
        confirm_broadcast: confirmBroadcast,
      }
      const response = await notificationsAPI.createAdminCommunication(payload)
      const created = unwrapData(response)
      toast.success(buildCommunicationToastMessage(created))
      setCommunications((current) => (created ? [created, ...current] : current))
      setTitle('')
      setMessage('')
      setCtaLabel('')
      setCtaLink('')
      setConfirmBroadcast(false)
      if (audienceType !== 'all_users') {
        setSelectedUsers([])
        setSelectedTeams([])
      }
    } catch (requestError) {
      toast.error(
        extractApiError(requestError, {
          fallbackMessage: 'Unable to send the communication right now.',
          serverMessage: 'Server error while sending the communication.',
        }).message
      )
    } finally {
      setSending(false)
    }
  }

  const audienceSummary = useMemo(() => {
    if (audienceType === 'all_users') {
      return 'This message will reach every active user across the platform.'
    }
    if (audienceType.includes('user')) {
      if (selectedUsers.length === 0) return 'Search and select the users you want to reach.'
      return `${selectedUsers.length} user${selectedUsers.length === 1 ? '' : 's'} selected for this communication.`
    }
    if (selectedTeams.length === 0) {
      return 'Search and select the teams you want to reach.'
    }
    return `${selectedTeams.length} team${selectedTeams.length === 1 ? '' : 's'} selected for this communication.`
  }, [audienceType, selectedUsers, selectedTeams])

  const smsSelected = ['sms', 'sms_and_in_app', 'email_and_sms', 'all'].includes(channelType)
  const estimatedRecipients =
    audienceType === 'all_users'
      ? 'all active users'
      : audienceType.includes('user')
        ? `${selectedUsers.length || 0} user${selectedUsers.length === 1 ? '' : 's'}`
        : `${selectedTeams.length || 0} team${selectedTeams.length === 1 ? '' : 's'}`

  if (loading) {
    return <LoadingState label="Loading communications" />
  }

  if (error) {
    return <EmptyState title="Communications unavailable" description={error} />
  }

  return (
    <div className="space-y-6">
      <section className={panelClass}>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Admin communication</p>
            <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-slate-950">Broadcast clear updates to every workspace</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              Choose the right audience, pick the delivery channel, and ship a polished message that lands in-app, email, or SMS.
            </p>
          </div>
          <div className="rounded-[20px] border border-slate-200 bg-[#fcfcfb] px-4 py-3 text-sm text-slate-600">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Delivery mode</p>
            <p className="mt-2 font-semibold text-slate-900">{toSentenceCase(channelType.replace('_', ' '))}</p>
          </div>
        </div>
      </section>

      <section className={panelClass}>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Audience</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {audienceOptions.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setAudienceType(option.id)}
                  className={`rounded-[20px] border px-4 py-4 text-left transition ${
                    audienceType === option.id
                      ? 'border-emerald-500 bg-emerald-50 shadow-[0_12px_30px_rgba(16,185,129,0.15)]'
                      : 'border-slate-200 bg-white hover:border-emerald-200 hover:bg-emerald-50/40'
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-950">{option.label}</p>
                  <p className="mt-2 text-sm text-slate-600">{option.description}</p>
                </button>
              ))}
            </div>
            <p className="mt-3 text-sm text-slate-500">{audienceSummary}</p>
          </div>

          {['selected_users', 'single_user'].includes(audienceType) ? (
            <div className={insetPanelClass}>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Select users</label>
              <input
                value={userQuery}
                onChange={(event) => setUserQuery(event.target.value)}
                placeholder="Search users by name or email"
                className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
              />
              {searchingUsers ? (
                <p className="mt-3 text-sm text-slate-500">Searching users…</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {userResults.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => handleSelectUser(user)}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50/40"
                    >
                      <span>{user.name || user.email}</span>
                      <span className="text-xs text-slate-400">{user.email}</span>
                    </button>
                  ))}
                </div>
              )}
              {selectedUsers.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {selectedUsers.map((user) => (
                    <span key={user.id} className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-900">
                      {user.name || user.email}
                      <button type="button" onClick={() => handleRemoveUser(user.id)} className="text-emerald-700">
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          {['single_team', 'selected_teams'].includes(audienceType) ? (
            <div className={insetPanelClass}>
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Select teams</label>
              <input
                value={teamQuery}
                onChange={(event) => setTeamQuery(event.target.value)}
                placeholder="Search teams by name"
                className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
              />
              {searchingTeams ? (
                <p className="mt-3 text-sm text-slate-500">Searching teams…</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {teamResults.map((team) => (
                    <button
                      key={team.id}
                      type="button"
                      onClick={() => handleSelectTeam(team)}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50/40"
                    >
                      <span>{team.name}</span>
                      <span className="text-xs text-slate-400">{team.member_count || 0} members</span>
                    </button>
                  ))}
                </div>
              )}
              {selectedTeams.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {selectedTeams.map((team) => (
                    <span key={team.id} className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-900">
                      {team.name}
                      <button type="button" onClick={() => handleRemoveTeam(team.id)} className="text-emerald-700">
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-[2fr,1fr]">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Message title</label>
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Title for the communication"
                  className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Message body</label>
                <textarea
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Write a clear update for your users"
                  rows={6}
                  className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
                />
              </div>
            </div>
            <div className="space-y-4">
              <div className={insetPanelClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Delivery channel</p>
                <div className="mt-3 space-y-2">
                  {channelOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setChannelType(option.id)}
                      className={`w-full rounded-xl border px-3 py-2 text-left text-sm font-semibold transition ${
                        channelType === option.id
                          ? 'border-emerald-400 bg-emerald-50 text-emerald-900'
                          : 'border-slate-200 bg-white text-slate-700 hover:border-emerald-200'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className={insetPanelClass}>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Optional CTA</p>
                <input
                  value={ctaLabel}
                  onChange={(event) => setCtaLabel(event.target.value)}
                  placeholder="CTA label"
                  className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
                />
                <input
                  value={ctaLink}
                  onChange={(event) => setCtaLink(event.target.value)}
                  placeholder="https://"
                  className="mt-3 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-emerald-400"
                />
              </div>
              {smsSelected ? (
                <div className={insetPanelClass}>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">SMS sending guardrail</p>
                  <p className="mt-3 text-sm text-slate-600">
                    SMS is a paid channel. This send will target {estimatedRecipients} with concise mobile delivery where phone settings allow it.
                  </p>
                  <label className="mt-4 flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={confirmBroadcast}
                      onChange={(event) => setConfirmBroadcast(event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-emerald-200"
                    />
                    I’ve reviewed this SMS broadcast and want to send it intentionally.
                  </label>
                </div>
              ) : null}
              <button
                type="submit"
                disabled={sending}
                className="inline-flex w-full items-center justify-center rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
              >
                {sending ? 'Sending...' : 'Send communication'}
              </button>
            </div>
          </div>
        </form>
      </section>

      <section className={panelClass}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">History</p>
            <h2 className="mt-3 text-xl font-semibold text-slate-950">Sent communications</h2>
          </div>
        </div>
        {communications.length === 0 ? (
          <div className="mt-6">
            <EmptyState title="No communications yet" description="Your sent communications will appear here once you send the first update." />
          </div>
        ) : (
          <div className="mt-6 space-y-3">
            {communications.map((item) => (
              <div key={item.id} className="rounded-[20px] border border-slate-200 bg-white px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">{item.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.message}</p>
                  </div>
                  <div className="text-sm text-slate-500">
                    <p>{formatDate(item.sent_at || item.created_at)}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em]">{toSentenceCase(item.status)}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  <span>Audience: {toSentenceCase((item.audience_type || 'selected_users').replace('_', ' '))}</span>
                  <span>Channel: {toSentenceCase((item.channel_type || 'email_and_in_app').replace('_', ' '))}</span>
                  <span>Recipients: {item.recipient_count ?? 0}</span>
                  <span>SMS delivered: {item.delivered_sms_count ?? 0}</span>
                  <span>SMS failed: {item.failed_sms_count ?? 0}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
