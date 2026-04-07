export default function StatCard({ label, value, hint, accent = 'from-emerald-500 to-teal-500', detail }) {
  return (
    <div className="feature-tile fade-in-delayed">
      <div className={`h-1.5 w-24 rounded-full bg-gradient-to-r ${accent}`} />
      <div className="mt-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{label}</p>
          <p className="mt-2 text-3xl font-extrabold tracking-tight text-emerald-950">{value}</p>
        </div>
        <div className="rounded-2xl bg-emerald-50/90 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">
          Signal
        </div>
      </div>
      {hint ? <p className="mt-3 text-sm leading-6 text-soft">{hint}</p> : null}
      {detail ? <p className="mt-3 text-xs font-medium uppercase tracking-[0.18em] text-emerald-800">{detail}</p> : null}
    </div>
  )
}
