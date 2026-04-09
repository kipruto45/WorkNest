import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import AccountTypeCard from '../components/AccountTypeCard'
import { login } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { resolvePostAuthPath } from '../utils/authRouting'

export default function Login() {
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [formError, setFormError] = useState('')
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
    watch,
    setValue,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      credential: registeredEmail,
      password: '',
      remember_me: true,
      account_type: '',
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
      account_type_required: 'Choose your workspace mode before continuing with Google.',
      account_type_mismatch: 'Selected workspace mode does not match this account.',
    }

    toast.error(errorMessages[loginError] || 'Sign in could not be completed.')
  }, [loginError])

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
      if (normalizedError.requestId || normalizedError.status) {
        console.error('auth_login_failed', {
          requestId: normalizedError.requestId,
          status: normalizedError.status,
          errors: normalizedError.errors,
        })
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    const selectedAccountType = watch('account_type')
    if (!selectedAccountType) {
      setError('account_type', { message: 'Choose your workspace mode' })
      return
    }
    setGoogleLoading(true)
    try {
      const response = await authAPI.getGoogleLoginUrl(nextPath, selectedAccountType, 'login')
      const payload = unwrapData(response)
      if (payload?.login_url) {
        window.location.href = payload.login_url
      } else {
        toast.error('Google sign-in is not available.')
      }
    } catch (error) {
      console.error('Google login error:', error)
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
      title="Sign in to WorkNest"
      subtitle="Enter your workspace with focused tasks, live team visibility, and clear delivery momentum."
      heroLabel="WorkNest access"
      heroHeadline="Work that feels composed before the day even starts."
      heroDescription="A calmer entrance into planning, ownership, and delivery. WorkNest keeps task flow, deadlines, and team signals aligned from the first screen."
      heroVisual={<LoginProductVisual />}
      heroBottom={<LoginWorkflowSummary />}
      mobileHero={<MobileLoginHero />}
      heroPanelClassName="login-brand-panel fade-in-delayed"
      cardClassName="login-auth-card"
      logoSubtitle="Task intelligence for focused teams"
      footer={
        <p className="text-sm leading-6 text-slate-500">
          New here?{' '}
          <Link
            className="font-semibold text-emerald-700 transition-colors hover:text-emerald-800"
            to={`/register?next=${encodeURIComponent(nextPath)}`}
          >
            Create an account
          </Link>
        </p>
      }
    >
      <div className="space-y-4">
        <div className="auth-section-panel">
          <input
            type="hidden"
            {...register('account_type', {
              validate: (value) => ['personal', 'team'].includes(value) || 'Choose your workspace mode',
            })}
          />
          <p className="auth-section-eyebrow">Workspace mode</p>
          <h3 className="auth-section-title">Choose your account context</h3>
          <p className="auth-section-copy">Google and direct sign-in follow the selected workspace mode so you land in the right experience immediately.</p>
          <div className="mt-3 grid grid-cols-2 gap-2.5">
            <AccountTypeCard
              value="personal"
              selected={watch('account_type') === 'personal'}
              onSelect={(value) => {
                setValue('account_type', value, { shouldValidate: true, shouldDirty: true })
                clearErrors('account_type')
              }}
              icon={UserIcon}
              title="Individual account"
              description="Use your personal workspace and task dashboard."
              helper="Personal focus"
              compact
            />
            <AccountTypeCard
              value="team"
              selected={watch('account_type') === 'team'}
              onSelect={(value) => {
                setValue('account_type', value, { shouldValidate: true, shouldDirty: true })
                clearErrors('account_type')
              }}
              icon={TeamIcon}
              title="Team account"
              description="Access your shared workspace, members, and team views."
              helper="Shared delivery"
              compact
            />
          </div>
          {errors.account_type ? <p className="mt-2 text-sm text-red-500">{errors.account_type.message}</p> : null}
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={googleLoading || !watch('account_type')}
          className="google-auth-button w-full justify-center"
        >
          {googleLoading ? (
            'Connecting to Google...'
          ) : (
            <span className="flex items-center gap-3">
              <GoogleMark className="h-5 w-5 shrink-0" />
              Continue with Google
            </span>
          )}
        </button>

        <div className="flex items-center gap-3">
          <div className="soft-divider" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">or</span>
          <div className="soft-divider" />
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form-stack">
          {formError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>
          ) : null}
          <div className="auth-field-group">
            <label className="auth-field-label">Email or phone number</label>
            <input
              type="text"
              {...register('credential', { required: 'Email or phone number is required' })}
              className="input-field auth-input"
              placeholder="name@company.com or +254712345678"
            />
            <p className="auth-helper-copy">Use the verified email address or phone number connected to this account.</p>
            {errors.credential ? <p className="mt-2 text-sm text-red-500">{errors.credential.message}</p> : null}
          </div>

          <div className="auth-field-group">
            <div className="mb-2 flex items-center justify-between gap-3">
              <label className="auth-field-label mb-0">Password</label>
              <Link className="text-sm font-semibold text-emerald-700 transition-colors hover:text-emerald-800" to="/forgot-password">
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
              inputClassName="auth-input"
              toggleButtonClassName="auth-password-toggle"
            />
          </div>

          <label className="auth-checkbox-row">
            <input type="checkbox" {...register('remember_me')} className="h-4 w-4 rounded border-emerald-200" />
            <span>
              <span className="block font-medium text-slate-700">Keep me signed in</span>
              <span className="block text-xs text-slate-500">Use this only on a trusted personal device.</span>
            </span>
          </label>

          <button type="submit" disabled={loading} className="login-submit-button w-full justify-center">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </AuthShell>
  )
}

function MobileLoginHero() {
  return (
    <div className="login-mobile-hero fade-in">
      <div className="stat-chip inline-flex items-center gap-2">
        <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
        WorkNest access
      </div>
      <h1 className="mt-4 font-display text-[2rem] font-bold leading-tight tracking-[-0.04em] text-slate-950">
        Sign in to work that already feels organized.
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Task flow, deadlines, and team visibility stay aligned from the first screen.
      </p>
    </div>
  )
}

function LoginWorkflowSummary() {
  const items = [
    {
      title: 'Capture',
      description: 'Create and organize work fast',
    },
    {
      title: 'Collaborate',
      description: 'Comments, mentions, and team visibility',
    },
    {
      title: 'Deliver',
      description: 'Track deadlines and move work forward',
    },
  ]

  return (
    <div className="login-workflow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Workflow pillars</p>
          <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-950">Structured for daily execution</h3>
        </div>
        <span className="micro-chip">Live workspace</span>
      </div>
      <div className="mt-4 grid gap-3">
        {items.map((item) => (
          <div key={item.title} className="login-workflow-row">
            <div className="login-workflow-dot" />
            <div>
              <p className="text-sm font-semibold text-slate-950">{item.title}</p>
              <p className="mt-1 text-sm leading-5 text-slate-500">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function LoginProductVisual() {
  return (
    <div className="login-product-stage">
      <div className="login-floating-chip login-floating-chip-left">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-800">Due today</span>
        <span className="mt-1 block text-xl font-bold tracking-[-0.04em] text-slate-950">06</span>
      </div>
      <div className="login-floating-chip login-floating-chip-right">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Team sync</span>
        <span className="mt-1 block text-sm font-semibold text-slate-950">14 comments resolved</span>
      </div>

      <div className="login-product-window">
        <div className="login-window-bar">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">WorkNest</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="space-y-3">
            <div className="login-hero-summary-card">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">Delivery board</p>
                <h3 className="mt-2 text-xl font-bold tracking-[-0.04em] text-slate-950">Product launch sprint</h3>
              </div>
              <div className="rounded-2xl bg-emerald-600 px-3 py-2 text-right text-white shadow-[0_14px_30px_rgba(5,150,105,0.18)]">
                <span className="block text-[11px] uppercase tracking-[0.18em] text-emerald-50/80">Progress</span>
                <span className="mt-1 block text-lg font-bold">82%</span>
              </div>
            </div>

            <div className="grid gap-3">
              <TaskCard
                title="Finalize launch checklist"
                meta="Today • Product"
                status="Ready for review"
                progress="3/4 complete"
              />
              <TaskCard
                title="Review onboarding copy"
                meta="Tomorrow • Design"
                status="Shared with team"
                progress="Comments aligned"
              />
              <TaskCard
                title="Confirm campaign timeline"
                meta="This week • Marketing"
                status="Needs owner"
                progress="Assign next"
              />
            </div>
          </div>

          <div className="space-y-3">
            <div className="login-side-stat-card">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Upcoming</span>
                <span className="micro-chip">2h window</span>
              </div>
              <div className="mt-4 space-y-3">
                <TimelineEvent time="09:30" title="Team standup" detail="Owners and blockers" />
                <TimelineEvent time="11:00" title="Launch QA" detail="Final walkthrough" />
                <TimelineEvent time="14:00" title="Stakeholder review" detail="Progress snapshot" />
              </div>
            </div>

            <div className="login-side-stat-card">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Momentum</p>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <MetricPill label="Active" value="18" accent />
                <MetricPill label="Done" value="43" />
                <MetricPill label="Overdue" value="2" warning />
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-emerald-50">
                <div className="h-full w-[78%] rounded-full bg-gradient-to-r from-emerald-500 to-emerald-700" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TaskCard({ title, meta, status, progress }) {
  return (
    <div className="login-task-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">{meta}</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">{status}</span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full w-[72%] rounded-full bg-gradient-to-r from-emerald-500 to-emerald-700" />
        </div>
        <span className="text-xs font-medium text-slate-500">{progress}</span>
      </div>
    </div>
  )
}

function TimelineEvent({ time, title, detail }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1 h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_0_5px_rgba(16,185,129,0.12)]" />
      <div className="flex-1">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <span className="text-xs font-semibold text-slate-400">{time}</span>
        </div>
        <p className="mt-1 text-sm text-slate-500">{detail}</p>
      </div>
    </div>
  )
}

function MetricPill({ label, value, accent = false, warning = false }) {
  const tone = warning
    ? 'border-amber-200 bg-amber-50 text-amber-800'
    : accent
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : 'border-slate-200 bg-white text-slate-700'

  return (
    <div className={`rounded-[18px] border px-3 py-2 ${tone}`}>
      <span className="block text-[10px] font-semibold uppercase tracking-[0.18em]">{label}</span>
      <span className="mt-1 block text-lg font-bold tracking-[-0.03em]">{value}</span>
    </div>
  )
}

function GoogleMark({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        fill="#4285F4"
        d="M21.6 12.23c0-.71-.06-1.23-.2-1.77H12v3.35h5.52c-.11.83-.69 2.08-1.97 2.92l-.02.11 2.71 2.06.19.02c1.74-1.57 2.77-3.88 2.77-6.69Z"
      />
      <path
        fill="#34A853"
        d="M12 21.75c2.7 0 4.97-.87 6.62-2.37l-3.15-2.4c-.84.57-1.97.97-3.47.97-2.64 0-4.88-1.71-5.68-4.08l-.11.01-2.82 2.14-.04.1c1.64 3.18 4.99 5.63 8.65 5.63Z"
      />
      <path
        fill="#FBBC05"
        d="M6.32 13.87A5.77 5.77 0 0 1 6 12c0-.65.12-1.28.31-1.87l-.01-.12-2.86-2.18-.09.04A9.68 9.68 0 0 0 2.4 12c0 1.53.37 2.98 1.03 4.13l2.89-2.26Z"
      />
      <path
        fill="#EA4335"
        d="M12 6.05c1.89 0 3.16.8 3.89 1.46l2.84-2.7C16.96 3.2 14.7 2.25 12 2.25c-3.66 0-7.01 2.45-8.65 5.63l2.96 2.26C7.12 7.76 9.36 6.05 12 6.05Z"
      />
    </svg>
  )
}

function UserIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M15.75 6.75a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 19.125a7.5 7.5 0 0 1 15 0" />
    </svg>
  )
}

function TeamIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M15 19.128a9.38 9.38 0 0 0-3-.503 9.38 9.38 0 0 0-3 .503m6-8.628a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 8.628a7.5 7.5 0 0 0-4.5-6.844M3 19.128a7.5 7.5 0 0 1 4.5-6.844m10.5-1.534a2.25 2.25 0 1 0-4.5 0 2.25 2.25 0 0 0 4.5 0Zm-9 0a2.25 2.25 0 1 0-4.5 0 2.25 2.25 0 0 0 4.5 0Z" />
    </svg>
  )
}
