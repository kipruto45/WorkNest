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
    watch,
    setValue,
    setError,
    clearErrors,
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
      heroImageSrc="/register.jpeg"
      heroImageAlt="WorkNest workspace preview"
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
        <div className="rounded-[22px] border border-slate-200 bg-white p-3.5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
          <input
            type="hidden"
            {...register('account_type', {
              validate: (value) => ['personal', 'team'].includes(value) || 'Choose your workspace mode',
            })}
          />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Workspace mode</p>
          <h3 className="mt-1.5 text-base font-semibold text-slate-950">Choose your account context</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Google and direct sign-in follow the selected workspace mode so you land in the right experience immediately.
          </p>
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

        <button type="button" onClick={handleGoogleLogin} disabled={googleLoading || !watch('account_type')} className="btn-secondary w-full justify-center">
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
