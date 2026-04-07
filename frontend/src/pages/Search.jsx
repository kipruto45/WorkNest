import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { tasksAPI, teamsAPI, unwrapResults } from '../services/api'
import { formatDate, toSentenceCase } from '../utils/formatters'

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [tasks, setTasks] = useState([])
  const [teams, setTeams] = useState([])

  const normalizedQuery = query.trim().toLowerCase()

  useEffect(() => {
    const nextParams = new URLSearchParams()
    if (query.trim()) {
      nextParams.set('q', query.trim())
    }
    setSearchParams(nextParams, { replace: true })
  }, [query, setSearchParams])

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      setError('')
      try {
        const params = normalizedQuery ? { search: normalizedQuery, page_size: 20 } : { page_size: 8 }
        const teamParams = normalizedQuery ? { search: normalizedQuery, page_size: 12 } : { page_size: 6 }
        const [tasksResponse, teamsResponse] = await Promise.all([
          tasksAPI.getTasks(params),
          teamsAPI.getTeams(teamParams),
        ])
        setTasks(unwrapResults(tasksResponse))
        setTeams(unwrapResults(teamsResponse))
      } catch (requestError) {
        setError('Search is unavailable right now.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [normalizedQuery])

  const filteredTasks = useMemo(() => tasks, [tasks])
  const filteredTeams = useMemo(() => teams, [teams])

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
        title="Find work and team spaces fast"
        description="Search across active tasks and teams without leaving the workspace flow."
        stats={[
          { label: 'Task index', value: tasks.length, caption: 'Searchable tasks' },
          { label: 'Team index', value: teams.length, caption: 'Searchable teams' },
          { label: 'Query mode', value: normalizedQuery ? 'Live' : 'Idle', caption: 'Filtering now' },
        ]}
        spotlight={{
          eyebrow: 'Command lens',
          title: 'A presentable search surface, not a plain input box.',
          description: 'This page is intentionally shaped like a workspace tool: fast query entry, immediate filtering, and separate result zones.',
          points: [
            { label: 'Current query', value: normalizedQuery || 'None' },
            { label: 'Visible results', value: filteredTasks.length + filteredTeams.length },
          ],
        }}
      />

      <div className="grid gap-6 xl:grid-cols-[0.72fr,1.28fr]">
        <section className="card fade-in">
          <label className="mb-2 block text-sm font-semibold text-emerald-950">Search query</label>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="input-field"
            placeholder="Search tasks, teams, statuses, or priorities"
          />
          <div className="mt-5 flex flex-wrap gap-2">
            {['priority', 'deadline', 'team', 'status', 'owner'].map((chip) => (
              <button key={chip} type="button" onClick={() => setQuery(chip)} className="micro-chip">
                {chip}
              </button>
            ))}
          </div>
          <div className="mt-5 rounded-[24px] bg-gradient-to-br from-emerald-500 to-teal-600 p-5 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-50/70">Result behavior</p>
            <p className="mt-3 text-lg font-semibold">Tasks and teams stay separated so your demos feel structured.</p>
          </div>
        </section>

        <section className="spotlight-panel fade-in text-white">
          <div className="relative z-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-50/70">Live feedback</p>
            <h2 className="mt-3 text-3xl font-bold">Search with context.</h2>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[22px] border border-white/12 bg-white/10 px-4 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-50/70">Tasks matching</p>
                <p className="mt-2 text-3xl font-bold">{filteredTasks.length}</p>
              </div>
              <div className="rounded-[22px] border border-white/12 bg-white/10 px-4 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-50/70">Teams matching</p>
                <p className="mt-2 text-3xl font-bold">{filteredTeams.length}</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Tasks</h2>
          <div className="mt-5 grid gap-3">
            {filteredTasks.length === 0 ? (
              <EmptyState title="No task matches" description="Try a different keyword, status, or team name." />
            ) : (
              filteredTasks.map((task) => (
                <Link key={task.id} to={`/tasks/${task.id}`} className="feature-tile">
                  <h3 className="text-lg font-bold text-emerald-950">{task.title}</h3>
                  <p className="mt-1 text-sm text-soft">
                    {task.team_name} • {toSentenceCase(task.status)} • Due {formatDate(task.due_date)}
                  </p>
                </Link>
              ))
            )}
          </div>
        </section>

        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Teams</h2>
          <div className="mt-5 grid gap-3">
            {filteredTeams.length === 0 ? (
              <EmptyState title="No team matches" description="Try a team name, slug, or part of its description." />
            ) : (
              filteredTeams.map((team) => (
                <Link key={team.id} to={`/teams/${team.id}/overview`} className="feature-tile">
                  <h3 className="text-lg font-bold text-emerald-950">{team.name}</h3>
                  <p className="mt-1 text-sm text-soft">{team.description || 'No description available yet.'}</p>
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
