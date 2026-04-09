import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import { usersAPI, unwrapData } from '../services/api'
import { setUser } from '../features/authSlice'
import { CLIENT_STORAGE_KEYS, USER_PREFERENCE_KEYS } from '../utils/clientConfig.js'

const notificationOptions = [
  { key: 'task_assigned', label: 'Task assignments', description: 'Get notified when work lands on your plate.' },
  { key: 'deadline_approaching', label: 'Deadline reminders', description: 'Stay ahead of deadlines before they turn urgent.' },
  { key: 'comment_posted', label: 'Comment updates', description: 'Know when teammates add context to your work.' },
  { key: 'mentioned_in_comment', label: 'Mentions', description: 'Stay aware when someone tags you.' },
  { key: 'team_invite', label: 'Team invitations', description: 'Receive invitations and onboarding updates.' },
  { key: 'admin_message', label: 'Admin announcements', description: 'Platform-wide messages and critical updates.' },
]

const smsNotificationOptions = [
  { key: 'task_assignment_sms', label: 'Task assignments', description: 'High-signal work assignments sent to your phone.' },
  { key: 'deadline_reminder_sms', label: 'Deadline reminders', description: 'Short reminders when due dates are getting close.' },
  { key: 'mention_sms', label: 'Mentions', description: 'Lightweight nudges when someone explicitly calls you in.' },
  { key: 'invite_sms', label: 'Invites', description: 'Important workspace invitations delivered to your mobile.' },
  { key: 'broadcast_sms', label: 'Admin broadcasts', description: 'Urgent operational updates that are worth sending by SMS.' },
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
      channels: settings.channels,
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
  const dispatch = useDispatch()
  const currentUser = useSelector((state) => state.auth.user)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [sendingEmailCode, setSendingEmailCode] = useState(false)
  const [confirmingEmailCode, setConfirmingEmailCode] = useState(false)
  const [sendingPhoneCode, setSendingPhoneCode] = useState(false)
  const [confirmingPhoneCode, setConfirmingPhoneCode] = useState(false)
  const [settings, setSettings] = useState({
    channels: {
      in_app: notificationOptions.reduce((acc, option) => ({ ...acc, [option.key]: true }), {}),
      email: notificationOptions.reduce((acc, option) => ({ ...acc, [option.key]: true }), {}),
    },
    mention_sms: true,
    task_assignment_sms: true,
    deadline_reminder_sms: true,
    invite_sms: true,
    broadcast_sms: true,
    phone_number: '',
    phone_country_code: '+254',
    phone_verified: false,
    sms_opt_in: false,
    compactMode: false,
    reducedMotion: false,
    email: '',
    email_code: '',
    phone_code: '',
  })

  useEffect(() => {
    const loadSettings = async () => {
      setLoading(true)
      try {
        const localPreferences = readWorkspacePrefs()
        let profile = currentUser
        let notificationPreferencePayload = null
        try {
          const [profileResponse, preferenceResponse] = await Promise.all([
            usersAPI.getProfile(),
            usersAPI.getNotificationPreferences(),
          ])
          profile = unwrapData(profileResponse) || currentUser
          notificationPreferencePayload = unwrapData(preferenceResponse)
        } catch (_error) {
          profile = currentUser
        }

        const notificationPreferences =
          notificationPreferencePayload ||
          profile?.[USER_PREFERENCE_KEYS.notifications] ||
          localPreferences[USER_PREFERENCE_KEYS.notifications] ||
          {}

        setSettings((current) => ({
          ...current,
          channels: {
            in_app: { ...current.channels.in_app, ...(notificationPreferences.channels?.in_app || {}) },
            email: { ...current.channels.email, ...(notificationPreferences.channels?.email || {}) },
          },
          mention_sms: notificationPreferences.mention_sms ?? current.mention_sms,
          task_assignment_sms: notificationPreferences.task_assignment_sms ?? current.task_assignment_sms,
          deadline_reminder_sms: notificationPreferences.deadline_reminder_sms ?? current.deadline_reminder_sms,
          invite_sms: notificationPreferences.invite_sms ?? current.invite_sms,
          broadcast_sms: notificationPreferences.broadcast_sms ?? current.broadcast_sms,
          phone_number: profile?.phone_number || current.phone_number,
          phone_country_code: profile?.phone_country_code || current.phone_country_code,
          phone_verified: profile?.phone_verified ?? current.phone_verified,
          sms_opt_in: profile?.sms_opt_in ?? current.sms_opt_in,
          compactMode: localPreferences.compactMode ?? current.compactMode,
          reducedMotion: localPreferences.reducedMotion ?? current.reducedMotion,
          email: profile?.email || current.email,
          email_code: current.email_code,
          phone_code: current.phone_code,
        }))
      } catch (_error) {
        const localPreferences = readWorkspacePrefs()
        const notificationPreferences = localPreferences[USER_PREFERENCE_KEYS.notifications] || {}
        setSettings((current) => ({
          ...current,
          channels: {
            in_app: { ...current.channels.in_app, ...(notificationPreferences.channels?.in_app || {}) },
            email: { ...current.channels.email, ...(notificationPreferences.channels?.email || {}) },
          },
          mention_sms: notificationPreferences.mention_sms ?? current.mention_sms,
          task_assignment_sms: notificationPreferences.task_assignment_sms ?? current.task_assignment_sms,
          deadline_reminder_sms: notificationPreferences.deadline_reminder_sms ?? current.deadline_reminder_sms,
          invite_sms: notificationPreferences.invite_sms ?? current.invite_sms,
          broadcast_sms: notificationPreferences.broadcast_sms ?? current.broadcast_sms,
          phone_number: currentUser?.phone_number || current.phone_number,
          phone_country_code: currentUser?.phone_country_code || current.phone_country_code,
          phone_verified: currentUser?.phone_verified ?? current.phone_verified,
          sms_opt_in: currentUser?.sms_opt_in ?? current.sms_opt_in,
          compactMode: localPreferences.compactMode ?? current.compactMode,
          reducedMotion: localPreferences.reducedMotion ?? current.reducedMotion,
          email: currentUser?.email || current.email,
          email_code: current.email_code,
          phone_code: current.phone_code,
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

  const toggleChannel = (channel, key) => {
    setSettings((current) => ({
      ...current,
      channels: {
        ...current.channels,
        [channel]: {
          ...current.channels[channel],
          [key]: !current.channels[channel][key],
        },
      },
    }))
  }

  const saveSettings = async () => {
    setSaving(true)
    const savedLocally = writeWorkspacePrefs(settings)
    try {
      const requests = [
        usersAPI.updateNotificationPreferences({
          channels: settings.channels,
          mention_sms: settings.mention_sms,
          task_assignment_sms: settings.task_assignment_sms,
          deadline_reminder_sms: settings.deadline_reminder_sms,
          invite_sms: settings.invite_sms,
          broadcast_sms: settings.broadcast_sms,
        }),
      ]
      if ((currentUser?.phone_number || '').trim()) {
        requests.push(
          usersAPI.updatePhoneSettings({
            phone_number: currentUser.phone_number.trim(),
            phone_country_code: (currentUser.phone_country_code || settings.phone_country_code).trim(),
            sms_opt_in: settings.sms_opt_in,
          })
        )
      }
      await Promise.all(requests)
      const refreshedProfile = unwrapData(await usersAPI.getProfile())
      if (refreshedProfile) {
        dispatch(setUser(refreshedProfile))
        setSettings((current) => ({
          ...current,
          phone_verified: refreshedProfile.phone_verified ?? current.phone_verified,
        }))
      }
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

  const syncUpdatedUser = (updatedUser) => {
    if (!updatedUser) return
    dispatch(setUser(updatedUser))
    setSettings((current) => ({
      ...current,
      email: updatedUser.email || current.email,
      phone_number: updatedUser.phone_number || current.phone_number,
      phone_country_code: updatedUser.phone_country_code || current.phone_country_code,
      phone_verified: Boolean(updatedUser.phone_verified),
      email_verified: Boolean(updatedUser.email_verified),
      sms_opt_in: Boolean(updatedUser.sms_opt_in),
      email_code: '',
      phone_code: '',
    }))
  }

  const requestEmailChange = async () => {
    if (!settings.email.trim()) {
      toast.error('Enter the new email address you want to use.')
      return
    }
    setSendingEmailCode(true)
    try {
      await usersAPI.requestCredentialChange({
        credential_type: 'email',
        new_value: settings.email.trim(),
      })
      toast.success('Verification code sent to the new email address.')
    } catch (error) {
      const fieldError = error?.response?.data?.errors?.new_value?.[0]
      toast.error(fieldError || error?.response?.data?.message || 'Unable to send an email verification code right now.')
    } finally {
      setSendingEmailCode(false)
    }
  }

  const confirmEmailChange = async () => {
    if (!settings.email_code.trim()) {
      toast.error('Enter the verification code sent to the new email address.')
      return
    }
    setConfirmingEmailCode(true)
    try {
      const response = await usersAPI.confirmCredentialChange({
        credential_type: 'email',
        code: settings.email_code.trim(),
      })
      syncUpdatedUser(unwrapData(response))
      toast.success('Email updated successfully.')
    } catch (error) {
      const fieldError = error?.response?.data?.errors?.code?.[0]
      toast.error(fieldError || error?.response?.data?.message || 'Verification code could not be confirmed.')
    } finally {
      setConfirmingEmailCode(false)
    }
  }

  const requestPhoneChange = async () => {
    if (!settings.phone_number.trim()) {
      toast.error('Enter the new phone number you want to use.')
      return
    }
    setSendingPhoneCode(true)
    try {
      await usersAPI.requestCredentialChange({
        credential_type: 'phone',
        new_value: settings.phone_number.trim(),
        phone_country_code: settings.phone_country_code.trim(),
      })
      toast.success('Verification code sent to the new phone number.')
    } catch (error) {
      const fieldError = error?.response?.data?.errors?.new_value?.[0]
      toast.error(fieldError || error?.response?.data?.message || 'Unable to send an SMS verification code right now.')
    } finally {
      setSendingPhoneCode(false)
    }
  }

  const confirmPhoneChange = async () => {
    if (!settings.phone_code.trim()) {
      toast.error('Enter the verification code sent to the new phone number.')
      return
    }
    setConfirmingPhoneCode(true)
    try {
      const response = await usersAPI.confirmCredentialChange({
        credential_type: 'phone',
        code: settings.phone_code.trim(),
      })
      syncUpdatedUser(unwrapData(response))
      toast.success('Phone number updated successfully.')
    } catch (error) {
      const fieldError = error?.response?.data?.errors?.code?.[0]
      toast.error(fieldError || error?.response?.data?.message || 'Verification code could not be confirmed.')
    } finally {
      setConfirmingPhoneCode(false)
    }
  }

  if (loading) {
    return <LoadingState label="Loading settings" />
  }

  const activeChannelCount =
    Object.values(settings.channels.in_app).filter(Boolean).length +
    Object.values(settings.channels.email).filter(Boolean).length +
    smsNotificationOptions.filter((option) => settings[option.key]).length
  const notificationRuleCount = notificationOptions.length + smsNotificationOptions.length

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Settings"
        title="Account and notification settings"
        description="Manage verified sign-in details and notification delivery from one place."
        stats={[
          {
            label: 'Alerts enabled',
            value: activeChannelCount,
            caption: 'Active channels',
          },
          { label: 'Email', value: currentUser?.email_verified ? 'Verified' : 'Pending', caption: 'Sign-in address' },
          { label: 'Phone status', value: settings.phone_verified ? 'Verified' : settings.phone_number ? 'Pending' : 'Missing', caption: 'SMS identity' },
        ]}
        spotlight={{
          eyebrow: 'Credential safety',
          title: 'Email and phone changes are verified before they go live.',
          description: 'Use the account controls below to request a code, verify the new destination, and then replace your sign-in details cleanly.',
          points: [
            { label: 'Notification rules', value: notificationRuleCount },
            { label: 'Phone status', value: settings.phone_verified ? 'Verified' : settings.phone_number ? 'Pending' : 'Missing' },
          ],
        }}
        actions={
          <div className="flex flex-wrap gap-3">
            <Link to="/settings/security" className="btn-secondary">
              Security
            </Link>
            <button type="button" onClick={saveSettings} className="btn-primary">
              {saving ? 'Saving preferences...' : 'Save preferences'}
            </button>
          </div>
        }
      />

      <div className="grid gap-6">
        <section className="card fade-in">
          <h2 className="text-2xl font-bold text-emerald-950">Contact and notifications</h2>
          <p className="mt-2 text-sm text-soft">Change email or phone only after verification, then decide which signals deserve email, SMS, or in-app delivery.</p>

          <div className="mt-6 grid gap-4">
            <div className="feature-tile space-y-4 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-emerald-950">Email address</p>
                  <p className="mt-1 text-sm text-soft">Update the sign-in email only after a verification code is confirmed on the new address.</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    currentUser?.email_verified ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {currentUser?.email_verified ? 'Verified' : currentUser?.email ? 'Pending verification' : 'Missing'}
                </span>
              </div>

              <input
                value={settings.email}
                onChange={(event) => setSettings((current) => ({ ...current, email: event.target.value }))}
                className="input-field"
                placeholder="name@example.com"
              />

              <div className="rounded-[20px] border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Verification</p>
                <p className="mt-2 text-sm text-soft">We send a six-digit code to the new email. Your current sign-in details stay active until you confirm it.</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button type="button" onClick={requestEmailChange} className="btn-secondary" disabled={sendingEmailCode}>
                    {sendingEmailCode ? 'Sending code...' : 'Send email code'}
                  </button>
                  <input
                    value={settings.email_code}
                    onChange={(event) => setSettings((current) => ({ ...current, email_code: event.target.value }))}
                    placeholder="Enter code"
                    className="input-field max-w-[180px]"
                  />
                  <button type="button" onClick={confirmEmailChange} className="btn-primary" disabled={confirmingEmailCode}>
                    {confirmingEmailCode ? 'Confirming...' : 'Confirm email'}
                  </button>
                </div>
              </div>
            </div>

            <div className="feature-tile space-y-4 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-emerald-950">Phone number</p>
                  <p className="mt-1 text-sm text-soft">Use a verified number for delivery-critical alerts and recovery-friendly sign-in options.</p>
                </div>
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    settings.phone_verified ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {settings.phone_verified ? 'Verified' : settings.phone_number ? 'Pending verification' : 'Not added'}
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-[140px,1fr]">
                <input
                  value={settings.phone_country_code}
                  onChange={(event) => setSettings((current) => ({ ...current, phone_country_code: event.target.value }))}
                  className="input-field"
                  placeholder="+254"
                />
                <input
                  value={settings.phone_number}
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      phone_number: event.target.value,
                      phone_verified: false,
                    }))
                  }
                  className="input-field"
                  placeholder="+254712345678"
                />
              </div>

              <label className="flex items-center gap-3 rounded-2xl bg-emerald-50/80 px-4 py-3 text-sm text-soft">
                <input
                  type="checkbox"
                  checked={settings.sms_opt_in}
                  onChange={() => toggle('sms_opt_in')}
                  className="h-4 w-4 rounded border-emerald-200"
                />
                Allow SMS notifications for the rules enabled below
              </label>

              <div className="rounded-[20px] border border-slate-200 bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Verification</p>
                <p className="mt-2 text-sm text-soft">Send a six-digit code to the new number before replacing the phone number you use for login and SMS delivery.</p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button type="button" onClick={requestPhoneChange} className="btn-secondary" disabled={sendingPhoneCode}>
                    {sendingPhoneCode ? 'Sending code...' : 'Send SMS code'}
                  </button>
                  <input
                    value={settings.phone_code}
                    onChange={(event) => setSettings((current) => ({ ...current, phone_code: event.target.value }))}
                    placeholder="Enter code"
                    className="input-field max-w-[180px]"
                  />
                  <button type="button" onClick={confirmPhoneChange} className="btn-primary" disabled={confirmingPhoneCode}>
                    {confirmingPhoneCode ? 'Confirming...' : 'Confirm phone'}
                  </button>
                </div>
              </div>
            </div>

            <div className="feature-tile space-y-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">In-app and email notifications</p>
                <p className="mt-1 text-sm text-soft">Tune which signals should stay visible in-app, and which deserve email delivery.</p>
              </div>
              {notificationOptions.map((option) => (
                <div key={option.key} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-emerald-950">{option.label}</p>
                      <p className="mt-1 text-sm text-soft">{option.description}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <label className="flex items-center gap-2 text-xs font-semibold text-emerald-900">
                        <input
                          type="checkbox"
                          checked={settings.channels.in_app[option.key]}
                          onChange={() => toggleChannel('in_app', option.key)}
                          className="h-4 w-4 rounded border-emerald-200"
                        />
                        In-app
                      </label>
                      <label className="flex items-center gap-2 text-xs font-semibold text-emerald-900">
                        <input
                          type="checkbox"
                          checked={settings.channels.email[option.key]}
                          onChange={() => toggleChannel('email', option.key)}
                          className="h-4 w-4 rounded border-emerald-200"
                        />
                        Email
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="feature-tile space-y-4 p-4">
              <div>
                <p className="font-semibold text-emerald-950">SMS notifications</p>
                <p className="mt-1 text-sm text-soft">Reserve SMS for short, urgent, mobile-friendly messages that are worth the interruption.</p>
              </div>
              {smsNotificationOptions.map((option) => (
                <label key={option.key} className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
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
          </div>
        </section>
      </div>
    </div>
  )
}
