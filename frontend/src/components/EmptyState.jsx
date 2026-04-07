export default function EmptyState({ title, description, action, eyebrow = 'Empty state' }) {
  return (
    <div className="feature-tile bg-grid text-center fade-in">
      <div className="micro-chip mx-auto">{eyebrow}</div>
      <div className="mx-auto mt-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-emerald-100 text-emerald-700 shadow-glow">
        <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M12 6v12m6-6H6"
          />
        </svg>
      </div>
      <h3 className="mt-5 text-xl font-bold text-emerald-950 text-balance">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-soft">{description}</p>
      {action ? <div className="mt-5 flex justify-center">{action}</div> : null}
    </div>
  )
}
