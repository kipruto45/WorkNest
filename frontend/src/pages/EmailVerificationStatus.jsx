import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import AppLogo from '../components/AppLogo'
import { setUser } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { extractApiError } from '../utils/apiErrors'

export default function EmailVerificationStatus() {
  const dispatch = useDispatch()
  const { token, user } = useSelector((state) => state.auth)
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState(() => (user?.email_verified ? 'success' : 'idle'))
  const [message, setMessage] = useState(() =>
    user?.email_verified ? 'Your email address is already verified.' : 'Open the verification link from your inbox to confirm your email.'
  )
  const [resending, setResending] = useState(false)

  const verificationToken = searchParams.get('token') || ''

  useEffect(() => {
    if (!verificationToken) return

    let isCancelled = false
    const verify = async () => {
      setStatus('loading')
      setMessage('Confirming your email address...')
      try {
        const response = await authAPI.verifyEmail({ token: verificationToken })
        const verifiedUser = unwrapData(response)
        if (token && verifiedUser) {
          dispatch(setUser(verifiedUser))
        }
        if (!isCancelled) {
          setStatus('success')
          setMessage('Your email address is verified. Account recovery, trusted notifications, and future security controls are now fully enabled.')
        }
      } catch (error) {
        if (!isCancelled) {
          setStatus('error')
          setMessage(
            extractApiError(error, { fallbackMessage: 'That verification link is invalid or has expired.' }).message
          )
        }
      }
    }

    verify()
    return () => {
      isCancelled = true
    }
  }, [dispatch, token, verificationToken])

  const handleResend = async () => {
    setResending(true)
    try {
      const response = await authAPI.resendVerification()
      const payload = unwrapData(response) || {}
      setStatus('pending')
      setMessage(
        payload?.delivery?.status === 'sent'
          ? 'A fresh verification link was sent to your inbox.'
          : 'A fresh verification link is being delivered to your inbox.'
      )
    } catch (error) {
      setStatus('error')
      setMessage(extractApiError(error, { fallbackMessage: 'We could not resend the verification email right now.' }).message)
    } finally {
      setResending(false)
    }
  }

  const tone = useMemo(() => {
    if (status === 'success') {
      return {
        badge: 'bg-emerald-100 text-emerald-800',
        title: 'Email verified',
      }
    }
    if (status === 'error') {
      return {
        badge: 'bg-rose-100 text-rose-800',
        title: 'Verification issue',
      }
    }
    return {
      badge: 'bg-amber-100 text-amber-800',
      title: status === 'loading' ? 'Verifying email' : 'Verification pending',
    }
  }, [status])

  return (
    <div className="app-shell min-h-screen bg-[#f7f8f6] px-4 py-8 md:px-6">
      <div className="mx-auto max-w-4xl rounded-[30px] border border-slate-200 bg-[#fbfbfa] p-5 shadow-[0_20px_60px_rgba(15,23,42,0.06)] md:p-8">
        <AppLogo to={token ? '/dashboard' : '/'} subtitle="Account Trust" />

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
          <section className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
            <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${tone.badge}`}>{tone.title}</span>
            <h1 className="mt-4 font-display text-4xl font-bold tracking-tight text-slate-950">Keep your workspace identity trusted.</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">{message}</p>

            <div className="mt-8 flex flex-wrap gap-3">
              {status === 'success' ? (
                <Link to={token ? '/dashboard' : '/login'} className="btn-primary">
                  {token ? 'Open workspace' : 'Sign in'}
                </Link>
              ) : null}
              {user?.email && !user?.email_verified ? (
                <button type="button" onClick={handleResend} className="btn-secondary" disabled={resending || status === 'loading'}>
                  {resending ? 'Sending...' : 'Resend verification email'}
                </button>
              ) : null}
              <Link to={token ? '/settings/security' : '/login'} className="btn-secondary">
                {token ? 'Open security settings' : 'Back to sign in'}
              </Link>
            </div>
          </section>

          <section className="rounded-[26px] border border-slate-200 bg-white p-6 shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Why this matters</p>
            <h2 className="mt-3 text-2xl font-semibold text-slate-950">Verified email unlocks a stronger account posture.</h2>
            <div className="mt-6 space-y-3">
              {[
                'Password recovery stays tied to a trusted inbox.',
                'Important account and workspace notifications stay reliable.',
                'Future security controls can confidently use verified identity state.',
              ].map((item) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-[#fcfcfb] px-4 py-3 text-sm text-slate-600">
                  {item}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
