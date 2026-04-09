export default function StatCard({ label, value, hint, accent = 'from-emerald-500 to-teal-500', detail }) {
  return (
    <div className="feature-tile fade-in-delayed">
      <div className="flex items-center justify-between gap-4">
        <div className={`h-1.5 w-20 rounded-full bg-gradient-to-r ${accent}`} />
        <span className="micro-chip">Live</span>
      </div>
      <div className="mt-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">{value}</p>
        </div>
      </div>
      {hint ? <p className="mt-3 text-sm leading-6 text-soft">{hint}</p> : null}
      {detail ? <p className="mt-3 text-xs font-medium uppercase tracking-[0.18em] text-slate-600">{detail}</p> : null}
    </div>
  )
}
