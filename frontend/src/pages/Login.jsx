import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import { login } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { resolvePostAuthPath } from '../utils/authRouting'

const loginHeroPhrases = [
  { text: 'Pick up work with clarity.', emphasis: 'clarity' },
  { text: 'See what needs action first.', emphasis: 'action' },
  { text: 'Move from backlog to delivery.', emphasis: 'delivery' },
  { text: 'Keep progress visible every day.', emphasis: 'visible' },
]

export default function Login() {
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [formError, setFormError] = useState('')
  const [activePhraseIndex, setActivePhraseIndex] = useState(0)
  const [visiblePhrase, setVisiblePhrase] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || '/dashboard'
  const loginError = searchParams.get('error')
  const registered = searchParams.get('registered') === '1'
  const registeredEmail = searchParams.get('email') || ''
  const {
    register,
    setError,
    clearErrors,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      credential: registeredEmail,
      password: '',
      remember_me: true,
    },
  })

  useEffect(() => {
    if (registered) {
      toast.success('Registration complete. Sign in with your new account.')
    }
  }, [registered])

  useEffect(() => {
    if (!loginError) {
      return
    }

    const errorMessages = {
      google_auth_failed: 'Google sign-in could not be completed.',
      google_token_exchange_failed: 'Google sign-in could not be completed. Check the backend Google client secret and redirect URI.',
      google_userinfo_failed: 'Google sign-in could not fetch your Google profile.',
      no_authorization_code: 'Google sign-in did not return an authorization code.',
      no_access_token: 'Google sign-in did not return an access token.',
      no_email: 'Google did not return an email address for this account.',
      account_type_mismatch: 'This Google account is already linked to a different workspace mode.',
    }

    toast.error(errorMessages[loginError] || 'Sign in could not be completed.')
  }, [loginError])

  useEffect(() => {
    const currentPhrase = loginHeroPhrases[activePhraseIndex].text
    let timer

    if (!isDeleting && visiblePhrase !== currentPhrase) {
      timer = window.setTimeout(() => {
        setVisiblePhrase(currentPhrase.slice(0, visiblePhrase.length + 1))
      }, 50)
    } else if (!isDeleting && visiblePhrase === currentPhrase) {
      timer = window.setTimeout(() => {
        setIsDeleting(true)
      }, 1500)
    } else if (isDeleting && visiblePhrase.length > 0) {
      timer = window.setTimeout(() => {
        setVisiblePhrase(currentPhrase.slice(0, visiblePhrase.length - 1))
      }, 28)
    } else {
      timer = window.setTimeout(() => {
        setIsDeleting(false)
        setActivePhraseIndex((index) => (index + 1) % loginHeroPhrases.length)
      }, 160)
    }

    return () => window.clearTimeout(timer)
  }, [activePhraseIndex, isDeleting, visiblePhrase])

  const activePhrase = loginHeroPhrases[activePhraseIndex]

  const onSubmit = async (data) => {
    setLoading(true)
    setFormError('')
    clearErrors()
    try {
      const session = await dispatch(login({ ...data, credential: data.credential.trim() })).unwrap()
      const destination = resolvePostAuthPath({ nextPath, user: session?.user })
      if (destination === '/403') {
        toast.error('You do not have admin access.')
        navigate('/403', { replace: true })
        return
      }
      toast.success('Welcome back to your workspace.')
      navigate(destination, { replace: true })
    } catch (error) {
      const normalizedError = typeof error === 'string' ? { message: error } : error || {}
      const fieldErrors = normalizedError.fieldErrors || {}
      Object.entries(fieldErrors).forEach(([field, value]) => {
        if (!value) return
        const message = Array.isArray(value) ? value[0] : value
        if (typeof message === 'string' && message.trim()) {
          setError(field, { message })
        }
      })
      const message = normalizedError.message || 'Sign in failed'
      setFormError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    setGoogleLoading(true)
    try {
      const response = await authAPI.getGoogleLoginUrl(nextPath, undefined, 'login')
      const payload = unwrapData(response)
      if (payload?.login_url) {
        window.location.href = payload.login_url
      } else {
        toast.error('Google sign-in is not available.')
      }
    } catch (error) {
      const backendMessage =
        error?.response?.data?.errors?.non_field_errors?.[0] ||
        error?.response?.data?.errors?.detail ||
        error?.response?.data?.message ||
        error?.message
      toast.error(backendMessage || 'Unable to start Google sign-in right now.')
    } finally {
      setGoogleLoading(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue to your tasks, teams, and recent activity."
      compact
      heroLabel="WorkNest access"
      heroHeadline="Enter a workspace that already feels in control."
      heroDescription="Pick up deadlines, ownership, and recent team movement from one calm operating surface."
      heroVisual={<AuthHeroVisual visiblePhrase={visiblePhrase} emphasis={activePhrase.emphasis} variant="login" />}
      heroBottom={<LoginHeroSummary />}
      mobileHero={<AuthMobileHero label="WorkNest access" title="Sign in and step straight into the work." phrase={visiblePhrase} emphasis={activePhrase.emphasis} />}
      heroPanelClassName="login-brand-panel fade-in-delayed"
      cardClassName="login-auth-card"
      logoSubtitle="Structured operations for modern teams"
      footer={
        <p>
          New here?{' '}
          <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to={`/register?next=${encodeURIComponent(nextPath)}`}>
            Create an account
          </Link>
        </p>
      }
    >
      <div className="space-y-4">
        <button type="button" onClick={handleGoogleLogin} disabled={googleLoading} className="btn-secondary w-full justify-center">
          {googleLoading ? (
            'Connecting to Google...'
          ) : (
            <span className="flex items-center gap-3">
              <img src="/google.png" alt="" className="h-5 w-5" />
              Continue with Google
            </span>
          )}
        </button>

        <div className="flex items-center gap-3">
          <div className="soft-divider" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-soft">or</span>
          <div className="soft-divider" />
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
          {formError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>
          ) : null}
          <div>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Email or phone number</label>
            <input
              type="text"
              {...register('credential', { required: 'Email or phone number is required' })}
              className="input-field"
              placeholder="name@company.com or +254712345678"
            />
            <p className="mt-2 text-xs text-soft">Use the verified email address or phone number connected to this account.</p>
            {errors.credential ? <p className="mt-2 text-sm text-red-500">{errors.credential.message}</p> : null}
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <label className="block text-sm font-semibold text-emerald-950">Password</label>
              <Link className="text-sm font-semibold text-emerald-700 hover:text-emerald-800" to="/forgot-password">
                Forgot password?
              </Link>
            </div>
            <PasswordField
              label=""
              name="password"
              register={register}
              error={errors.password}
              placeholder="Enter your password"
              requiredMessage="Password is required"
            />
          </div>

          <label className="flex items-center gap-3 rounded-2xl bg-emerald-50/80 px-4 py-2.5 text-sm text-soft">
            <input type="checkbox" {...register('remember_me')} className="h-4 w-4 rounded border-emerald-200" />
            Keep me signed in on this device
          </label>

          <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </AuthShell>
  )
}

function AuthHeroVisual({ visiblePhrase, emphasis, variant }) {
  const metrics =
    variant === 'login'
      ? [
          { label: 'Due today', value: '06' },
          { label: 'In review', value: '14' },
          { label: 'Focus score', value: '91%' },
        ]
      : [
          { label: 'Setup time', value: '<10m' },
          { label: 'Roles ready', value: '04' },
          { label: 'Day one', value: 'Clear' },
        ]

  return (
    <div className="space-y-4">
      <div className="landing-typewriter-panel max-w-none">
        <div className="landing-typewriter-label">{variant === 'login' ? 'Today in WorkNest' : 'Getting started'}</div>
        <div className="landing-typewriter-line">
          {renderTypedPhrase(visiblePhrase, emphasis)}
          <span className="landing-typewriter-caret" aria-hidden="true" />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {metrics.map((item) => (
          <div key={item.label} className="rounded-[20px] border border-slate-200/80 bg-white px-4 py-4 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="rounded-[24px] border border-emerald-100 bg-[linear-gradient(180deg,#f4fbf6_0%,#ffffff_100%)] p-5 shadow-[0_18px_40px_rgba(15,23,42,0.05)]">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">
              {variant === 'login' ? 'Delivery snapshot' : 'Workspace setup'}
            </p>
            <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-950">
              {variant === 'login' ? 'Execution stays readable at a glance.' : 'A strong starting point from the first screen.'}
            </h3>
          </div>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-emerald-700">
            {variant === 'login' ? 'Live' : 'Ready'}
          </span>
        </div>
        <div className="mt-4 grid gap-3">
          <div className="rounded-[18px] border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-600">
            {variant === 'login'
              ? 'Deadlines, owners, and recent movement stay visible before the day starts.'
              : 'Teams begin with structure, personal users begin with focus, and both start in a calmer system.'}
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-600">
            {variant === 'login'
              ? 'Your account decides where you land after sign-in.'
              : 'Pick the right workspace at signup, then keep every task, owner, and deadline in context.'}
          </div>
        </div>
      </div>
    </div>
  )
}

function LoginHeroSummary() {
  return (
    <div className="glass-panel p-5">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Workflow</p>
      <div className="mt-3 grid gap-4 md:grid-cols-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">Capture</p>
          <p className="mt-2 text-sm text-soft">Create tasks, assign owners, and set deadlines fast.</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-950">Collaborate</p>
          <p className="mt-2 text-sm text-soft">Comments, mentions, notifications, and team context stay connected.</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-950">Deliver</p>
          <p className="mt-2 text-sm text-soft">Boards, calendars, and analytics keep momentum visible.</p>
        </div>
      </div>
    </div>
  )
}

function AuthMobileHero({ label, title, phrase, emphasis }) {
  return (
    <div className="login-mobile-hero fade-in">
      <div className="stat-chip inline-flex items-center gap-2">
        <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
        {label}
      </div>
      <h1 className="mt-4 font-display text-[2rem] font-bold leading-tight tracking-[-0.04em] text-slate-950">{title}</h1>
      <div className="landing-typewriter-panel mt-4 max-w-none">
        <div className="landing-typewriter-label">Live focus</div>
        <div className="landing-typewriter-line">
          {renderTypedPhrase(phrase, emphasis)}
          <span className="landing-typewriter-caret" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

function renderTypedPhrase(visibleText, emphasis) {
  if (!visibleText) {
    return <span className="text-slate-400">Pick up work with clarity.</span>
  }

  if (!emphasis) {
    return <span>{visibleText}</span>
  }

  const startIndex = visibleText.toLowerCase().indexOf(emphasis.toLowerCase())
  if (startIndex === -1) {
    return <span>{visibleText}</span>
  }

  const before = visibleText.slice(0, startIndex)
  const highlighted = visibleText.slice(startIndex, startIndex + emphasis.length)
  const after = visibleText.slice(startIndex + emphasis.length)

  return (
    <span>
      {before}
      <span className="text-emerald-700">{highlighted}</span>
      {after}
    </span>
  )
}
