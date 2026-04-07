import { useState } from 'react'

export default function PasswordField({
  label,
  name,
  register,
  error,
  placeholder,
  requiredMessage,
  autoComplete = 'current-password',
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div>
      {label ? <label className="mb-2 block text-sm font-semibold text-emerald-950">{label}</label> : null}
      <div className="relative">
        <input
          type={visible ? 'text' : 'password'}
          {...register(name, requiredMessage ? { required: requiredMessage } : undefined)}
          className="input-field pr-12"
          placeholder={placeholder}
          autoComplete={autoComplete}
        />
        <button
          type="button"
          onClick={() => setVisible((current) => !current)}
          className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-slate-500 transition-colors hover:text-emerald-700"
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
        >
          {visible ? <EyeOffIcon className="h-5 w-5" /> : <EyeIcon className="h-5 w-5" />}
        </button>
      </div>
      {error ? <p className="mt-2 text-sm text-red-500">{error.message}</p> : null}
    </div>
  )
}

function EyeIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"
      />
      <circle cx="12" cy="12" r="3" strokeWidth={1.8} />
    </svg>
  )
}

function EyeOffIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M3 3 21 21M10.58 10.58A2 2 0 0 0 10 12a2 2 0 0 0 3.42 1.42M6.71 6.72C4.4 8.26 2.95 10.93 2.5 12c0 0 3.5 6.5 9.5 6.5 1.76 0 3.28-.56 4.56-1.35M14.95 9.05A9.9 9.9 0 0 0 12 5.5C6 5.5 2.5 12 2.5 12a16.6 16.6 0 0 0 2.3 3.44"
      />
    </svg>
  )
}
