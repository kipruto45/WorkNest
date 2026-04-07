import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import PasswordField from '../components/PasswordField'
import { authAPI } from '../services/api'

export default function ResetPassword() {
  const [loading, setLoading] = useState(false)
  const [linkState, setLinkState] = useState('ready')
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const uid = searchParams.get('uid') || ''
  const token = searchParams.get('token') || ''
  const linkReady = useMemo(() => Boolean(uid && token), [token, uid])
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm()

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await authAPI.confirmPasswordReset({
        uid,
        token,
        new_password: data.new_password,
        new_password_confirm: data.new_password_confirm,
      })
      toast.success('Password updated. You can sign in now.')
      setLinkState('success')
      navigate('/login')
    } catch (error) {
      const message = error?.response?.data?.errors?.token || 'Reset link is invalid or expired.'
      toast.error(message)
      setLinkState('invalid')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Choose a new password"
      subtitle="Create a strong password and continue back into your workspace."
      footer={
        <p>
          Return to{' '}
          <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to="/login">
            sign in
          </Link>
        </p>
      }
    >
      {!linkReady || linkState === 'invalid' ? (
        <div className="rounded-2xl bg-red-50 px-4 py-4 text-sm leading-6 text-red-700">
          {!linkReady
            ? 'This reset link is missing the required credentials. Open the latest email again and retry.'
            : 'This reset link is invalid or expired. Request a fresh reset email to continue securely.'}
          <div className="mt-4">
            <Link className="font-semibold text-red-700 underline-offset-4 hover:underline" to="/forgot-password">
              Request a new reset link
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <PasswordField
            label="New password"
            name="new_password"
            register={register}
            error={errors.new_password}
            placeholder="Minimum 8 characters"
            requiredMessage="New password is required"
            autoComplete="new-password"
          />

          <PasswordField
            label="Confirm password"
            name="new_password_confirm"
            register={register}
            error={errors.new_password_confirm}
            placeholder="Repeat your password"
            requiredMessage="Please confirm your password"
            autoComplete="new-password"
          />

          <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
            {loading ? 'Updating password...' : 'Update password'}
          </button>
        </form>
      )}
    </AuthShell>
  )
}
