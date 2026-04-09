export default function EmptyState({ title, description, action, eyebrow = 'Empty state' }) {
  return (
    <div className="feature-tile bg-grid text-center fade-in">
      <div className="micro-chip mx-auto">{eyebrow}</div>
      <div className="mx-auto mt-5 flex h-14 w-14 items-center justify-center rounded-[20px] border border-slate-200 bg-white text-slate-700 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
        <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M12 6v12m6-6H6"
          />
        </svg>
      </div>
      <h3 className="mt-5 text-xl font-bold text-slate-950 text-balance">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-soft">{description}</p>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  )
}
