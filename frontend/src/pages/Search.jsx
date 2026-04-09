import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { commonAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'

function SearchSection({ title, items, emptyTitle, emptyDescription }) {
  return (
    <section className="card fade-in">
      <h2 className="text-2xl font-bold text-emerald-950">{title}</h2>
      <div className="mt-5 grid gap-3">
        {items.length === 0 ? (
          <EmptyState title={emptyTitle} description={emptyDescription} />
        ) : (
          items.map((item) => (
            <Link key={`${title}-${item.id}`} to={item.href} className="feature-tile">
              <h3 className="text-lg font-bold text-emerald-950">{item.title}</h3>
              <p className="mt-1 text-sm text-soft">{item.subtitle || 'No additional context available.'}</p>
            </Link>
          ))
        )}
      </div>
    </section>
  )
}

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [teams, setTeams] = useState([])
  const [teamMembers, setTeamMembers] = useState([])
  const [filters, setFilters] = useState({
    team: searchParams.get('team') || '',
    assignee: searchParams.get('assignee') || '',
    status: searchParams.get('status') || '',
    priority: searchParams.get('priority') || '',
    date_from: searchParams.get('date_from') || '',
    date_to: searchParams.get('date_to') || '',
    types: new Set((searchParams.get('types') || '').split(',').filter(Boolean)),
  })
  const [results, setResults] = useState({
    tasks: [],
    teams: [],
    people: [],
    comments: [],
    announcements: [],
    milestones: [],
  })

  const normalizedQuery = query.trim()
  const typesKey = useMemo(() => Array.from(filters.types).sort().join(','), [filters.types])
  const selectedTypes = useMemo(() => (typesKey ? typesKey.split(',') : []), [typesKey])

  useEffect(() => {
    const nextParams = new URLSearchParams()
    if (normalizedQuery) {
      nextParams.set('q', normalizedQuery)
    }
    if (filters.team) nextParams.set('team', filters.team)
    if (filters.assignee) nextParams.set('assignee', filters.assignee)
    if (filters.status) nextParams.set('status', filters.status)
    if (filters.priority) nextParams.set('priority', filters.priority)
    if (filters.date_from) nextParams.set('date_from', filters.date_from)
    if (filters.date_to) nextParams.set('date_to', filters.date_to)
    if (selectedTypes.length > 0) {
      nextParams.set('types', selectedTypes.join(','))
    }
    setSearchParams(nextParams, { replace: true })
  }, [normalizedQuery, filters.assignee, filters.date_from, filters.date_to, filters.priority, filters.status, filters.team, selectedTypes, setSearchParams])

  useEffect(() => {
    const loadTeams = async () => {
      try {
        const response = await teamsAPI.getTeams({ page_size: 50 })
        setTeams(unwrapResults(response))
      } catch (_error) {
        setTeams([])
      }
    }
    loadTeams()
  }, [])

  useEffect(() => {
    const loadMembers = async () => {
      if (!filters.team) {
        setTeamMembers([])
        return
      }
      try {
        const response = await teamsAPI.getTeamMembers(filters.team, { page_size: 100 })
        setTeamMembers(unwrapResults(response))
      } catch (_error) {
        setTeamMembers([])
      }
    }
    loadMembers()
  }, [filters.team])

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await commonAPI.search({
          q: normalizedQuery,
          limit: 12,
          team: filters.team || undefined,
          assignee: filters.assignee || undefined,
          status: filters.status || undefined,
          priority: filters.priority || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
          types: typesKey || undefined,
        })
        const sections = unwrapData(response)?.sections || {}
        setResults({
          tasks: sections.tasks || [],
          teams: sections.teams || [],
          people: sections.people || [],
          comments: sections.comments || [],
          announcements: sections.announcements || [],
          milestones: sections.milestones || [],
        })
      } catch (_requestError) {
        setError('Search is unavailable right now.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [filters.assignee, filters.date_from, filters.date_to, filters.priority, filters.status, filters.team, normalizedQuery, typesKey])

  const totalMatches = useMemo(
    () => Object.values(results).reduce((sum, section) => sum + section.length, 0),
    [results]
  )
  const activeFilterCount = useMemo(
    () => [filters.team, filters.assignee, filters.status, filters.priority, filters.date_from, filters.date_to].filter(Boolean).length + filters.types.size,
    [filters.assignee, filters.date_from, filters.date_to, filters.priority, filters.status, filters.team, filters.types]
  )

  const handleTypeToggle = (value) => {
    setFilters((current) => {
      const next = new Set(current.types)
      if (next.has(value)) {
        next.delete(value)
      } else {
        next.add(value)
      }
      return { ...current, types: next }
    })
  }

  if (loading) {
    return <LoadingState label="Preparing search workspace" />
  }

  if (error) {
    return <EmptyState title="Search unavailable" description={error} />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Search"
        title="Find work, people, and team context fast"
        description="One permission-aware search surface for tasks, teams, comments, people, and announcements."
        stats={[
          { label: 'Total matches', value: totalMatches, caption: 'Across all sections' },
          { label: 'Query mode', value: normalizedQuery ? 'Live' : 'Recent', caption: 'Search behavior' },
          { label: 'Active filters', value: activeFilterCount, caption: 'Applied to this search' },
        ]}
        spotlight={{
          eyebrow: 'Global index',
          title: 'Search stays structured under pressure.',
          description: 'Results are grouped by the way people actually navigate work: tasks, teams, people, conversation, and announcements.',
          points: [
            { label: 'Current query', value: normalizedQuery || 'Recent activity' },
            { label: 'Result density', value: totalMatches || 'No matches' },
          ],
        }}
      />

      <section className="card fade-in">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <label className="block flex-1 text-sm font-semibold text-emerald-950">
            Search query
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="input-field mt-2"
              placeholder="Search tasks, teams, comments, people, or announcements"
            />
          </label>
          <button
            type="button"
            onClick={() =>
              setFilters({
                team: '',
                assignee: '',
                status: '',
                priority: '',
                date_from: '',
                date_to: '',
                types: new Set(),
              })
            }
            className="btn-secondary"
          >
            Clear filters
          </button>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <label className="block text-sm font-semibold text-emerald-950">
            Team
            <select
              value={filters.team}
              onChange={(event) => setFilters((current) => ({ ...current, team: event.target.value, assignee: '' }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            >
              <option value="">All teams</option>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold text-emerald-950">
            Assignee
            <select
              value={filters.assignee}
              onChange={(event) => setFilters((current) => ({ ...current, assignee: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            >
              <option value="">Any assignee</option>
              {teamMembers.map((member) => (
                <option key={member.user?.id || member.id} value={member.user?.id || member.id}>
                  {member.user?.name || member.user?.email || member.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold text-emerald-950">
            Status
            <select
              value={filters.status}
              onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            >
              <option value="">Any status</option>
              <option value="todo">Todo</option>
              <option value="in_progress">In progress</option>
              <option value="in_review">In review</option>
              <option value="done">Done</option>
              <option value="blocked">Blocked</option>
            </select>
          </label>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <label className="block text-sm font-semibold text-emerald-950">
            Priority
            <select
              value={filters.priority}
              onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            >
              <option value="">Any priority</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </label>
          <label className="block text-sm font-semibold text-emerald-950">
            Due from
            <input
              type="date"
              value={filters.date_from}
              onChange={(event) => setFilters((current) => ({ ...current, date_from: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            />
          </label>
          <label className="block text-sm font-semibold text-emerald-950">
            Due to
            <input
              type="date"
              value={filters.date_to}
              onChange={(event) => setFilters((current) => ({ ...current, date_to: event.target.value }))}
              className="mt-2 w-full rounded-xl border border-emerald-100 bg-white px-3 py-2 text-sm text-emerald-950 shadow-sm"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {[
            { key: 'tasks', label: 'Tasks' },
            { key: 'teams', label: 'Teams' },
            { key: 'people', label: 'People' },
            { key: 'comments', label: 'Comments' },
            { key: 'announcements', label: 'Announcements' },
            { key: 'milestones', label: 'Milestones' },
          ].map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => handleTypeToggle(item.key)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                filters.types.has(item.key)
                  ? 'bg-emerald-900 text-white'
                  : 'border border-emerald-100 text-emerald-900 hover:border-emerald-200'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <SearchSection
          title="Tasks"
          items={results.tasks}
          emptyTitle="No task matches"
          emptyDescription="Try a different title, label, or delivery phrase."
        />
        <SearchSection
          title="Teams"
          items={results.teams}
          emptyTitle="No team matches"
          emptyDescription="Try a team name, description, or slug."
        />
        <SearchSection
          title="People"
          items={results.people}
          emptyTitle="No people matched"
          emptyDescription="Search by teammate name or email."
        />
        <SearchSection
          title="Recent Matches"
          items={results.comments}
          emptyTitle="No comment matches"
          emptyDescription="Conversation matches will appear here."
        />
        <SearchSection
          title="Announcements"
          items={results.announcements}
          emptyTitle="No announcement matches"
          emptyDescription="Team announcements will appear here when they match your query."
        />
        <SearchSection
          title="Milestones"
          items={results.milestones}
          emptyTitle="No milestone matches"
          emptyDescription="Try searching by milestone title or due date."
        />
      </div>
    </div>
  )
}
