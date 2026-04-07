import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import { login } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'

export default function Login() {
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next') || '/dashboard'
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: '',
      password: '',
      remember_me: true,
    },
  })

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await dispatch(login(data)).unwrap()
      toast.success('Welcome back to your workspace.')
      navigate(nextPath)
    } catch (error) {
      toast.error(error || 'Sign in failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    setGoogleLoading(true)
    try {
      const response = await authAPI.getGoogleLoginUrl()
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
      title="Welcome back"
      subtitle="Sign in to continue to your tasks, teams, and recent activity."
      footer={
        <p>
          New here?{' '}
          <Link
            className="font-semibold text-emerald-700 hover:text-emerald-800"
            to={`/register?next=${encodeURIComponent(nextPath)}`}
          >
            Create an account
          </Link>
        </p>
      }
    >
      <div className="space-y-4">
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
          <div>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Email</label>
            <input
              type="email"
              {...register('email', { required: 'Email is required' })}
              className="input-field"
              placeholder="name@company.com"
            />
            {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
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
