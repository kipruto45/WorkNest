export default function LoadingState({ label = 'Loading workspace' }) {
  return (
    <div className="glass-panel flex min-h-[240px] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="pulse-glow flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
          <svg className="h-7 w-7 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-90" fill="currentColor" d="M12 2a10 10 0 0 1 10 10h-3A7 7 0 0 0 12 5V2Z" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-soft">{label}</p>
      </div>
    </div>
  )
}
