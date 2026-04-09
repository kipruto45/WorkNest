import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'
import { resolveMembershipRole } from '../utils/permissions'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

export default function TeamAnnouncements() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [team, setTeam] = useState(null)
  const [announcements, setAnnouncements] = useState([])
  const [query, setQuery] = useState('')
  const [draft, setDraft] = useState({ title: '', content: '' })

  const loadAnnouncements = useCallback(async () => {
    setLoading(true)
    try {
      const [teamResponse, announcementsResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        teamsAPI.getAnnouncements(teamId, { page_size: 50 }),
      ])
      setTeam(unwrapData(teamResponse))
      setAnnouncements(unwrapResults(announcementsResponse))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load team announcements.')
      setAnnouncements([])
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    loadAnnouncements()
  }, [loadAnnouncements])

  const currentRole = resolveMembershipRole(team)
  const canPublish = currentRole === 'admin' || currentRole === 'manager'

  const filteredAnnouncements = useMemo(() => {
    const input = query.trim().toLowerCase()
    if (!input) return announcements
    return announcements.filter((item) => {
      const haystack = `${item.title || ''} ${item.content || ''} ${item.published_by?.name || ''}`
      return haystack.toLowerCase().includes(input)
    })
  }, [announcements, query])

  const featuredAnnouncement = filteredAnnouncements.find((item) => item.is_pinned) || filteredAnnouncements[0] || null

  const handlePublish = async (event) => {
    event.preventDefault()
    if (!canPublish) {
      toast.error('Only team admins or managers can publish announcements.')
      return
    }
    if (!draft.title.trim() || !draft.content.trim()) {
      toast.error('Add both title and content.')
      return
    }

    setSaving(true)
    try {
      await teamsAPI.createAnnouncement(teamId, {
        title: draft.title.trim(),
        content: draft.content.trim(),
      })
      setDraft({ title: '', content: '' })
      await loadAnnouncements()
      toast.success('Announcement published.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to publish announcement.')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !team) {
    return <LoadingState label="Loading announcements" />
  }

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.15fr,0.85fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Announcements</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{team.name} communication hub</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Share milestones, operational notes, and team-level updates in one clean channel that everybody can scan quickly.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Back to dashboard
              </Link>
              <button type="button" onClick={loadAnnouncements} className="btn-secondary">
                Refresh feed
              </button>
            </div>
          </div>

          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <SummaryTile label="Total posts" value={announcements.length} note="Across this workspace" />
              <SummaryTile
                label="Published today"
                value={announcements.filter((item) => formatRelativeDate(item.created_at) === 'Today').length}
                note="Recent updates"
              />
              <SummaryTile label="Your role" value={toSentenceCase(currentRole || 'member')} note={canPublish ? 'Can publish' : 'Read-only'} />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Browse updates</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Recent communication</h2>
          </div>
          <label className="w-full max-w-md text-sm font-medium text-slate-600">
            Search announcements
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-field mt-2"
              placeholder="Find by title, message, or author"
            />
          </label>
        </div>

        {featuredAnnouncement ? (
          <article className={`${cardClass} mt-5 p-5`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
                {featuredAnnouncement.is_pinned ? 'Pinned' : 'Latest'}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                {formatRelativeDate(featuredAnnouncement.created_at)}
              </span>
            </div>
            <h3 className="mt-3 text-xl font-semibold text-slate-950">{featuredAnnouncement.title}</h3>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{featuredAnnouncement.content}</p>
            <p className="mt-3 text-xs text-slate-500">
              Published by {featuredAnnouncement.published_by?.name || 'Team lead'} on {formatDate(featuredAnnouncement.created_at)}
            </p>
          </article>
        ) : null}

        <div className="mt-5 space-y-3">
          {filteredAnnouncements.length === 0 ? (
            <EmptyState
              title="No announcements yet"
              description="Team announcements will appear here once leads start publishing updates."
            />
          ) : (
            filteredAnnouncements.map((announcement) => (
              <article key={announcement.id} className={`${cardClass} p-4`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-slate-950">{announcement.title}</h3>
                    <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-600">{announcement.content}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                    {formatRelativeDate(announcement.created_at)}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  {announcement.published_by?.name || 'Team lead'} | {formatDate(announcement.created_at)}
                </p>
              </article>
            ))
          )}
        </div>
      </section>

      {canPublish ? (
        <section className={`${panelClass} p-6 lg:p-7`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Create announcement</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950">Publish a new team message</h2>

          <form onSubmit={handlePublish} className="mt-5 space-y-4">
            <label className="block text-sm font-semibold text-slate-900">
              Title
              <input
                value={draft.title}
                onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                className="input-field mt-2"
                placeholder="Sprint planning update"
              />
            </label>
            <label className="block text-sm font-semibold text-slate-900">
              Message
              <textarea
                value={draft.content}
                onChange={(event) => setDraft((current) => ({ ...current, content: event.target.value }))}
                className="input-field mt-2 min-h-[140px]"
                placeholder="Share goals, blockers, and what the team should focus on next."
              />
            </label>
            <div className="flex justify-end">
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? 'Publishing...' : 'Publish announcement'}
              </button>
            </div>
          </form>
        </section>
      ) : null}
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}
