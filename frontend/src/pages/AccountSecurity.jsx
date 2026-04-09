import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { setUser } from '../features/authSlice'
import { authAPI, unwrapData, usersAPI, unwrapResults } from '../services/api'

export default function AccountSecurity() {
  const dispatch = useDispatch()
  const currentUser = useSelector((state) => state.auth.user)
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [resending, setResending] = useState(false)
  const [sessions, setSessions] = useState([])
  const [devices, setDevices] = useState([])
  const [revokingSessionId, setRevokingSessionId] = useState('')
  const [removingDeviceId, setRemovingDeviceId] = useState('')

  const verificationToken = searchParams.get('verify_email') || ''

  const loadSecurityData = async () => {
    setLoading(true)
    try {
      const [sessionsResponse, devicesResponse] = await Promise.all([
        authAPI.getSessions(),
        usersAPI.getPushDevices({ page_size: 50 }),
      ])
      setSessions(unwrapData(sessionsResponse) || [])
      setDevices(unwrapResults(devicesResponse))
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to load security data right now.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSecurityData()
  }, [])

  useEffect(() => {
    if (!verificationToken) return

    const verify = async () => {
      setVerifying(true)
      try {
        const response = await authAPI.verifyEmail({ token: verificationToken })
        const user = unwrapData(response)
        dispatch(setUser(user))
        toast.success('Email verified successfully.')
        const nextParams = new URLSearchParams(searchParams)
        nextParams.delete('verify_email')
        setSearchParams(nextParams, { replace: true })
      } catch (error) {
        toast.error(error?.response?.data?.message || 'Unable to verify email.')
      } finally {
        setVerifying(false)
      }
    }

    verify()
  }, [dispatch, searchParams, setSearchParams, verificationToken])

  const handleResendVerification = async () => {
    setResending(true)
    try {
      await authAPI.resendVerification()
      toast.success('Verification email sent.')
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to resend verification email.')
    } finally {
      setResending(false)
    }
  }

  const handleRevokeSession = async (sessionId) => {
    setRevokingSessionId(sessionId)
    try {
      await authAPI.revokeSession(sessionId)
      toast.success('Session revoked.')
      await loadSecurityData()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to revoke that session.')
    } finally {
      setRevokingSessionId('')
    }
  }

  const handleRemoveDevice = async (deviceId) => {
    setRemovingDeviceId(deviceId)
    try {
      await usersAPI.removePushDevice(deviceId)
      toast.success('Push device removed.')
      await loadSecurityData()
    } catch (error) {
      toast.error(error?.response?.data?.message || 'Unable to remove that device.')
    } finally {
      setRemovingDeviceId('')
    }
  }

  const stats = useMemo(
    () => [
      { label: 'Verification', value: currentUser?.email_verified ? 'Verified' : 'Pending', caption: 'Email trust state' },
      { label: 'Sessions', value: sessions.length, caption: 'Tracked devices' },
      { label: 'Push devices', value: devices.length, caption: 'Mobile-ready tokens' },
    ],
    [currentUser?.email_verified, devices.length, sessions.length]
  )

  if (loading) {
    return <LoadingState label="Loading security workspace" />
  }

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Security"
        title="Account trust, sessions, and device visibility"
        description="Review verification status, active sessions, and push-ready devices from one connected control surface."
        stats={stats}
        spotlight={{
          eyebrow: 'Future-ready 2FA',
          title: 'The account model is ready for stronger auth.',
          description: 'This workspace now exposes verified identity state, tracked sessions, and device inventory so stronger authentication can be layered in cleanly.',
          points: [
            { label: '2FA status', value: currentUser?.two_factor_status || 'disabled' },
            { label: 'Theme mode', value: currentUser?.theme_preference || 'system' },
          ],
        }}
      />

      {!currentUser?.email_verified ? (
        <section className="card fade-in">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Email verification</p>
              <h2 className="mt-2 text-2xl font-bold text-emerald-950">Confirm your email address</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-soft">
                Verified email strengthens account recovery, secure notifications, and future authentication upgrades.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={handleResendVerification} className="btn-primary" disabled={resending || verifying}>
                {verifying ? 'Verifying…' : resending ? 'Sending…' : 'Resend verification'}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="card fade-in">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Sessions</p>
              <h2 className="mt-2 text-2xl font-bold text-emerald-950">Recent devices</h2>
            </div>
            <Link to="/settings" className="btn-secondary">
              Back to settings
            </Link>
          </div>

          <div className="mt-5 space-y-3">
            {sessions.length === 0 ? (
              <EmptyState title="No tracked sessions" description="New sign-ins will appear here with device and last-seen details." />
            ) : (
              sessions.map((session) => (
                <div key={session.id} className="feature-tile">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-emerald-950">{session.device_name || 'Unknown device'}</p>
                      <p className="mt-1 text-sm text-soft">{session.ip_address || 'Unknown IP'} • {session.status}</p>
                      <p className="mt-2 text-xs text-slate-500">{session.user_agent || 'No device signature recorded.'}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRevokeSession(session.id)}
                      className="btn-ghost"
                      disabled={revokingSessionId === session.id || session.status === 'revoked'}
                    >
                      {revokingSessionId === session.id ? 'Revoking…' : session.status === 'revoked' ? 'Revoked' : 'Revoke'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="card fade-in">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Push devices</p>
            <h2 className="mt-2 text-2xl font-bold text-emerald-950">Mobile-ready notification targets</h2>
            <p className="mt-2 text-sm leading-6 text-soft">
              Web and mobile clients can register device tokens here for notification delivery and deep linking.
            </p>
          </div>

          <div className="mt-5 space-y-3">
            {devices.length === 0 ? (
              <EmptyState
                title="No push devices yet"
                description="Device registrations will appear here when a supported browser or mobile client saves a push token."
              />
            ) : (
              devices.map((device) => (
                <div key={device.id} className="feature-tile">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-semibold text-emerald-950">{device.label || `${device.platform} device`}</p>
                      <p className="mt-1 text-sm text-soft">{device.platform} • {device.app_version || 'Version not provided'}</p>
                      <p className="mt-2 text-xs text-slate-500">Last seen {device.last_seen_at || 'recently'}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveDevice(device.id)}
                      className="btn-ghost"
                      disabled={removingDeviceId === device.id}
                    >
                      {removingDeviceId === device.id ? 'Removing…' : 'Remove'}
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
