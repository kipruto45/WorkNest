import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import Forbidden from './Forbidden'
import { tasksAPI, teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { toSentenceCase } from '../utils/formatters'
import { resolveMembershipRole } from '../utils/permissions'

const panelClass = 'rounded-[26px] border border-slate-200 bg-white shadow-[0_10px_28px_rgba(15,23,42,0.05)]'
const cardClass = 'rounded-[22px] border border-slate-200 bg-[#fcfcfb]'

const triggerOptions = [
  { value: 'task_created', label: 'Task created' },
  { value: 'task_assigned', label: 'Task assigned' },
  { value: 'task_overdue', label: 'Task overdue' },
  { value: 'task_status_changed', label: 'Status changed' },
  { value: 'invite_accepted', label: 'Invite accepted' },
  { value: 'milestone_overdue', label: 'Milestone overdue' },
]

const actionOptions = [
  { value: 'create_notification', label: 'Create in-app notification' },
  { value: 'send_email', label: 'Send email' },
  { value: 'assign_user', label: 'Assign user' },
  { value: 'change_status', label: 'Change status' },
  { value: 'add_label', label: 'Add label' },
  { value: 'create_follow_up_task', label: 'Create follow-up task' },
  { value: 'notify_admin', label: 'Notify admin' },
]

export default function TeamAutomationRules() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [rules, setRules] = useState([])
  const [draft, setDraft] = useState({
    name: '',
    trigger_type: 'task_created',
    action_type: 'create_notification',
    conditions: '{}',
    action_payload: '{}',
    is_active: true,
  })
  const [saving, setSaving] = useState(false)

  const loadRules = useCallback(async () => {
    setLoading(true)
    try {
      const [teamResponse, rulesResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        tasksAPI.getAutomationRules(teamId, { page_size: 50 }),
      ])
      setTeam(unwrapData(teamResponse))
      setRules(unwrapResults(rulesResponse))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load automation rules.')
      setTeam(null)
      setRules([])
    } finally {
      setLoading(false)
    }
  }, [teamId])

  useEffect(() => {
    if (teamId) {
      loadRules()
    }
  }, [loadRules, teamId])

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!draft.name.trim()) {
      toast.error('Rule name is required.')
      return
    }
    setSaving(true)
    try {
      await tasksAPI.createAutomationRule(teamId, {
        name: draft.name.trim(),
        trigger_type: draft.trigger_type,
        action_type: draft.action_type,
        conditions: JSON.parse(draft.conditions || '{}'),
        action_payload: JSON.parse(draft.action_payload || '{}'),
        is_active: draft.is_active,
      })
      setDraft({
        name: '',
        trigger_type: 'task_created',
        action_type: 'create_notification',
        conditions: '{}',
        action_payload: '{}',
        is_active: true,
      })
      await loadRules()
      toast.success('Automation rule created.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to create automation rule.')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (rule) => {
    try {
      await tasksAPI.updateAutomationRule(teamId, rule.id, { is_active: !rule.is_active })
      await loadRules()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to update rule status.')
    }
  }

  const handleDelete = async (rule) => {
    if (!window.confirm(`Delete "${rule.name}"?`)) return
    try {
      await tasksAPI.deleteAutomationRule(teamId, rule.id)
      await loadRules()
      toast.success('Automation rule deleted.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to delete automation rule.')
    }
  }

  if (loading) {
    return <LoadingState label="Loading automation rules" />
  }

  const canManageAutomation = resolveMembershipRole(team) === 'admin'
  if (!canManageAutomation) {
    return <Forbidden />
  }

  const activeRules = rules.filter((rule) => rule.is_active).length
  const pausedRules = rules.filter((rule) => !rule.is_active).length

  return (
    <div className="space-y-6">
      <section className={`${panelClass} overflow-hidden`}>
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.1fr,0.9fr] lg:px-8 lg:py-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Automation</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              {(team?.name || 'Team')} workflow rules
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
              Build event-based automations to reduce manual follow-up and keep execution consistent.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link to={`/teams/${teamId}/overview`} className="btn-secondary">
                Team dashboard
              </Link>
              <Link to={`/teams/${teamId}/activity`} className="btn-secondary">
                Activity log
              </Link>
            </div>
          </div>
          <div className={`${cardClass} p-4`}>
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile label="Rules" value={rules.length} note="Configured total" />
              <SummaryTile label="Active" value={activeRules} note="Running now" />
              <SummaryTile label="Paused" value={pausedRules} note="Disabled manually" />
            </div>
          </div>
        </div>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <h2 className="text-xl font-semibold text-slate-950">Create a rule</h2>
        <p className="mt-2 text-sm text-slate-600">Use a clear when/then structure with explicit JSON conditions and payload.</p>
        <form onSubmit={handleCreate} className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-slate-900 md:col-span-2">
            Rule name
            <input
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
              className="input-field mt-2"
              placeholder="Notify admins when a task is overdue"
            />
          </label>
          <label className="text-sm font-semibold text-slate-900">
            Trigger
            <select
              value={draft.trigger_type}
              onChange={(event) => setDraft((current) => ({ ...current, trigger_type: event.target.value }))}
              className="input-field mt-2"
            >
              {triggerOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-900">
            Action
            <select
              value={draft.action_type}
              onChange={(event) => setDraft((current) => ({ ...current, action_type: event.target.value }))}
              className="input-field mt-2"
            >
              {actionOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-semibold text-slate-900 md:col-span-1">
            Conditions (JSON)
            <textarea
              value={draft.conditions}
              onChange={(event) => setDraft((current) => ({ ...current, conditions: event.target.value }))}
              className="input-field mt-2 min-h-[120px] font-mono text-xs"
            />
          </label>
          <label className="text-sm font-semibold text-slate-900 md:col-span-1">
            Action payload (JSON)
            <textarea
              value={draft.action_payload}
              onChange={(event) => setDraft((current) => ({ ...current, action_payload: event.target.value }))}
              className="input-field mt-2 min-h-[120px] font-mono text-xs"
            />
          </label>
          <label className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <input
              type="checkbox"
              checked={draft.is_active}
              onChange={() => setDraft((current) => ({ ...current, is_active: !current.is_active }))}
            />
            Activate immediately
          </label>
          <div className="md:col-span-2">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Creating...' : 'Create rule'}
            </button>
          </div>
        </form>
      </section>

      <section className={`${panelClass} p-6 lg:p-7`}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Rules library</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-950">Current automation coverage</h2>
          </div>
          <p className="text-sm text-slate-500">{rules.length} rules</p>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {rules.length === 0 ? (
          <EmptyState title="No rules yet" description="Create your first automation to reduce manual coordination." />
        ) : (
          rules.map((rule) => (
            <div key={rule.id} className={`${cardClass} p-5 transition-shadow hover:shadow-[0_12px_30px_rgba(15,23,42,0.08)]`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                    {toSentenceCase(rule.trigger_type?.replaceAll('_', ' '))}
                  </p>
                  <h3 className="mt-2 text-xl font-semibold text-emerald-950">{rule.name}</h3>
                  <p className="mt-2 text-sm text-slate-600">Action: {toSentenceCase(rule.action_type?.replaceAll('_', ' '))}</p>
                </div>
                <button type="button" onClick={() => handleDelete(rule)} className="btn-ghost">
                  Delete
                </button>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Conditions</p>
                  <pre className="mt-2 overflow-x-auto text-xs text-slate-600">{JSON.stringify(rule.conditions || {}, null, 2)}</pre>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white px-3 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Payload</p>
                  <pre className="mt-2 overflow-x-auto text-xs text-slate-600">{JSON.stringify(rule.action_payload || {}, null, 2)}</pre>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button type="button" onClick={() => handleToggle(rule)} className="btn-secondary">
                  {rule.is_active ? 'Disable' : 'Enable'}
                </button>
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {rule.is_active ? 'Active' : 'Paused'}
                </span>
              </div>
            </div>
          ))
        )}
        </div>
      </section>
    </div>
  )
}

function SummaryTile({ label, value, note }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{note}</p>
    </div>
  )
}
