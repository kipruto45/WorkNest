import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import { dashboardAPI, teamsAPI, unwrapData } from '../services/api'
import { toSentenceCase } from '../utils/formatters'

function DistributionCard({ title, items, valueKey }) {
  return (
    <section className="card fade-in">
      <h2 className="text-2xl font-bold text-emerald-950">{title}</h2>
      <div className="mt-5 grid gap-3">
        {items.map((item) => (
          <div key={item.label || item.status || item.priority || item.user_name} className="glass-panel p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-semibold text-emerald-950">
                {toSentenceCase(item.label || item.status || item.priority || item.user_name || item.member_name || 'Item')}
              </p>
              <p className="text-lg font-bold text-emerald-800">{item[valueKey] ?? item.count ?? 0}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function TeamAnalytics() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [progress, setProgress] = useState({})
  const [workload, setWorkload] = useState([])
  const [statuses, setStatuses] = useState([])
  const [priorities, setPriorities] = useState([])

  useEffect(() => {
    const loadAnalytics = async () => {
      setLoading(true)
      try {
        const [teamResponse, progressResponse, workloadResponse, statusResponse, priorityResponse] = await Promise.all([
          teamsAPI.getTeam(teamId),
          dashboardAPI.getTeamProgress(teamId),
          dashboardAPI.getTeamWorkload(teamId),
          dashboardAPI.getTeamStatusDistribution(teamId),
          dashboardAPI.getTeamPriorityDistribution(teamId),
        ])

        setTeam(unwrapData(teamResponse))
        setProgress(unwrapData(progressResponse) || {})
        setWorkload(unwrapData(workloadResponse)?.workload || [])
        setStatuses(unwrapData(statusResponse)?.status_distribution || [])
        setPriorities(unwrapData(priorityResponse)?.priority_distribution || [])
      } finally {
        setLoading(false)
      }
    }

    loadAnalytics()
  }, [teamId])

  const headlineStats = useMemo(
    () => [
      { label: 'Completion rate', value: `${progress.completion_rate ?? 0}%` },
      { label: 'Open work', value: progress.open_tasks ?? 0 },
      { label: 'Done', value: progress.completed_tasks ?? 0 },
    ],
    [progress]
  )

  if (loading || !team) {
    return <LoadingState label="Loading team analytics" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Team Analytics"
        title={`${team.name} performance`}
        description="Read the health of execution across workload, status mix, priority balance, and completion momentum."
        stats={[
          { label: 'Completion', value: `${progress.completion_rate ?? 0}%`, caption: 'Overall delivery rate' },
          { label: 'Open work', value: progress.open_tasks ?? 0, caption: 'Still active' },
          { label: 'Closed', value: progress.completed_tasks ?? 0, caption: 'Finished tasks' },
        ]}
        spotlight={{
          eyebrow: 'Metrics',
          title: 'Analytics that help your presentation land.',
          description: 'This page is structured to show workload balance, status distribution, and priority pressure without feeling like a raw report dump.',
          points: [
            { label: 'Workload rows', value: workload.length },
            { label: 'Status buckets', value: statuses.length },
          ],
        }}
      />

      <div className="grid gap-4 md:grid-cols-3">
        {headlineStats.map((stat) => (
          <div key={stat.label} className="card fade-in">
            <p className="text-sm text-soft">{stat.label}</p>
            <p className="mt-2 text-3xl font-bold text-emerald-950">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <DistributionCard title="Workload" items={workload} valueKey="task_count" />
        <DistributionCard title="Status Mix" items={statuses} valueKey="count" />
        <DistributionCard title="Priority Mix" items={priorities} valueKey="count" />
      </div>
    </div>
  )
}
