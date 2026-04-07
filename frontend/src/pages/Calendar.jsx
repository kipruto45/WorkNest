import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { dashboardAPI, unwrapData } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

export default function Calendar() {
  const [loading, setLoading] = useState(true)
  const [events, setEvents] = useState([])

  useEffect(() => {
    const loadCalendar = async () => {
      try {
        const response = await dashboardAPI.getPersonalCalendar()
        const payload = unwrapData(response)
        setEvents(Array.isArray(payload) ? payload : [])
      } finally {
        setLoading(false)
      }
    }

    loadCalendar()
  }, [])

  const groupedEvents = useMemo(() => {
    return events.reduce((accumulator, event) => {
      const key = formatDate(event.due_date)
      accumulator[key] = accumulator[key] || []
      accumulator[key].push(event)
      return accumulator
    }, {})
  }, [events])

  const dueThisWeekCount = useMemo(() => {
    const now = new Date()
    const weekAhead = new Date()
    weekAhead.setDate(now.getDate() + 7)

    return events.filter((event) => {
      const dueDate = new Date(event.due_date)
      return dueDate >= now && dueDate <= weekAhead
    }).length
  }, [events])

  if (loading) {
    return <LoadingState label="Loading calendar" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Calendar"
        title="Deadline radar"
        description="A date-based view of your upcoming workload so due dates stop sneaking up on the team."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Upcoming items" value={events.length} hint="Tracked deadlines in view" />
        <StatCard
          label="Due this week"
          value={dueThisWeekCount}
          hint="Immediate focus zone"
        />
        <StatCard
          label="Teams represented"
          value={new Set(events.map((event) => event.team?.id || event.team?.name).filter(Boolean)).size}
          hint="Cross-team visibility"
          accent="from-lime-500 to-emerald-600"
        />
      </div>

      {events.length === 0 ? (
        <EmptyState
          title="Nothing scheduled yet"
          description="Deadlines and dated work will appear here once tasks are planned with due dates."
        />
      ) : (
        <div className="grid gap-4">
          {Object.entries(groupedEvents).map(([date, items]) => (
            <div key={date} className="card fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Calendar day</p>
                  <h3 className="mt-2 text-2xl font-bold text-emerald-950">{date}</h3>
                </div>
                <div className="stat-chip">{items.length} items</div>
              </div>

              <div className="mt-5 grid gap-3">
                {items.map((event) => (
                  <Link key={event.task_id} to={event.task_id ? `/tasks/${event.task_id}` : '/tasks'} className="glass-panel p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <h4 className="text-lg font-bold text-emerald-950">{event.title}</h4>
                        <p className="mt-1 text-sm text-soft">
                          {event.team?.name || 'Personal'} • {toSentenceCase(event.status || 'scheduled')}
                        </p>
                      </div>
                      <div className="rounded-2xl bg-emerald-50/80 px-4 py-3 text-sm text-emerald-800">
                        {formatRelativeDate(event.due_date)}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
