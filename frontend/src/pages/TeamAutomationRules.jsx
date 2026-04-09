import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { tasksAPI, unwrapResults } from '../services/api'

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
      const response = await tasksAPI.getAutomationRules(teamId, { page_size: 50 })
      setRules(unwrapResults(response))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load automation rules.')
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

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Automation"
        title="Let the workflow move on its own"
        description="Create lightweight rules that respond to key events without adding process overhead."
        stats={[
          { label: 'Active rules', value: rules.filter((rule) => rule.is_active).length, caption: 'Running now' },
          { label: 'Paused rules', value: rules.filter((rule) => !rule.is_active).length, caption: 'Currently disabled' },
        ]}
      />

      <section className="card fade-in">
        <h2 className="text-2xl font-bold text-emerald-950">Create a rule</h2>
        <p className="mt-2 text-sm text-soft">Use a clear When/Then structure to keep automation understandable.</p>
        <form onSubmit={handleCreate} className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="text-sm font-semibold text-emerald-950 md:col-span-2">
            Rule name
            <input
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
              className="input-field mt-2"
              placeholder="Notify admins when a task is overdue"
            />
          </label>
          <label className="text-sm font-semibold text-emerald-950">
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
          <label className="text-sm font-semibold text-emerald-950">
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
          <label className="text-sm font-semibold text-emerald-950 md:col-span-1">
            Conditions (JSON)
            <textarea
              value={draft.conditions}
              onChange={(event) => setDraft((current) => ({ ...current, conditions: event.target.value }))}
              className="input-field mt-2 min-h-[120px] font-mono text-xs"
            />
          </label>
          <label className="text-sm font-semibold text-emerald-950 md:col-span-1">
            Action payload (JSON)
            <textarea
              value={draft.action_payload}
              onChange={(event) => setDraft((current) => ({ ...current, action_payload: event.target.value }))}
              className="input-field mt-2 min-h-[120px] font-mono text-xs"
            />
          </label>
          <label className="flex items-center gap-2 text-sm font-semibold text-emerald-950">
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

      <section className="grid gap-4 lg:grid-cols-2">
        {rules.length === 0 ? (
          <EmptyState title="No rules yet" description="Create your first automation to reduce manual coordination." />
        ) : (
          rules.map((rule) => (
            <div key={rule.id} className="card fade-in">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                    {rule.trigger_type?.replaceAll('_', ' ')}
                  </p>
                  <h3 className="mt-2 text-xl font-semibold text-emerald-950">{rule.name}</h3>
                  <p className="mt-2 text-sm text-soft">Action: {rule.action_type?.replaceAll('_', ' ')}</p>
                </div>
                <button type="button" onClick={() => handleDelete(rule)} className="btn-ghost">
                  Delete
                </button>
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
      </section>
    </div>
  )
}
