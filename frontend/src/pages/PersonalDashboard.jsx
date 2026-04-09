import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { dashboardAPI, notificationsAPI, tasksAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, formatRelativeDate, toSentenceCase } from '../utils/formatters'

export default function PersonalDashboard() {
  const currentUser = useSelector((state) => state.auth.user)
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [tasks, setTasks] = useState([])
  const [overdue, setOverdue] = useState([])
  const [calendarItems, setCalendarItems] = useState([])
  const [notifications, setNotifications] = useState([])

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true)
      try {
        const [summaryResponse, tasksResponse, overdueResponse, calendarResponse, notificationResponse] = await Promise.all([
          dashboardAPI.getPersonalSummary(),
          dashboardAPI.getPersonalTasks({ page_size: 6 }),
          dashboardAPI.getPersonalOverdue({ page_size: 4 }),
          dashboardAPI.getPersonalCalendar({ page_size: 6 }),
          notificationsAPI.getNotifications({ page_size: 4 }),
        ])

        const summaryPayload = unwrapData(summaryResponse) || {}
        setSummary(summaryPayload.summary || {})
        setTasks(unwrapResults(tasksResponse))
        setOverdue(unwrapResults(overdueResponse))
        setCalendarItems(Array.isArray(unwrapData(calendarResponse)) ? unwrapData(calendarResponse) : [])
        setNotifications(unwrapResults(notificationResponse))
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  const dueSoon = useMemo(() => {
    return tasks.filter((task) => task.due_date).slice(0, 3)
  }, [tasks])

  if (loading) {
    return <LoadingState label="Preparing your personal dashboard" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Personal Dashboard"
        title={`Welcome back, ${currentUser?.first_name || currentUser?.name?.split(' ')[0] || 'there'}`}
        description="Your personal control center for tasks, deadlines, and the work that moves your day forward."
        actions={
          <div className="flex flex-wrap gap-3">
            <Link to="/tasks" className="btn-primary">
              Create task
            </Link>
            <Link to="/calendar" className="btn-secondary">
              View calendar
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Assigned to you" value={summary.assigned_tasks || 0} hint="Open tasks in your queue" />
        <StatCard label="Overdue" value={summary.overdue_tasks || 0} hint="Needs attention now" />
        <StatCard label="Due soon" value={summary.due_soon || 0} hint="Next 7 days" />
        <StatCard
          label="Completed this week"
          value={summary.completed_this_week || 0}
          hint="Progress tracked"
          accent="from-emerald-500 to-lime-500"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <section className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">My tasks</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">Focus for today</h2>
            </div>
            <Link to="/tasks" className="btn-secondary">
              Open tasks
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {tasks.length === 0 ? (
              <EmptyState
                title="No tasks yet"
                description="Create your first personal task to start building momentum."
                action={
                  <Link to="/tasks" className="btn-primary">
                    Create task
                  </Link>
                }
              />
            ) : (
              tasks.map((task) => (
                <Link key={task.id} to={`/tasks/${task.id}`} className="feature-tile p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-950">{task.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {toSentenceCase(task.status)} • {toSentenceCase(task.priority)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-emerald-50/80 px-4 py-2 text-xs font-semibold text-emerald-800">
                      {task.due_date ? formatRelativeDate(task.due_date) : 'No due date'}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </section>

        <div className="space-y-6">
          <section className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Overdue</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-950">Needs attention</h3>
              </div>
              <span className="stat-chip">{overdue.length}</span>
            </div>
            <div className="mt-4 space-y-2">
              {overdue.length === 0 ? (
                <p className="text-sm text-slate-500">You are all caught up.</p>
              ) : (
                overdue.map((task) => (
                  <Link key={task.id} to={`/tasks/${task.id}`} className="feature-tile p-3">
                    <p className="text-sm font-semibold text-slate-950">{task.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{formatDate(task.due_date)}</p>
                  </Link>
                ))
              )}
            </div>
          </section>

          <section className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Calendar</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-950">Upcoming deadlines</h3>
              </div>
              <Link to="/calendar" className="btn-secondary">
                View all
              </Link>
            </div>
            <div className="mt-4 space-y-2">
              {calendarItems.length === 0 ? (
                <p className="text-sm text-slate-500">No deadlines scheduled yet.</p>
              ) : (
                calendarItems.slice(0, 4).map((item) => (
                  <div key={item.task_id || item.id} className="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                    <p className="text-sm font-semibold text-slate-950">{item.title || item.task_title}</p>
                    <p className="mt-1 text-xs text-slate-500">{formatRelativeDate(item.due_date || item.date)}</p>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notifications</p>
                <h3 className="mt-2 text-xl font-semibold text-slate-950">Recent updates</h3>
              </div>
              <Link to="/notifications" className="btn-secondary">
                See all
              </Link>
            </div>
            <div className="mt-4 space-y-2">
              {notifications.length === 0 ? (
                <p className="text-sm text-slate-500">No new notifications yet.</p>
              ) : (
                notifications.map((notification) => (
                  <div key={notification.id} className="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                    <p className="text-sm font-semibold text-slate-950">{notification.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{notification.message}</p>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
