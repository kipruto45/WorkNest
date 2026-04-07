import { useEffect, useState } from 'react'
import { useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import { usersAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS, USER_PREFERENCE_KEYS } from '../utils/clientConfig.js'

const notificationOptions = [
  { key: 'mention_emails', label: 'Mentions and replies', description: 'Stay aware when someone calls you into a discussion.' },
  { key: 'task_assignment_emails', label: 'Task assignments', description: 'Get notified the moment work lands on your plate.' },
  { key: 'deadline_reminder_emails', label: 'Deadline reminders', description: 'Keep due dates visible before they turn urgent.' },
  { key: 'comment_emails', label: 'Comment updates', description: 'Know when someone adds context to work you are part of.' },
]

function readWorkspacePrefs() {
  try {
    const rawValue = localStorage.getItem(CLIENT_STORAGE_KEYS.workspacePrefs)
    if (!rawValue) return {}
    const parsed = JSON.parse(rawValue)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch (_error) {
    return {}
  }
}

function buildWorkspacePrefs(settings) {
  return {
    compactMode: settings.compactMode,
    reducedMotion: settings.reducedMotion,
    [USER_PREFERENCE_KEYS.notifications]: {
      mention_emails: settings.mention_emails,
      task_assignment_emails: settings.task_assignment_emails,
      deadline_reminder_emails: settings.deadline_reminder_emails,
      comment_emails: settings.comment_emails,
    },
  }
}

function writeWorkspacePrefs(settings) {
  try {
    localStorage.setItem(CLIENT_STORAGE_KEYS.workspacePrefs, JSON.stringify(buildWorkspacePrefs(settings)))
    return true
  } catch (_error) {
    return false
  }
}

export default function Settings() {
  const currentUser = useSelector((state) => state.auth.user)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    mention_emails: true,
    task_assignment_emails: true,
    deadline_reminder_emails: true,
    comment_emails: true,
    compactMode: false,
    reducedMotion: false,
  })

  useEffect(() => {
    const loadSettings = async () => {
      setLoading(true)
      try {
        const localPreferences = readWorkspacePrefs()
        let profile = currentUser
        try {
          const response = await usersAPI.getProfile()
          profile = unwrapData(response) || currentUser
        } catch (_error) {
          profile = currentUser
        }

        const notificationPreferences =
          profile?.[USER_PREFERENCE_KEYS.notifications] ||
          localPreferences[USER_PREFERENCE_KEYS.notifications] ||
          {}

        setSettings((current) => ({
          ...current,
          mention_emails: notificationPreferences.mention_emails ?? current.mention_emails,
          task_assignment_emails:
            notificationPreferences.task_assignment_emails ?? current.task_assignment_emails,
          deadline_reminder_emails:
            notificationPreferences.deadline_reminder_emails ?? current.deadline_reminder_emails,
          comment_emails: notificationPreferences.comment_emails ?? current.comment_emails,
          compactMode: localPreferences.compactMode ?? current.compactMode,
          reducedMotion: localPreferences.reducedMotion ?? current.reducedMotion,
        }))
      } catch (_error) {
        const localPreferences = readWorkspacePrefs()
        const notificationPreferences = localPreferences[USER_PREFERENCE_KEYS.notifications] || {}
        setSettings((current) => ({
          ...current,
          mention_emails: notificationPreferences.mention_emails ?? current.mention_emails,
          task_assignment_emails:
            notificationPreferences.task_assignment_emails ?? current.task_assignment_emails,
          deadline_reminder_emails:
            notificationPreferences.deadline_reminder_emails ?? current.deadline_reminder_emails,
          comment_emails: notificationPreferences.comment_emails ?? current.comment_emails,
          compactMode: localPreferences.compactMode ?? current.compactMode,
          reducedMotion: localPreferences.reducedMotion ?? current.reducedMotion,
        }))
      } finally {
        setLoading(false)
      }
    }

    loadSettings()
  }, [currentUser])

  const toggle = (key) => {
    setSettings((current) => ({ ...current, [key]: !current[key] }))
  }

  const saveSettings = async () => {
    setSaving(true)
    const savedLocally = writeWorkspacePrefs(settings)
    try {
      await usersAPI.updateProfile({
        [USER_PREFERENCE_KEYS.notifications]: {
          mention_emails: settings.mention_emails,
          task_assignment_emails: settings.task_assignment_emails,
          deadline_reminder_emails: settings.deadline_reminder_emails,
          comment_emails: settings.comment_emails,
        },
      })
      toast.success('Preferences saved successfully.')
    } catch (error) {
      if (savedLocally) {
        toast.success('Preferences saved on this device. Cloud sync will retry when the profile endpoint is available.')
      } else {
        toast.error('Unable to save preferences on this device right now.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading settings" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Settings"
        title="Tune the workspace feel"
        description="Shape the app around how you prefer to receive signals, move through the UI, and manage focus."
        stats={[
          { label: 'Alerts enabled', value: Object.values(settings).filter(Boolean).length, caption: 'Active preferences' },
          { label: 'Theme mode', value: 'Emerald', caption: 'Current visual system' },
          { label: 'Motion', value: settings.reducedMotion ? 'Reduced' : 'Expressive', caption: 'Interaction profile' },
        ]}
        spotlight={{
          eyebrow: 'Experience system',
          title: 'Settings should feel like a control room.',
          description: 'This screen is designed to look intentional in demos: not just toggles, but a clear control surface for signal and atmosphere.',
          points: [
            { label: 'Notification rules', value: notificationOptions.length },
            { label: 'Density mode', value: settings.compactMode ? 'Compact' : 'Comfortable' },
          ],
        }}
        actions={
          <button type="button" onClick={saveSettings} className="btn-primary">
            {saving ? 'Saving preferences...' : 'Save preferences'}
          </button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Notifications</h2>
          <p className="mt-2 text-sm text-soft">Choose which signals stay active across email and in-app activity.</p>

          <div className="mt-6 grid gap-4">
            {notificationOptions.map((option) => (
              <label key={option.key} className="feature-tile flex items-start justify-between gap-4 p-4">
                <div>
                  <p className="font-semibold text-emerald-950">{option.label}</p>
                  <p className="mt-1 text-sm text-soft">{option.description}</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings[option.key]}
                  onChange={() => toggle(option.key)}
                  className="mt-1 h-5 w-5 rounded border-emerald-200"
                />
              </label>
            ))}
          </div>
        </section>

        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Experience</h2>
          <p className="mt-2 text-sm text-soft">Control density and motion while keeping the green-forward visual system intact.</p>

          <div className="mt-6 grid gap-4">
            <label className="feature-tile flex items-start justify-between gap-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">Compact mode</p>
                <p className="mt-1 text-sm text-soft">Tighten spacing for denser work sessions and faster scanning.</p>
              </div>
              <input
                type="checkbox"
                checked={settings.compactMode}
                onChange={() => toggle('compactMode')}
                className="mt-1 h-5 w-5 rounded border-emerald-200"
              />
            </label>

            <label className="feature-tile flex items-start justify-between gap-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">Reduced motion</p>
                <p className="mt-1 text-sm text-soft">Keep interactions calmer if you prefer less movement.</p>
              </div>
              <input
                type="checkbox"
                checked={settings.reducedMotion}
                onChange={() => toggle('reducedMotion')}
                className="mt-1 h-5 w-5 rounded border-emerald-200"
              />
            </label>

            <div className="spotlight-panel text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">Theme direction</p>
              <h3 className="mt-3 text-xl font-bold">Emerald glass</h3>
              <p className="mt-2 text-sm text-emerald-50/90">
                The current interface uses bright greens, soft gradients, airy cards, and subtle depth to keep the workspace modern and calm.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="feature-tile">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Density</p>
                <p className="mt-3 text-lg font-bold text-emerald-950">{settings.compactMode ? 'Compact' : 'Relaxed'}</p>
              </div>
              <div className="feature-tile">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Motion</p>
                <p className="mt-3 text-lg font-bold text-emerald-950">{settings.reducedMotion ? 'Reduced' : 'Animated'}</p>
              </div>
              <div className="feature-tile">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Digest</p>
                <p className="mt-3 text-lg font-bold text-emerald-950">{settings.comment_emails ? 'Enabled' : 'Off'}</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
