import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import AuthShell from '../components/AuthShell'
import { authAPI } from '../services/api'

export default function ForgotPassword() {
  const [loading, setLoading] = useState(false)
  const [submittedEmail, setSubmittedEmail] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm()

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await authAPI.requestPasswordReset(data)
      setSubmittedEmail(data.email)
      toast.success('Reset instructions have been sent if the account exists.')
    } catch (error) {
      toast.error('Unable to request password reset right now.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="Enter the email linked to your account and we’ll send you a secure reset link."
      footer={
        <p>
          Back to{' '}
          <Link className="font-semibold text-emerald-700 hover:text-emerald-800" to="/login">
            sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-semibold text-emerald-950">Email address</label>
          <input
            type="email"
            {...register('email', { required: 'Email is required' })}
            className="input-field"
            placeholder="name@company.com"
          />
          {errors.email ? <p className="mt-2 text-sm text-red-500">{errors.email.message}</p> : null}
        </div>

        {submittedEmail ? (
          <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-800">
            A reset message has been queued for <span className="font-semibold">{submittedEmail}</span>. If that inbox
            exists in WorkNest, you’ll receive a link shortly.
          </div>
        ) : null}

        <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
          {loading ? 'Sending link...' : 'Send reset link'}
        </button>
      </form>
    </AuthShell>
  )
}
