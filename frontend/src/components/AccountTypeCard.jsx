export default function AccountTypeCard({ value, selected, icon, title, description, helper, onSelect, compact = false }) {
  const Icon = icon
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`w-full rounded-[20px] border text-left transition-all ${compact ? 'px-3.5 py-3' : 'px-4 py-4'} ${
        selected
          ? 'border-emerald-500 bg-emerald-50/70 shadow-[0_12px_28px_rgba(16,185,129,0.18)]'
          : 'border-slate-200 bg-white hover:border-emerald-200 hover:bg-emerald-50/40'
      }`}
    >
      <div className={`flex items-start ${compact ? 'gap-2.5' : 'gap-3'}`}>
        <span
          className={`flex items-center justify-center rounded-2xl ${compact ? 'h-9 w-9' : 'h-11 w-11'} ${
            selected ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
          }`}
        >
          <Icon className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className={`text-slate-500 ${compact ? 'mt-0.5 text-xs leading-5' : 'mt-1 text-sm'}`}>{description}</p>
          {helper ? <p className={`${compact ? 'mt-1.5 text-[10px]' : 'mt-2 text-xs'} font-semibold uppercase tracking-[0.18em] text-emerald-700`}>{helper}</p> : null}
        </div>
      </div>
    </button>
  )
}
