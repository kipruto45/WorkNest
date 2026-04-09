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
import { hydrateCurrentUser, register as registerUser, setUser } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { resolvePostAuthPath } from '../utils/authRouting'
import { beginGoogleAuth, clearGoogleAuthState } from '../utils/googleAuthState'

const phonePattern = /^\+254\d{9}$/
const registerHeroPhrases = [
  { text: 'Launch with structure.', emphasis: 'structure' },
  { text: 'Invite the right people fast.', emphasis: 'right people' },
  { text: 'Start tracking real work immediately.', emphasis: 'real work' },
  { text: 'Keep every owner aligned from day one.', emphasis: 'aligned' },
]

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
  const [activePhraseIndex, setActivePhraseIndex] = useState(0)
  const [visiblePhrase, setVisiblePhrase] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || '/dashboard'
  const accountTypeHint = searchParams.get('account_type')
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

  useEffect(() => {
    if (accountTypeHint !== 'personal' && accountTypeHint !== 'team') {
      return
    }
    setValue('account_type', accountTypeHint, { shouldValidate: true, shouldDirty: true })
    if (accountTypeHint === 'personal') {
      setValue('team_name', '', { shouldValidate: false, shouldDirty: false })
    }
    clearErrors('account_type')
  }, [accountTypeHint, clearErrors, setValue])

  useEffect(() => {
    const currentPhrase = registerHeroPhrases[activePhraseIndex].text
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
        setActivePhraseIndex((index) => (index + 1) % registerHeroPhrases.length)
      }, 160)
    }

    return () => window.clearTimeout(timer)
  }, [activePhraseIndex, isDeleting, visiblePhrase])

  const activePhrase = registerHeroPhrases[activePhraseIndex]

  const onSubmit = async (data) => {
    setLoading(true)
    setFormError('')
    clearErrors()
    try {
      const selectedAccountType = watch('account_type')
      const payload = {
        ...data,
        account_type: selectedAccountType,
        email: data.email.trim(),
        phone_number: data.phone_number.trim(),
        phone_country_code: '+254',
        name: data.name.trim(),
        team_name: data.team_name?.trim() || '',
      }
      const result = await dispatch(registerUser(payload)).unwrap()
      let authenticatedUser = result?.user
      try {
        authenticatedUser = await dispatch(hydrateCurrentUser()).unwrap()
      } catch (_error) {
        authenticatedUser = result?.user
      }
      if (selectedAccountType === 'team' && authenticatedUser) {
        const normalizedUser = { ...authenticatedUser, account_type: 'team' }
        dispatch(setUser(normalizedUser))
        authenticatedUser = normalizedUser
      }
      const destination = resolvePostAuthPath({
        nextPath,
        user: authenticatedUser,
      })
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
      beginGoogleAuth({ flow: 'register', accountType: selectedAccountType, nextPath })
      const response = await authAPI.getGoogleLoginUrl(nextPath, selectedAccountType, 'register', trimmedTeamName)
      const payload = unwrapData(response)
      if (payload?.login_url) {
        window.location.assign(payload.login_url)
        return
      }
      clearGoogleAuthState()
      setGoogleLoading(false)
      toast.error('Google sign-in is not available.')
    } catch (error) {
      clearGoogleAuthState()
      setGoogleLoading(false)
      const backendMessage =
        error?.response?.data?.errors?.non_field_errors?.[0] ||
        error?.response?.data?.errors?.detail ||
        error?.response?.data?.message ||
        error?.message
      toast.error(backendMessage || 'Unable to start Google sign-in right now.')
    }
  }

  const isTeamAccount = watch('account_type') === 'team'

  return (
    <AuthShell
      title="Create your workspace account"
      subtitle="Create your account and start organizing work."
      compact
      shellClassName="overflow-y-auto py-4 lg:py-6"
      heroLabel="WorkNest onboarding"
      heroHeadline="Start with a workspace that already feels composed."
      heroDescription="Set your mode, confirm your details, and start from a calmer operating system."
      heroVisual={<RegisterHeroVisual visiblePhrase={visiblePhrase} emphasis={activePhrase.emphasis} />}
      heroBottom={<RegisterHeroSummary />}
      mobileHero={<AuthMobileHero label="WorkNest onboarding" title="Create your account and start with structure." phrase={visiblePhrase} emphasis={activePhrase.emphasis} />}
      heroPanelClassName="register-brand-panel fade-in-delayed"
      cardClassName="register-auth-card"
      logoSubtitle="Structured signup for focused teams"
      footer={
        <p>
          Already have an account?{' '}
          <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to={`/login?next=${encodeURIComponent(nextPath)}`}>
            Sign in
          </Link>
        </p>
      }
    >
      <div className="space-y-3">
        <input type="hidden" {...register('account_type')} />

        {formError ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>
        ) : null}

        <div className="rounded-[22px] border border-slate-200 bg-white p-3.5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Account type</p>
          <h3 className="mt-1.5 text-base font-semibold text-slate-950">Choose your workspace mode</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">Choose the workspace this account should open into.</p>
          <div className="mt-2.5 grid grid-cols-2 gap-2">
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

        <button type="button" onClick={handleGoogleLogin} disabled={googleLoading || !watch('account_type')} className="btn-secondary w-full justify-center">
          {googleLoading ? (
            'Redirecting to Google...'
          ) : (
            <span className="flex items-center gap-3">
              <img src="/google.png" alt="" className="h-5 w-5" />
              Sign up with Google
            </span>
          )}
        </button>

        <div className="flex items-center gap-2">
          <div className="soft-divider" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-soft">or</span>
          <div className="soft-divider" />
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-2">
          <div className={`grid gap-2.5 ${isTeamAccount ? 'sm:grid-cols-2' : ''}`}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Full name</label>
              <input {...register('name')} className="input-field" placeholder="Alex Morgan" />
              {errors.name ? <p className="mt-2 text-sm text-red-500">{errors.name.message}</p> : null}
            </div>

            {isTeamAccount ? (
              <div>
                <label className="mb-2 block text-sm font-semibold text-emerald-950">Team name</label>
                <input {...register('team_name')} className="input-field" placeholder="Growth Squad" />
                {errors.team_name ? <p className="mt-2 text-sm text-red-500">{errors.team_name.message}</p> : null}
              </div>
            ) : null}
          </div>

          <div className="grid gap-2.5 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Email</label>
              <input type="email" {...register('email')} className="input-field" placeholder="name@company.com" />
              {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Phone number</label>
              <input type="text" {...register('phone_number')} className="input-field" placeholder="+254712345678" />
              <p className="mt-1.5 text-xs text-soft">Use a valid number with +254 for verification and alerts.</p>
              {errors.phone_number ? <p className="mt-2 text-sm text-red-500">{errors.phone_number.message}</p> : null}
            </div>
          </div>

          <div className="grid gap-2.5 sm:grid-cols-2">
            <PasswordField
              label="Password"
              name="password"
              register={register}
              error={errors.password}
              placeholder="Create password"
              autoComplete="new-password"
            />

            <PasswordField
              label="Confirm password"
              name="password_confirm"
              register={register}
              error={errors.password_confirm}
              placeholder="Confirm password"
              autoComplete="new-password"
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
            {loading ? (isTeamAccount ? 'Creating workspace...' : 'Creating account...') : isTeamAccount ? 'Create workspace' : 'Create account'}
          </button>
        </form>
      </div>
    </AuthShell>
  )
}

function RegisterHeroVisual({ visiblePhrase, emphasis }) {
  return (
    <div className="space-y-4">
      <div className="landing-typewriter-panel max-w-none">
        <div className="landing-typewriter-label">Workspace setup</div>
        <div className="landing-typewriter-line">
          {renderTypedPhrase(visiblePhrase, emphasis)}
          <span className="landing-typewriter-caret" aria-hidden="true" />
        </div>
      </div>

      <div className="rounded-[24px] border border-slate-200 bg-white/92 px-5 py-5 shadow-[0_18px_40px_rgba(15,23,42,0.05)]">
        <div className="grid gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">What opens next</p>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              Choose personal or team mode, confirm your details, and start in a cleaner workspace built for visible execution.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[18px] border border-emerald-100 bg-emerald-50/70 px-4 py-3">
              <p className="text-sm font-semibold text-slate-950">Personal flow</p>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">Plan tasks, set timelines, and keep your own execution visible.</p>
            </div>
            <div className="rounded-[18px] border border-slate-200 bg-slate-50/80 px-4 py-3">
              <p className="text-sm font-semibold text-slate-950">Team flow</p>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">Launch a shared workspace, invite members, and assign work with ownership.</p>
            </div>
          </div>

          <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-950">Included from day one</p>
                <p className="mt-1 text-sm text-slate-500">The account opens with the core operating layer already in place.</p>
              </div>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                Ready
              </span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Identity</p>
                <p className="mt-2 text-sm font-semibold text-slate-950">Email and phone verification</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Structure</p>
                <p className="mt-2 text-sm font-semibold text-slate-950">Deadlines, ownership, and status</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50/80 px-3 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Visibility</p>
                <p className="mt-2 text-sm font-semibold text-slate-950">Boards, updates, and reminders</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RegisterHeroSummary() {
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
    <div className="register-mobile-hero fade-in">
      <div className="stat-chip inline-flex items-center gap-2">
        <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
        {label}
      </div>
      <h1 className="mt-4 font-display text-[2rem] font-bold leading-tight tracking-[-0.04em] text-slate-950">{title}</h1>
      <div className="landing-typewriter-panel mt-4 max-w-none">
        <div className="landing-typewriter-label">Launch mode</div>
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
    return <span className="text-slate-400">Launch with structure.</span>
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
