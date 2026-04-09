export default function AccountTypeCard({ value, selected, icon, title, description, helper, onSelect, compact = false }) {
  const Icon = icon
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`w-full rounded-[22px] border text-left transition-all duration-200 ${compact ? 'px-3.5 py-3.5' : 'px-4.5 py-4.5'} ${
        selected
          ? 'border-emerald-400/80 bg-[linear-gradient(180deg,rgba(236,253,245,0.95),rgba(255,255,255,0.98))] shadow-[0_16px_34px_rgba(16,185,129,0.16)]'
          : 'border-slate-200/90 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(249,250,247,0.96))] hover:-translate-y-[1px] hover:border-emerald-200 hover:bg-emerald-50/30 hover:shadow-[0_14px_30px_rgba(15,23,42,0.06)]'
      }`}
    >
      <div className={`flex items-start ${compact ? 'gap-2.5' : 'gap-3'}`}>
        <span
          className={`flex items-center justify-center rounded-[18px] border ${compact ? 'h-9 w-9' : 'h-11 w-11'} ${
            selected
              ? 'border-emerald-500 bg-emerald-600 text-white shadow-[0_10px_20px_rgba(16,185,129,0.18)]'
              : 'border-slate-200 bg-white text-slate-600'
          }`}
        >
          <Icon className={compact ? 'h-4 w-4' : 'h-5 w-5'} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-[-0.02em] text-slate-950">{title}</p>
          <p className={`text-slate-500 ${compact ? 'mt-1 text-[12px] leading-[1.45]' : 'mt-1.5 text-sm leading-6'}`}>{description}</p>
          {helper ? <p className={`${compact ? 'mt-2 text-[10px]' : 'mt-2.5 text-xs'} font-semibold uppercase tracking-[0.18em] text-emerald-700`}>{helper}</p> : null}
        </div>
      </div>
    </button>
  )
}
