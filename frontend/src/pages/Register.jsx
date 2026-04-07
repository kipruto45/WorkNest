import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import { register as registerUser } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    password_confirm: z.string().min(8, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  })

export default function Register() {
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
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      const payload = { ...data, email: data.email.trim(), name: data.name.trim() }
      const result = await dispatch(registerUser(payload)).unwrap()
      const loginParams = new URLSearchParams({
        registered: '1',
        email: result?.email || payload.email,
        next: nextPath,
      })
      toast.success('Account created successfully. Sign in to continue.')
      navigate(`/login?${loginParams.toString()}`, { replace: true })
    } catch (error) {
      toast.error(error || 'Registration failed')
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
        return
      }
      toast.error('Google sign-in is not configured yet.')
    } catch (error) {
      toast.error('Unable to start Google sign-in right now.')
    } finally {
      setGoogleLoading(false)
    }
  }

  return (
    <AuthShell
      title="Create your workspace account"
      subtitle="Create your account and start organizing work with your team."
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
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
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
        <div>
          <label className="mb-2 block text-sm font-semibold text-emerald-950">Full name</label>
          <input {...register('name')} className="input-field" placeholder="Alex Morgan" />
          {errors.name ? <p className="mt-2 text-sm text-red-500">{errors.name.message}</p> : null}
        </div>

        <div>
          <label className="mb-2 block text-sm font-semibold text-emerald-950">Email</label>
          <input type="email" {...register('email')} className="input-field" placeholder="name@company.com" />
          {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
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
