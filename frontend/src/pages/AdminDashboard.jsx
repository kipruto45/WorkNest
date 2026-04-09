import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { dashboardAPI, notificationsAPI, usersAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate, getInitials, toSentenceCase } from '../utils/formatters'

const sectionMap = {
  users: 'admin-users',
  teams: 'admin-teams',
  tasks: 'admin-growth',
  notifications: 'admin-notifications',
  messaging: 'admin-messaging',
  'audit-logs': 'admin-audit',
  settings: 'admin-ops',
}

const panelClass = 'rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const insetPanelClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb] p-4'

export default function AdminDashboard() {
  const { section } = useParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [snapshot, setSnapshot] = useState(null)
  const [audience, setAudience] = useState('all')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [sending, setSending] = useState(false)

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await dashboardAPI.getAdminOverview()
        setSnapshot(unwrapData(response))
      } catch (requestError) {
        setError(requestError?.response?.data?.message || 'Unable to load admin dashboard data right now.')
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  useEffect(() => {
    if (!section) return
    const targetId = sectionMap[section]
    if (!targetId) return
    const element = document.getElementById(targetId)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [section])

  useEffect(() => {
    if (audience !== 'selected') {
      setSearchResults([])
      return undefined
    }

    const trimmedQuery = query.trim()
    if (!trimmedQuery) {
      setSearchResults([])
      return undefined
    }

    const timeoutId = window.setTimeout(async () => {
      setSearching(true)
      try {
        const response = await usersAPI.searchAdminUsers({ q: trimmedQuery, page_size: 8, is_active: true })
        const results = unwrapResults(response).filter(
          (candidate) => !selectedUsers.some((selected) => selected.id === candidate.id)
        )
        setSearchResults(results)
      } catch (requestError) {
        toast.error(requestError?.response?.data?.message || 'Unable to search users right now.')
      } finally {
        setSearching(false)
      }
    }, 250)

    return () => window.clearTimeout(timeoutId)
  }, [audience, query, selectedUsers])

  const overview = snapshot?.overview || {}
  const growth = snapshot?.growth || {}
  const userActivity = snapshot?.user_activity || {}
  const teamHealth = snapshot?.team_health || {}
  const notifications = snapshot?.notifications || {}
  const ops = snapshot?.ops || {}
  const insights = snapshot?.insights || {}
  const attentionQueue = insights.attention_queue || []
  const adminInsights = insights.admin_insights || []
  const audienceSummary =
    audience === 'all'
      ? 'This message will be delivered to every active student account except you.'
      : selectedUsers.length
        ? `This message will be delivered to ${selectedUsers.length} selected user${selectedUsers.length === 1 ? '' : 's'}.`
        : 'Search for a student, then add them as a recipient.'

  const overviewCards = [
    { label: 'Total Users', value: overview.total_users ?? 0, note: 'Registered accounts' },
    { label: 'Total Teams', value: overview.total_teams ?? 0, note: 'Active workspaces' },
    { label: 'Total Tasks', value: overview.total_tasks ?? 0, note: 'Tracked work items' },
    { label: 'Active Users', value: overview.active_users ?? 0, note: 'Seen in the last 7 days' },
    { label: 'Pending Invites', value: overview.pending_invites ?? 0, note: 'Awaiting response' },
    { label: 'Activity Today', value: overview.system_activity_today ?? 0, note: 'Audit events recorded' },
  ]

  const addSelectedUser = (candidate) => {
    if (selectedUsers.some((user) => user.id === candidate.id)) return
    setSelectedUsers((current) => [...current, candidate])
    setQuery('')
    setSearchResults([])
  }

  const removeSelectedUser = (userId) => {
    setSelectedUsers((current) => current.filter((item) => item.id !== userId))
  }

  const handleSendNotification = async (event) => {
    event.preventDefault()
    const trimmedMessage = message.trim()
    const trimmedTitle = title.trim()

    if (!trimmedMessage) {
      toast.error('Write a message before sending.')
      return
    }

    if (audience === 'selected' && selectedUsers.length === 0) {
      toast.error('Select at least one user first.')
      return
    }

    setSending(true)
    try {
      const response = await notificationsAPI.sendAdminNotification({
        scope: audience,
        title: trimmedTitle,
        message: trimmedMessage,
        user_ids: audience === 'selected' ? selectedUsers.map((user) => user.id) : [],
      })
      const result = unwrapData(response) || {}
      toast.success(
        result.count
          ? `Notification sent to ${result.count} user${result.count === 1 ? '' : 's'}.`
          : 'No active recipients matched this send request.'
      )
      setTitle('')
      setMessage('')
      setQuery('')
      setSearchResults([])
      if (audience === 'selected') {
        setSelectedUsers([])
      }
    } catch (requestError) {
      toast.error(requestError?.response?.data?.message || 'Unable to send the notification right now.')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading admin dashboard" />
  }

  if (error) {
    return <EmptyState title="Admin dashboard unavailable" description={error} />
  }

  if (!snapshot) {
    return <EmptyState title="No admin data available" description="The platform overview did not return any usable data." />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-8 lg:grid-cols-[1.1fr,0.9fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">Platform Overview</p>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-slate-950">Operational visibility across the platform</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              Usage, growth, delivery load, audit events, and service health from one backend-authored control surface.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <CompactOverview label="Environment" value={overview.environment || ops.environment || 'unknown'} note={`Version ${overview.version || ops.version || 'n/a'}`} />
            <CompactOverview label="Health" value={toSentenceCase(overview.health_status || 'unknown')} note="Runtime readiness" />
            <CompactOverview label="Unread" value={notifications.unread_notifications ?? 0} note="Unread platform notifications" />
          </div>
        </div>
      </section>

      <section id="admin-overview" className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {overviewCards.map((item) => (
          <MetricCard key={item.label} label={item.label} value={item.value} note={item.note} />
        ))}
      </section>

      <section id="admin-attention" className={panelClass}>
        <SectionHeader eyebrow="Attention Queue" title="Actionable admin signals" />
        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {attentionQueue.map((item) => (
            <div key={item.title} className={`${insetPanelClass} ${severityClasses[item.severity] || severityClasses.healthy}`}>
              <p className="text-xs font-semibold uppercase tracking-[0.18em]">{toSentenceCase(item.severity)}</p>
              <h3 className="mt-3 text-lg font-semibold text-slate-950">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
              <Link to={item.href} className="mt-4 inline-flex text-sm font-semibold text-emerald-700">
                {item.action_label}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section id="admin-growth" className={panelClass}>
        <SectionHeader eyebrow="Growth & Usage" title="Seven-day platform movement" />
        <div className="mt-6 grid gap-4 xl:grid-cols-2">
          <SeriesCard title="User growth" items={growth.user_growth || []} />
          <SeriesCard title="Team growth" items={growth.team_growth || []} />
          <SeriesCard title="Task creation" items={growth.task_creation || []} />
          <SeriesCard title="Platform activity" items={growth.platform_activity || []} />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.92fr,1.08fr]">
        <section id="admin-users" className={panelClass}>
          <SectionHeader eyebrow="User Activity" title="Recently active users and registrations" />

          <div className="mt-5 space-y-3">
            {(userActivity.recently_active_users || []).length === 0 ? (
              <EmptyState title="No recent user activity" description="Recent actor activity will appear here as users interact with the platform." />
            ) : (
              userActivity.recently_active_users.map((item) => (
                <ActivityUserRow key={item.id} item={item} />
              ))
            )}
          </div>

          <div className="mt-6 border-t border-slate-200 pt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">New registrations</p>
            <div className="mt-4 space-y-3">
              {(userActivity.new_registrations || []).map((user) => (
                <div key={user.id} className={insetPanelClass}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{user.name || user.email}</p>
                      <p className="mt-1 text-sm text-slate-600">{user.email}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{toSentenceCase(user.auth_provider)}</p>
                      <p className="mt-1 text-sm text-slate-700">{formatDate(user.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="admin-teams" className={panelClass}>
          <SectionHeader eyebrow="Team Health" title="Most active, inactive, and overdue-heavy teams" />

          <div className="mt-5 grid gap-5 lg:grid-cols-3">
            <TeamHealthColumn
              title="Most active"
              items={teamHealth.most_active_teams || []}
              caption="Recent activity and task volume"
            />
            <TeamHealthColumn
              title="Needs momentum"
              items={teamHealth.inactive_teams || []}
              caption="Lowest recent activity"
            />
            <TeamHealthColumn
              title="Overdue concentration"
              items={teamHealth.overdue_heavy_teams || []}
              caption="Deadline pressure hotspots"
            />
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.04fr,0.96fr]">
        <section id="admin-notifications" className={panelClass}>
          <SectionHeader eyebrow="Notification Signals" title="Current distribution across notification types" />
          <div className="mt-5 space-y-4">
            {(notifications.distribution || []).map((item) => (
              <DistributionRow key={item.type} label={toSentenceCase(item.type)} value={item.count} items={notifications.distribution || []} />
            ))}
          </div>
        </section>

        <section id="admin-ops" className={panelClass}>
          <SectionHeader eyebrow="System Status" title="Operational dependencies and environment" />
          <div className="mt-5 grid gap-3">
            {(ops.services || []).map((service) => (
              <div key={service.label} className={insetPanelClass}>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">{service.label}</p>
                    <p className="mt-1 text-sm text-slate-600">{ops.environment || 'Runtime environment'}</p>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${serviceToneClasses[service.tone] || serviceToneClasses.neutral}`}>
                    {toSentenceCase(service.value)}
                  </span>
                </div>
              </div>
            ))}
            <div className={`${insetPanelClass} grid gap-3 sm:grid-cols-2`}>
              <MiniKpi label="Docs enabled" value={ops.docs_enabled ? 'Yes' : 'No'} />
              <MiniKpi label="Debug" value={ops.debug ? 'On' : 'Off'} />
            </div>
          </div>
        </section>
      </div>

      <section id="admin-messaging" className={panelClass}>
        <SectionHeader eyebrow="Admin Messaging" title="Send in-app notifications to students" />
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
          Send an announcement to every active student or target specific users. Messages are delivered through the in-app notification system and appear live for anyone currently active in the app.
        </p>

        <div className="mt-6 grid gap-6 xl:grid-cols-[0.72fr,1.28fr]">
          <div className="space-y-4">
            <div className={insetPanelClass}>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Audience</p>
              <div className="mt-4 grid gap-3">
                <AudienceOption
                  active={audience === 'all'}
                  title="All students"
                  description="Broadcast to every active user account."
                  onClick={() => setAudience('all')}
                />
                <AudienceOption
                  active={audience === 'selected'}
                  title="Selected users"
                  description="Search and choose the exact recipients."
                  onClick={() => setAudience('selected')}
                />
              </div>
            </div>

            <div className={insetPanelClass}>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Delivery summary</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">{audienceSummary}</p>
            </div>
          </div>

          <form onSubmit={handleSendNotification} className="grid gap-4">
            <div className={insetPanelClass}>
              <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Title</label>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="mt-3 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-emerald-400"
                placeholder="Message from admin"
                maxLength={255}
              />
            </div>

            <div className={insetPanelClass}>
              <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Message</label>
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                className="mt-3 min-h-[148px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-emerald-400"
                placeholder="Write the message students should receive in the app."
                maxLength={1000}
              />
            </div>

            {audience === 'selected' ? (
              <div className={insetPanelClass}>
                <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Target users</label>
                <div className="mt-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-center gap-3">
                    <SearchIcon className="h-5 w-5 text-slate-400" />
                    <input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      className="w-full border-none bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                      placeholder="Search by name or email"
                    />
                  </div>
                </div>

                {selectedUsers.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {selectedUsers.map((user) => (
                      <SelectedUserChip key={user.id} user={user} onRemove={() => removeSelectedUser(user.id)} />
                    ))}
                  </div>
                ) : null}

                <div className="mt-4 space-y-3">
                  {searching ? (
                    <p className="text-sm text-slate-500">Searching users...</p>
                  ) : searchResults.length ? (
                    searchResults.map((candidate) => (
                      <UserSearchRow key={candidate.id} user={candidate} onSelect={() => addSelectedUser(candidate)} />
                    ))
                  ) : query.trim() ? (
                    <p className="text-sm text-slate-500">No matching active users found.</p>
                  ) : (
                    <p className="text-sm text-slate-500">Search to find and select users.</p>
                  )}
                </div>
              </div>
            ) : null}

            <div className="flex items-center justify-between gap-4 rounded-[22px] border border-slate-200 bg-[#fcfcfb] px-5 py-4">
              <p className="text-sm text-slate-600">Recipients will receive the notification inside the app immediately.</p>
              <button
                type="submit"
                disabled={sending}
                className="inline-flex items-center rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {sending ? 'Sending...' : 'Send notification'}
              </button>
            </div>
          </form>
        </div>
      </section>

      <section id="admin-audit" className={panelClass}>
        <SectionHeader eyebrow="System Events" title="Recent audit trail" />
        <div className="mt-5 space-y-3">
          {(snapshot.system_events || []).length === 0 ? (
            <EmptyState title="No audit events yet" description="Important system actions will appear here once they are recorded." />
          ) : (
            snapshot.system_events.map((event) => (
              <div key={event.id} className={insetPanelClass}>
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">{event.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{event.description}</p>
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {event.actor_name || 'System'} {event.team_name ? `• ${event.team_name}` : ''}
                    </p>
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    {formatRelativeDate(event.created_at)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className={panelClass}>
        <SectionHeader eyebrow="Admin Insights" title="Platform checks worth reviewing" />
        <div className="mt-5 grid gap-4 xl:grid-cols-3">
          {adminInsights.map((item) => (
            <div key={item.label} className={insetPanelClass}>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
              <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{item.value}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.note}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

const severityClasses = {
  critical: 'border-rose-200 bg-rose-50/80',
  warning: 'border-amber-200 bg-amber-50/80',
  healthy: 'border-emerald-200 bg-emerald-50/70',
}

const serviceToneClasses = {
  healthy: 'bg-emerald-50 text-emerald-700',
  warning: 'bg-amber-50 text-amber-700',
  neutral: 'bg-slate-100 text-slate-700',
}

function SectionHeader({ eyebrow, title }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p>
      <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
    </div>
  )
}

function CompactOverview({ label, value, note }) {
  return (
    <div className={insetPanelClass}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-600">{note}</p>
    </div>
  )
}

function AudienceOption({ active, title, description, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-[20px] border px-4 py-4 text-left transition-colors ${
        active ? 'border-emerald-300 bg-emerald-50' : 'border-slate-200 bg-white hover:bg-slate-50'
      }`}
    >
      <p className="text-sm font-semibold text-slate-950">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
    </button>
  )
}

function MetricCard({ label, value, note }) {
  return (
    <div className={`${panelClass} p-5`}>
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}

function SeriesCard({ title, items }) {
  const maxValue = Math.max(1, ...(items || []).map((item) => item.count))

  return (
    <div className={insetPanelClass}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-sm text-slate-600">
            {(items || []).reduce((sum, item) => sum + item.count, 0)} total over the last seven days
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-7 items-end gap-2">
        {(items || []).map((item) => (
          <div key={`${title}-${item.date}`} className="flex flex-col items-center gap-2">
            <div className="w-full rounded-t-xl bg-emerald-600/85" style={{ height: `${item.count ? Math.max(18, (item.count / maxValue) * 96) : 8}px` }} />
            <span className="text-[11px] font-medium text-slate-500">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ActivityUserRow({ item }) {
  return (
    <div className={insetPanelClass}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-950">{item.name || item.email}</p>
          <p className="mt-1 text-sm text-slate-600">{item.email}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold text-slate-950">{item.actions}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
            Active {formatRelativeDate(item.last_seen)}
          </p>
        </div>
      </div>
    </div>
  )
}

function UserSearchRow({ user, onSelect }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-[18px] border border-slate-200 bg-white px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <UserListAvatar user={user} />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-950">{user.name || user.email}</p>
          <p className="truncate text-sm text-slate-600">{user.email}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onSelect}
        className="inline-flex rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-900 transition-colors hover:bg-slate-50"
      >
        Select
      </button>
    </div>
  )
}

function SelectedUserChip({ user, onRemove }) {
  return (
    <div className="inline-flex items-center gap-3 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2">
      <UserListAvatar user={user} compact />
      <span className="max-w-[220px] truncate text-sm font-medium text-emerald-950">{user.name || user.email}</span>
      <button
        type="button"
        onClick={onRemove}
        className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700"
      >
        Remove
      </button>
    </div>
  )
}

function UserListAvatar({ user, compact = false }) {
  const initials = getInitials(user?.name || user?.email || 'U')
  const sizeClass = compact ? 'h-7 w-7 rounded-full text-[10px]' : 'h-10 w-10 rounded-2xl text-sm'

  if (user?.avatar) {
    return <img src={user.avatar} alt={user.name || user.email} className={`${sizeClass} object-cover border border-slate-200`} />
  }

  return (
    <div className={`flex items-center justify-center bg-emerald-700 font-semibold text-white ${sizeClass}`}>
      {initials}
    </div>
  )
}

function TeamHealthColumn({ title, items, caption }) {
  return (
    <div>
      <p className="text-sm font-semibold text-slate-950">{title}</p>
      <p className="mt-1 text-sm text-slate-600">{caption}</p>
      <div className="mt-4 space-y-3">
        {items.length === 0 ? (
          <div className={insetPanelClass}>
            <p className="text-sm text-slate-600">No teams in this bucket right now.</p>
          </div>
        ) : (
          items.map((item) => (
            <div key={item.id} className={insetPanelClass}>
              <p className="text-sm font-semibold text-slate-950">{item.name}</p>
              <p className="mt-2 text-sm text-slate-600">
                {item.task_count} tasks • {item.overdue_count} overdue • {item.activity_count} recent events
              </p>
              <p className="mt-2 text-xs uppercase tracking-[0.16em] text-slate-500">
                Updated {formatRelativeDate(item.updated_at)}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function DistributionRow({ label, value, items }) {
  const maxValue = Math.max(1, ...(items || []).map((item) => item.count))

  return (
    <div className={insetPanelClass}>
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-slate-950">{label}</p>
        <p className="text-sm font-medium text-slate-600">{value}</p>
      </div>
      <div className="mt-3 h-2.5 rounded-full bg-slate-100">
        <div className="h-2.5 rounded-full bg-emerald-700 transition-all duration-700" style={{ width: `${(value / maxValue) * 100}%` }} />
      </div>
    </div>
  )
}

function MiniKpi({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{value}</p>
    </div>
  )
}

function SearchIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="m21 21-4.35-4.35M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" />
    </svg>
  )
}
