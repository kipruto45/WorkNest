import { useState } from 'react'
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

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || /\S+@\S+\.\S+/.test(value), 'Enter a valid email address'),
    phone_number: z
      .string()
      .trim()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || /^[+0-9()\-\s]{9,20}$/.test(value), 'Enter a valid phone number'),
    phone_country_code: z.string().trim().optional().or(z.literal('')),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    password_confirm: z.string().min(8, 'Please confirm your password'),
    account_type: z.enum(['personal', 'team']),
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
  .refine((data) => Boolean(data.email?.trim() || data.phone_number?.trim()), {
    message: 'Add an email address or phone number to continue',
    path: ['email'],
  })

export default function Register() {
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [formError, setFormError] = useState('')
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || '/dashboard'
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
      account_type: 'personal',
      team_name: '',
      phone_country_code: '+254',
    },
  })

  const onSubmit = async (data) => {
    setLoading(true)
    setFormError('')
    clearErrors()
    try {
      const payload = {
        ...data,
        email: data.email?.trim() || '',
        phone_number: data.phone_number?.trim() || '',
        phone_country_code: data.phone_country_code?.trim() || '',
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
    setGoogleLoading(true)
    try {
      const response = await authAPI.getGoogleLoginUrl(nextPath)
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

  return (
    <AuthShell
      title="Create your workspace account"
      subtitle="Create your account and start organizing work with your team."
      showPresentationSpotlight={false}
      compact
      footer={
        <p>
          Already have an account?{' '}
          <Link
            className="font-semibold text-emerald-700 hover:text-emerald-800"
            to={`/login?next=${encodeURIComponent(nextPath)}`}
          >
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="grid gap-3">
        <input type="hidden" {...register('account_type')} />
        {formError ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</div>
        ) : null}
        <div className="rounded-[22px] border border-slate-200 bg-white p-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Account type</p>
          <h3 className="mt-1.5 text-base font-semibold text-slate-950">Choose your workspace mode</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">Pick the starting mode that matches how you plan to work.</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <AccountTypeCard
              value="personal"
              selected={watch('account_type') === 'personal'}
              onSelect={(value) => {
                setValue('account_type', value, { shouldValidate: true })
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
                setValue('account_type', value, { shouldValidate: true })
                clearErrors('account_type')
              }}
              icon={TeamIcon}
              title="Team account"
              description="Create a workspace, invite members, and track team progress."
              helper="Shared collaboration"
              compact
            />
          </div>
          {errors.account_type ? <p className="mt-2 text-sm text-red-500">{errors.account_type.message}</p> : null}
        </div>
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={googleLoading}
          className="btn-secondary w-full justify-center"
        >
          {googleLoading ? (
            'Connecting to Google...'
          ) : (
            <span className="flex items-center gap-3">
              <img src="/google.png" alt="" className="h-5 w-5" />
              Sign up with Google
            </span>
          )}
        </button>

        <div className="flex items-center gap-3">
          <div className="soft-divider" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-soft">or</span>
          <div className="soft-divider" />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Full name</label>
            <input {...register('name')} className="input-field" placeholder="Alex Morgan" />
            {errors.name ? <p className="mt-2 text-sm text-red-500">{errors.name.message}</p> : null}
          </div>
          {watch('account_type') === 'team' ? (
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Team name</label>
              <input {...register('team_name')} className="input-field" placeholder="Growth Squad" />
              {errors.team_name ? <p className="mt-2 text-sm text-red-500">{errors.team_name.message}</p> : null}
            </div>
          ) : (
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Email</label>
              <input type="email" {...register('email')} className="input-field" placeholder="name@company.com" />
              <p className="mt-2 text-xs text-soft">Optional if you prefer to start with phone-based sign in.</p>
              {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
            </div>
          )}

          {watch('account_type') === 'team' ? (
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Email</label>
              <input type="email" {...register('email')} className="input-field" placeholder="name@company.com" />
              <p className="mt-2 text-xs text-soft">Optional if you prefer to start with phone-based sign in.</p>
              {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
            </div>
          ) : null}

          <div className={watch('account_type') === 'team' ? 'sm:col-span-2' : ''}>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Phone number</label>
            <div className="grid gap-2 sm:grid-cols-[112px,1fr]">
              <div>
                <input {...register('phone_country_code')} className="input-field" placeholder="+254" />
                {errors.phone_country_code ? <p className="mt-2 text-sm text-red-500">{errors.phone_country_code.message}</p> : null}
              </div>
              <div>
                <input {...register('phone_number')} className="input-field" placeholder="+254712345678" />
                <p className="mt-2 text-xs text-soft">Optional if you prefer phone-first registration and login.</p>
                {errors.phone_number ? <p className="mt-2 text-sm text-red-500">{errors.phone_number.message}</p> : null}
              </div>
            </div>
          </div>

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
          {loading ? 'Creating account...' : 'Create Account'}
        </button>
      </form>
    </AuthShell>
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
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 21v-1a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v1M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm9 10v-1a4 4 0 0 0-3-3.87M15 3.13A4 4 0 0 1 15 11" />
    </svg>
  )
}
