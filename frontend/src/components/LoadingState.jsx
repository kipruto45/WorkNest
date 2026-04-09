export default function LoadingState({ label = 'Loading workspace', description = '' }) {
  return (
    <div className="glass-panel flex min-h-[240px] items-center justify-center p-6">
      <div className="w-full max-w-sm text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-[18px] border border-slate-200 bg-white text-slate-700 shadow-[0_10px_22px_rgba(15,23,42,0.05)]">
          <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" />
            <path className="opacity-90" fill="currentColor" d="M12 2a10 10 0 0 1 10 10h-3A7 7 0 0 0 12 5V2Z" />
          </svg>
        </div>
        <p className="mt-4 text-sm font-semibold text-slate-900">{label}</p>
        {description ? <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p> : null}
        <div className="mx-auto mt-5 grid max-w-xs gap-2">
          <div className="h-2.5 rounded-full bg-slate-200/80" />
          <div className="h-2.5 rounded-full bg-slate-100" />
          <div className="h-2.5 w-2/3 rounded-full bg-slate-100" />
        </div>
      </div>
    </div>
  )
}
