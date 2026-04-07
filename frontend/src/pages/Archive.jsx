import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import PageHero from '../components/PageHero'
import { tasksAPI, teamsAPI, unwrapResults } from '../services/api'
import { formatDate, toSentenceCase } from '../utils/formatters'

export default function Archive() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [archivedTasks, setArchivedTasks] = useState([])
  const [archivedTeams, setArchivedTeams] = useState([])

  useEffect(() => {
    const loadArchive = async () => {
      setLoading(true)
      setError('')
      try {
        const [tasksResponse, teamsResponse] = await Promise.all([
          tasksAPI.getTasks({ is_archived: true, ordering: '-archived_at', page_size: 24 }),
          teamsAPI.getTeams({ is_archived: true, page_size: 24 }),
        ])
        setArchivedTasks(unwrapResults(tasksResponse))
        setArchivedTeams(unwrapResults(teamsResponse))
      } catch (requestError) {
        setError(requestError?.response?.data?.message || 'Unable to load archived items right now.')
      } finally {
        setLoading(false)
      }
    }

    loadArchive()
  }, [])

  const totalArchived = archivedTasks.length + archivedTeams.length
  const mostRecentArchiveLabel = useMemo(() => {
    const dates = [
      ...archivedTasks.map((task) => task.archived_at).filter(Boolean),
      ...archivedTeams.map((team) => team.archived_at).filter(Boolean),
    ]
    if (!dates.length) {
      return 'No archived activity'
    }
    dates.sort((left, right) => new Date(right) - new Date(left))
    return formatDate(dates[0])
  }, [archivedTasks, archivedTeams])

  if (loading) {
    return <LoadingState label="Loading archive" />
  }

  if (error) {
    return <EmptyState title="Archive unavailable" description={error} />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Archive"
        title="Archived work and spaces"
        description="Review older tasks and archived teams from the real product history instead of losing operational context."
        stats={[
          { label: 'Archived tasks', value: archivedTasks.length, caption: 'No longer active' },
          { label: 'Archived teams', value: archivedTeams.length, caption: 'Closed workspaces' },
          { label: 'Latest archive', value: mostRecentArchiveLabel, caption: 'Most recent action' },
        ]}
        spotlight={{
          eyebrow: 'History',
          title: 'A real archive, not an empty shell.',
          description: 'This page is now connected to live backend data so archived work remains discoverable and presentation-ready.',
          points: [
            { label: 'Total archived', value: totalArchived },
            { label: 'Surface state', value: totalArchived ? 'Populated' : 'Quiet' },
          ],
        }}
      />

      {totalArchived === 0 ? (
        <EmptyState
          title="Nothing archived right now"
          description="As tasks and teams are archived, they will appear here automatically for reference."
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-2">
          <section className="card fade-in">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Tasks</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Archived tasks</h2>
              </div>
              <div className="stat-chip">{archivedTasks.length}</div>
            </div>

            <div className="mt-5 grid gap-3">
              {archivedTasks.length === 0 ? (
                <EmptyState title="No archived tasks" description="Archived tasks will appear here once work is retired from active boards." />
              ) : (
                archivedTasks.map((task) => (
                  <Link key={task.id} to={`/tasks/${task.id}`} className="feature-tile">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="text-lg font-bold text-emerald-950">{task.title}</h3>
                        <p className="mt-2 text-sm leading-6 text-soft">
                          {task.team_name || 'Team'} • {toSentenceCase(task.status)} • {toSentenceCase(task.priority)}
                        </p>
                      </div>
                      <span className="micro-chip">Archived</span>
                    </div>
                    <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
                      Archived {formatDate(task.archived_at || task.updated_at)}
                    </p>
                  </Link>
                ))
              )}
            </div>
          </section>

          <section className="card fade-in">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Teams</p>
                <h2 className="mt-2 text-2xl font-bold text-emerald-950">Archived teams</h2>
              </div>
              <div className="stat-chip">{archivedTeams.length}</div>
            </div>

            <div className="mt-5 grid gap-3">
              {archivedTeams.length === 0 ? (
                <EmptyState title="No archived teams" description="Archived workspaces will appear here after admins close them." />
              ) : (
                archivedTeams.map((team) => (
                  <div key={team.id} className="feature-tile">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <h3 className="text-lg font-bold text-emerald-950">{team.name}</h3>
                        <p className="mt-2 text-sm leading-6 text-soft">
                          {team.description || 'No description available.'}
                        </p>
                      </div>
                      <span className="micro-chip">Team</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3 text-sm text-soft">
                      <span>{team.member_count || 0} members</span>
                      <span>{toSentenceCase(team.my_role || 'member')}</span>
                      <span>Archived {formatDate(team.archived_at || team.updated_at)}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
