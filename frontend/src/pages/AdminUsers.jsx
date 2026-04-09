import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import EmptyState from '../components/EmptyState'
import LoadingState from '../components/LoadingState'
import { usersAPI, unwrapData, unwrapResults } from '../services/api'

export default function AdminUsers() {
  const navigate = useNavigate()
  const { userId } = useParams()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [filters, setFilters] = useState({ q: '', account_type: '', is_active: '' })
  const [users, setUsers] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)

  const loadUsers = useCallback(async (selectedId = userId) => {
    setLoading(true)
    try {
      const params = {
        q: filters.q || undefined,
        account_type: filters.account_type || undefined,
        is_active: filters.is_active || undefined,
        page_size: 24,
      }
      const response = await usersAPI.searchAdminUsers(params)
      const items = unwrapResults(response)
      setUsers(items)

      const targetId = selectedId || items[0]?.id
      if (targetId) {
        const detailResponse = await usersAPI.getAdminUser(targetId)
        setSelectedUser(unwrapData(detailResponse))
      } else {
        setSelectedUser(null)
      }
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load users right now.')
    } finally {
      setLoading(false)
    }
  }, [filters.account_type, filters.is_active, filters.q, userId])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleFilterChange = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  const applyFilters = async (event) => {
    event.preventDefault()
    await loadUsers()
  }

  const openUser = async (id) => {
    navigate(`/admin/users/${id}`)
    try {
      const response = await usersAPI.getAdminUser(id)
      setSelectedUser(unwrapData(response))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load the selected user.')
    }
  }

  const handleStatusUpdate = async (payload) => {
    if (!selectedUser) return
    setSaving(true)
    try {
      const response = await usersAPI.updateAdminUser(selectedUser.id, payload)
      const updated = unwrapData(response)
      setSelectedUser(updated)
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      toast.success('User updated.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update that user.')
    } finally {
      setSaving(false)
    }
  }

  const summary = useMemo(
    () => ({
      total: users.length,
      active: users.filter((user) => user.is_active).length,
      verified: users.filter((user) => user.email_verified).length,
    }),
    [users]
  )

  if (loading) {
    return <LoadingState label="Loading user management" />
  }

  return (
    <div className="space-y-6">
      <section className="hero-panel fade-in">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Admin users</p>
            <h1 className="mt-3 font-display text-4xl font-bold text-emerald-950">Manage users with account and workload context</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-soft">
              Review activation state, verification, team footprint, and recent account activity.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label="Visible users" value={summary.total} />
            <StatTile label="Active accounts" value={summary.active} />
            <StatTile label="Verified emails" value={summary.verified} />
          </div>
        </div>
      </section>

      <form onSubmit={applyFilters} className="card fade-in">
        <div className="grid gap-4 md:grid-cols-[1.2fr,0.8fr,0.8fr,auto]">
          <input
            value={filters.q}
            onChange={(event) => handleFilterChange('q', event.target.value)}
            className="input-field"
            placeholder="Search by name or email"
          />
          <select value={filters.account_type} onChange={(event) => handleFilterChange('account_type', event.target.value)} className="input-field">
            <option value="">All account types</option>
            <option value="personal">Personal</option>
            <option value="team">Team</option>
          </select>
          <select value={filters.is_active} onChange={(event) => handleFilterChange('is_active', event.target.value)} className="input-field">
            <option value="">Any status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
          <button type="submit" className="btn-primary">
            Apply filters
          </button>
        </div>
      </form>

      <div className="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
        <section className="card fade-in">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-emerald-950">Accounts</h2>
            <Link to="/admin" className="btn-secondary">
              Back to admin
            </Link>
          </div>

          <div className="mt-5 space-y-3">
            {users.length === 0 ? (
              <EmptyState title="No users matched" description="Try a different search or broader filter." />
            ) : (
              users.map((user) => (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => openUser(user.id)}
                  className={`feature-tile w-full text-left ${selectedUser?.id === user.id ? 'ring-2 ring-emerald-300' : ''}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-emerald-950">{user.name || user.email}</p>
                      <p className="mt-1 text-sm text-soft">{user.email}</p>
                    </div>
                    <span className="micro-chip">{user.is_active ? 'Active' : 'Inactive'}</span>
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    {user.team_memberships?.length || 0} teams • {user.presence?.label || 'No recent activity'}
                  </p>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="card fade-in">
          {!selectedUser ? (
            <EmptyState title="Select a user" description="Choose an account from the list to inspect details and apply moderation actions." />
          ) : (
            <div className="space-y-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">User detail</p>
                  <h2 className="mt-2 text-3xl font-bold text-emerald-950">{selectedUser.name || selectedUser.email}</h2>
                  <p className="mt-2 text-sm text-soft">{selectedUser.email}</p>
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => handleStatusUpdate({ is_active: !selectedUser.is_active })}
                    className="btn-secondary"
                    disabled={saving}
                  >
                    {saving ? 'Saving…' : selectedUser.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <StatTile label="Account type" value={selectedUser.account_type} />
                <StatTile label="Email" value={selectedUser.email_verified ? 'Verified' : 'Pending'} />
                <StatTile label="Presence" value={selectedUser.presence?.label || 'Unknown'} />
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="feature-tile">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Memberships</p>
                  <div className="mt-4 space-y-3">
                    {(selectedUser.team_memberships || []).length === 0 ? (
                      <p className="text-sm text-soft">No active team memberships.</p>
                    ) : (
                      selectedUser.team_memberships.map((membership) => (
                        <div key={membership.id} className="rounded-2xl border border-slate-200 bg-white/70 px-4 py-3">
                          <p className="font-semibold text-emerald-950">{membership.team_name}</p>
                          <p className="mt-1 text-sm text-soft">{membership.role}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="feature-tile">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workload snapshot</p>
                  <div className="mt-4 grid gap-3">
                    <MetricRow label="Assigned tasks" value={selectedUser.stats?.assigned_tasks || 0} />
                    <MetricRow label="Completed tasks" value={selectedUser.stats?.completed_tasks || 0} />
                    <MetricRow label="Overdue tasks" value={selectedUser.stats?.overdue_tasks || 0} />
                    <MetricRow label="2FA state" value={selectedUser.two_factor_status || 'disabled'} />
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function StatTile({ label, value }) {
  return (
    <div className="feature-tile">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{label}</p>
      <p className="mt-3 text-2xl font-bold text-emerald-950">{value}</p>
    </div>
  )
}

function MetricRow({ label, value }) {
  return (
    <div className="metric-strip">
      <span className="text-sm text-soft">{label}</span>
      <span className="font-semibold text-emerald-950">{value}</span>
    </div>
  )
}
