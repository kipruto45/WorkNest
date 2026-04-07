import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { auditLogsAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, toSentenceCase } from '../utils/formatters'

export default function TeamActivity() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [logs, setLogs] = useState([])

  useEffect(() => {
    const loadLogs = async () => {
      setLoading(true)
      try {
        const [teamResponse, logsResponse] = await Promise.all([
          teamsAPI.getTeam(teamId),
          auditLogsAPI.getForTeam(teamId),
        ])
        setTeam(unwrapData(teamResponse))
        setLogs(unwrapResults(logsResponse))
      } finally {
        setLoading(false)
      }
    }

    loadLogs()
  }, [teamId])

  if (loading || !team) {
    return <LoadingState label="Loading team activity" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Activity Feed"
        title={`${team.name} audit trail`}
        description="A reliable record of workspace actions, useful for transparency, governance, and operational memory."
        stats={[
          { label: 'Log entries', value: logs.length, caption: 'Auditable events' },
          { label: 'Actors', value: new Set(logs.map((log) => log.actor?.id).filter(Boolean)).size, caption: 'Unique contributors' },
          { label: 'Mode', value: logs.length ? 'Active' : 'Quiet', caption: 'Current stream state' },
        ]}
        spotlight={{
          eyebrow: 'Transparency',
          title: 'An activity trail that feels presentable.',
          description: 'Instead of a plain table, the audit trail reads like a curated timeline for better storytelling during demos.',
          points: [
            { label: 'Latest event', value: logs[0]?.action ? toSentenceCase(logs[0].action) : 'None yet' },
            { label: 'Purpose', value: 'Traceability' },
          ],
        }}
      />

      {logs.length === 0 ? (
        <EmptyState
          title="No activity recorded yet"
          description="Important team actions will appear here as members edit tasks, manage invitations, and change permissions."
        />
      ) : (
        <div className="relative space-y-4 pl-4">
          <div className="absolute left-[11px] top-0 h-full w-px bg-emerald-200" />
          {logs.map((log) => (
            <div key={log.id} className="card relative fade-in">
              <div className="absolute -left-[30px] top-6 timeline-dot" />
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="stat-chip">{toSentenceCase(log.action)}</div>
                  <h3 className="mt-3 text-lg font-bold text-emerald-950">{log.target_repr || 'Workspace item'}</h3>
                  <p className="mt-2 text-sm text-soft">
                    {log.actor?.name || 'System'} acted on {toSentenceCase(log.target_type || 'resource')}
                  </p>
                </div>
                <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
                  {formatDate(log.created_at, {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
