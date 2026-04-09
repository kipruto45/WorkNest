export default function AccountTypeCard({ value, selected, icon, title, description, helper, onSelect }) {
  const Icon = icon
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`w-full rounded-[20px] border px-4 py-4 text-left transition-all ${
        selected
          ? 'border-emerald-500 bg-emerald-50/70 shadow-[0_12px_28px_rgba(16,185,129,0.18)]'
          : 'border-slate-200 bg-white hover:border-emerald-200 hover:bg-emerald-50/40'
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className={`flex h-11 w-11 items-center justify-center rounded-2xl ${
            selected ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
          }`}
        >
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
          {helper ? <p className="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{helper}</p> : null}
        </div>
      </div>
    </button>
  )
}
