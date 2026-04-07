import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { fetchNotifications, markAllAsRead, markAsRead, markAsUnread } from '../features/notificationsSlice'
import { formatDate, toSentenceCase } from '../utils/formatters'
import { buildNotificationLink } from '../utils/notificationLinks'

export default function Notifications() {
  const dispatch = useDispatch()
  const { items: notifications, loading } = useSelector((state) => state.notifications)

  useEffect(() => {
    dispatch(fetchNotifications())
  }, [dispatch])

  const unreadCount = useMemo(() => notifications.filter((item) => !item.is_read).length, [notifications])

  const handleMarkAll = async () => {
    await dispatch(markAllAsRead())
  }

  const handleToggleRead = async (notification) => {
    if (notification.is_read) {
      await dispatch(markAsUnread(notification.id))
    } else {
      await dispatch(markAsRead(notification.id))
    }
  }

  if (loading) {
    return <LoadingState label="Loading notifications" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Notifications"
        title="Activity pulse"
        description="Mentions, assignments, comments, and workflow signals gathered into one calm, readable stream."
        stats={[
          { label: 'Total', value: notifications.length, caption: 'Recent events' },
          { label: 'Unread', value: unreadCount, caption: 'Needs your attention' },
          { label: 'Read', value: notifications.length - unreadCount, caption: 'Already triaged' },
        ]}
        spotlight={{
          eyebrow: 'Signal stream',
          title: 'Readable enough for live walkthroughs.',
          description: 'This screen turns backend notification data into a cleaner, more premium activity surface.',
          points: [
            { label: 'Stream state', value: unreadCount ? 'Active' : 'Quiet' },
            { label: 'Bulk action', value: 'Mark all read' },
          ],
        }}
        actions={
          <>
            <button type="button" onClick={handleMarkAll} className="btn-secondary">
              Mark all read
            </button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Total items" value={notifications.length} hint="Recent account activity" />
        <StatCard label="Unread" value={unreadCount} hint="Needs your attention" accent="from-emerald-500 to-green-600" />
        <StatCard
          label="Read"
          value={notifications.length - unreadCount}
          hint="Already triaged"
          accent="from-teal-500 to-emerald-600"
        />
      </div>

      {notifications.length === 0 ? (
        <EmptyState
          title="No notifications yet"
          description="Mentions, task assignments, and reminders will land here as your team starts collaborating."
        />
      ) : (
        <div className="grid gap-4">
          {notifications.map((notification) => (
            <div key={notification.id} className="feature-tile fade-in">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="stat-chip">{toSentenceCase(notification.type)}</div>
                  <h3 className="mt-3 text-lg font-bold text-emerald-950">{notification.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-soft">{notification.message}</p>
                  <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                    {formatDate(notification.created_at, {
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </p>
                </div>

                <div className="flex flex-col gap-3 lg:min-w-[210px]">
                  <div className={`rounded-2xl px-4 py-3 text-sm font-semibold ${notification.is_read ? 'bg-slate-100 text-slate-500' : 'bg-emerald-100 text-emerald-800'}`}>
                    {notification.is_read ? 'Already read' : 'Unread and active'}
                  </div>
                  <Link to={buildNotificationLink(notification)} className="btn-secondary">
                    Open context
                  </Link>
                  <button type="button" onClick={() => handleToggleRead(notification)} className="btn-ghost">
                    {notification.is_read ? 'Mark unread' : 'Mark read'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
