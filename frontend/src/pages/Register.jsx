import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import AccountTypeCard from '../components/AccountTypeCard'
import { register as registerUser } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { resolvePostAuthPath } from '../utils/authRouting'

const phonePattern = /^\+254\d{9}$/

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z
      .string()
      .trim()
      .min(1, 'Email is required')
      .refine((value) => /\S+@\S+\.\S+/.test(value), 'Enter a valid email address'),
    phone_number: z
      .string()
      .trim()
      .min(1, 'Phone number is required')
      .refine((value) => phonePattern.test(value), 'Enter a valid phone number with +254'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    password_confirm: z.string().min(8, 'Please confirm your password'),
    account_type: z.string().refine((value) => ['personal', 'team'].includes(value), 'Choose your workspace mode'),
    team_name: z.string().optional(),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  })
  .refine((data) => (data.account_type === 'team' ? Boolean(data.team_name?.trim()) : true), {
    message: 'Team name is required for team accounts',
    path: ['team_name'],
  })

export default function Register() {
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [formError, setFormError] = useState('')
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || '/dashboard'
  const authError = searchParams.get('error')
  const {
    register,
    setError,
    clearErrors,
    watch,
    setValue,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      account_type: '',
      team_name: '',
      email: '',
      phone_number: '+254',
    },
  })

  useEffect(() => {
    if (!authError) return

    const errorMessages = {
      google_auth_failed: 'Google sign-in could not be completed.',
      google_token_exchange_failed:
        'Google sign-in could not be completed. Check the backend Google client secret and redirect URI.',
      google_userinfo_failed: 'Google sign-in could not fetch your Google profile.',
      no_authorization_code: 'Google sign-in did not return an authorization code.',
      no_access_token: 'Google sign-in did not return an access token.',
      no_email: 'Google did not return an email address for this account.',
      account_type_required: 'Choose your workspace mode before continuing with Google.',
      account_type_mismatch: 'Selected workspace mode does not match this account.',
    }

    toast.error(errorMessages[authError] || 'Sign up could not be completed.')
  }, [authError])

  const onSubmit = async (data) => {
    setLoading(true)
    setFormError('')
    clearErrors()
    try {
      const payload = {
        ...data,
        email: data.email.trim(),
        phone_number: data.phone_number.trim(),
        phone_country_code: '+254',
        name: data.name.trim(),
        team_name: data.team_name?.trim() || '',
      }
      const result = await dispatch(registerUser(payload)).unwrap()
      const destination = resolvePostAuthPath({ nextPath, user: result?.user })
      if (result?.user?.email && !result.user.email_verified) {
        toast.success('Account created. We also sent a verification email to help secure your account.')
      } else {
        toast.success('Account created successfully.')
      }
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
      const message = normalizedError.message || 'Registration failed'
      setFormError(message)
      toast.error(message)
      if (normalizedError.requestId || normalizedError.status) {
        console.error('auth_register_failed', {
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
    const trimmedTeamName = (watch('team_name') || '').trim()
    if (!selectedAccountType) {
      setError('account_type', { message: 'Choose your workspace mode' })
      return
    }
    if (selectedAccountType === 'team' && !trimmedTeamName) {
      setError('team_name', { message: 'Team name is required for team accounts' })
      return
    }
    setGoogleLoading(true)
    try {
      const response = await authAPI.getGoogleLoginUrl(nextPath, selectedAccountType, 'register', trimmedTeamName)
      const payload = unwrapData(response)
      if (payload?.login_url) {
        window.location.href = payload.login_url
        return
      }
      toast.error('Google sign-in is not available.')
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

  const isTeamAccount = watch('account_type') === 'team'

  return (
    <AuthShell
      title="Create your WorkNest account"
      subtitle="Set up your account, choose your workspace mode, and start from a calmer operating system for work."
      compact
      heroLabel="WorkNest onboarding"
      heroHeadline="Start with a workspace that already feels structured."
      heroDescription="From first account setup to daily execution, WorkNest keeps planning, visibility, and delivery composed from the beginning."
      heroVisual={<RegisterProductVisual />}
      heroBottom={<RegisterWorkflowSummary />}
      mobileHero={<MobileRegisterHero />}
      heroPanelClassName="register-brand-panel fade-in-delayed"
      cardClassName="register-auth-card"
      logoSubtitle="Structured signup for focused teams"
      footer={
        <p className="text-sm leading-6 text-slate-500">
          Already have an account?{' '}
          <Link
            className="font-semibold text-emerald-700 transition-colors hover:text-emerald-800"
            to={`/login?next=${encodeURIComponent(nextPath)}`}
          >
            Sign in
          </Link>
        </p>
      }
    >
      <div className="space-y-4">
        <input type="hidden" {...register('account_type')} />

        {formError ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>
        ) : null}

        <div className="auth-section-panel register-selector-panel">
          <p className="auth-section-eyebrow">Workspace mode</p>
          <h3 className="auth-section-title">Choose how you want to begin</h3>
          <p className="auth-section-copy">
            Pick the account shape that matches this signup. Google and manual registration follow the same mode.
          </p>
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
              description="Manage personal tasks, schedules, and deadlines."
              helper="Focused productivity"
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
              description="Create a workspace, invite members, assign work, and track team progress."
              helper="Shared collaboration"
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
              Sign up with Google
            </span>
          )}
        </button>

        <div className="flex items-center gap-2.5">
          <div className="soft-divider" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">or</span>
          <div className="soft-divider" />
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form-stack">
          <div className="auth-section-panel register-form-panel">
            <div className="mb-4">
              <p className="auth-section-eyebrow">Registration details</p>
              <h3 className="auth-section-title">Create your account</h3>
              <p className="auth-section-copy">Add the details required for secure sign-in, verification, and onboarding.</p>
            </div>

            <div className="grid gap-3">
              <div className={`grid gap-3 ${isTeamAccount ? 'sm:grid-cols-2' : ''}`}>
                <div className="auth-field-group">
                  <label className="auth-field-label">Full name</label>
                  <input {...register('name')} className="input-field auth-input" placeholder="Alex Morgan" />
                  {errors.name ? <p className="mt-1 text-sm text-red-500">{errors.name.message}</p> : null}
                </div>

                {isTeamAccount ? (
                  <div className="auth-field-group">
                    <label className="auth-field-label">Team name</label>
                    <input {...register('team_name')} className="input-field auth-input" placeholder="Growth Squad" />
                    {errors.team_name ? <p className="mt-1 text-sm text-red-500">{errors.team_name.message}</p> : null}
                  </div>
                ) : null}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="auth-field-group">
                  <label className="auth-field-label">Email</label>
                  <input type="email" {...register('email')} className="input-field auth-input" placeholder="name@company.com" />
                  {errors.email ? <p className="mt-1 text-sm text-red-500">{errors.email.message}</p> : null}
                </div>

                <div className="auth-field-group">
                  <label className="auth-field-label">Phone number</label>
                  <input
                    type="text"
                    {...register('phone_number')}
                    className="input-field auth-input"
                    placeholder="+254712345678"
                  />
                  <p className="auth-helper-copy">Use a valid number with `+254` for verification and alerts.</p>
                  {errors.phone_number ? <p className="mt-1 text-sm text-red-500">{errors.phone_number.message}</p> : null}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <PasswordField
                  label="Password"
                  name="password"
                  register={register}
                  error={errors.password}
                  placeholder="Create password"
                  autoComplete="new-password"
                  inputClassName="auth-input"
                  toggleButtonClassName="auth-password-toggle"
                />

                <PasswordField
                  label="Confirm password"
                  name="password_confirm"
                  register={register}
                  error={errors.password_confirm}
                  placeholder="Confirm password"
                  autoComplete="new-password"
                  inputClassName="auth-input"
                  toggleButtonClassName="auth-password-toggle"
                />
              </div>
            </div>
          </div>

          <button type="submit" disabled={loading} className="register-submit-button w-full justify-center">
            {loading ? 'Creating account...' : isTeamAccount ? 'Create workspace' : 'Create account'}
          </button>
        </form>
      </div>
    </AuthShell>
  )
}

function MobileRegisterHero() {
  return (
    <div className="register-mobile-hero fade-in">
      <div className="stat-chip inline-flex items-center gap-2">
        <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
        WorkNest onboarding
      </div>
      <h1 className="mt-4 font-display text-[2rem] font-bold leading-tight tracking-[-0.04em] text-slate-950">
        Start from a workspace that already feels organized.
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Create your account, choose your mode, and move into a calmer planning system from day one.
      </p>
    </div>
  )
}

function RegisterWorkflowSummary() {
  const items = [
    { title: 'Capture', description: 'Create and structure work instantly' },
    { title: 'Collaborate', description: 'Keep context visible with comments and mentions' },
    { title: 'Deliver', description: 'Track deadlines and move work forward' },
  ]

  return (
    <div className="register-workflow-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">How WorkNest works</p>
          <h3 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-950">Built for calm execution</h3>
        </div>
        <span className="micro-chip">From first login</span>
      </div>
      <div className="mt-4 grid gap-3">
        {items.map((item) => (
          <div key={item.title} className="register-workflow-row">
            <div className="register-workflow-dot" />
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

function RegisterProductVisual() {
  return (
    <div className="register-product-stage">
      <div className="register-floating-chip register-floating-chip-left">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-800">Team invites</span>
        <span className="mt-1 block text-xl font-bold tracking-[-0.04em] text-slate-950">04</span>
      </div>
      <div className="register-floating-chip register-floating-chip-right">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Setup status</span>
        <span className="mt-1 block text-sm font-semibold text-slate-950">Workspace ready in minutes</span>
      </div>

      <div className="register-product-window">
        <div className="register-window-bar">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
            <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Workspace setup</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.15fr,0.85fr]">
          <div className="space-y-3">
            <div className="register-summary-card">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">New workspace</p>
                <h3 className="mt-2 text-xl font-bold tracking-[-0.04em] text-slate-950">Product operations hub</h3>
              </div>
              <div className="rounded-2xl bg-emerald-600 px-3 py-2 text-right text-white shadow-[0_14px_30px_rgba(5,150,105,0.18)]">
                <span className="block text-[11px] uppercase tracking-[0.18em] text-emerald-50/80">Launch status</span>
                <span className="mt-1 block text-lg font-bold">Ready</span>
              </div>
            </div>

            <div className="grid gap-3">
              <RegisterSetupCard
                title="Choose workspace mode"
                meta="Step 1"
                status="Active"
                detail="Pick personal or team setup"
              />
              <RegisterSetupCard
                title="Invite core teammates"
                meta="Step 2"
                status="Queued"
                detail="Share access and roles"
              />
              <RegisterSetupCard
                title="Create your first board"
                meta="Step 3"
                status="Next"
                detail="Start with tasks, deadlines, and owners"
              />
            </div>
          </div>

          <div className="space-y-3">
            <div className="register-side-card">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Starter visibility</p>
              <div className="mt-4 space-y-3">
                <RegisterChecklistItem label="Tasks and due dates" state="Ready" />
                <RegisterChecklistItem label="Comments and mentions" state="Ready" />
                <RegisterChecklistItem label="Member permissions" state="Ready" />
                <RegisterChecklistItem label="Dashboard analytics" state="Ready" />
              </div>
            </div>

            <div className="register-side-card">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">First week outcomes</p>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <RegisterMetricPill label="Tasks" value="24" accent />
                <RegisterMetricPill label="Members" value="08" />
                <RegisterMetricPill label="On time" value="91%" accent />
              </div>
              <div className="mt-4 rounded-[18px] border border-emerald-100 bg-emerald-50/70 px-3 py-3">
                <p className="text-sm font-semibold text-emerald-900">Clear onboarding, cleaner execution.</p>
                <p className="mt-1 text-sm leading-5 text-emerald-800/80">
                  Set up once, then manage tasks, ownership, and delivery from a single system.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RegisterSetupCard({ title, meta, status, detail }) {
  return (
    <div className="register-setup-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">{meta}</p>
        </div>
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">{status}</span>
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-500">{detail}</p>
    </div>
  )
}

function RegisterChecklistItem({ label, state }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[18px] border border-slate-100 bg-white/90 px-3 py-3">
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_0_5px_rgba(16,185,129,0.12)]" />
        <span className="text-sm font-medium text-slate-700">{label}</span>
      </div>
      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{state}</span>
    </div>
  )
}

function RegisterMetricPill({ label, value, accent = false }) {
  return (
    <div
      className={`rounded-[18px] border px-3 py-2 ${
        accent ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-700'
      }`}
    >
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
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 21v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
    </svg>
  )
}

function TeamIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M16 21v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm9 10v-1a4 4 0 0 0-3-3.87M15 3.13A4 4 0 0 1 15 11"
      />
    </svg>
  )
}
