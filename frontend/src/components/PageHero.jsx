export default function PageHero({ eyebrow, title, description, actions, aside, stats = [], spotlight }) {
  return (
    <section className="hero-panel fade-in">
      <div className="absolute right-0 top-0 h-36 w-36 rounded-full bg-emerald-500/6 blur-3xl" />
      <div className="absolute bottom-0 left-10 h-24 w-24 rounded-full bg-emerald-500/5 blur-2xl" />
      <div className="relative grid gap-6 xl:grid-cols-[minmax(0,1.28fr),minmax(280px,0.72fr)]">
        <div className="flex flex-col gap-5">
          {eyebrow ? <div className="stat-chip">{eyebrow}</div> : null}
          <h1 className="page-title text-balance">{title}</h1>
          {description ? <p className="page-subtitle">{description}</p> : null}
          {actions || aside ? (
            <div className="flex flex-col gap-4 border-t border-slate-200/80 pt-5 lg:flex-row lg:items-center lg:justify-between">
              {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : <div />}
              {aside ? <div className="text-sm font-medium text-soft">{aside}</div> : null}
            </div>
          ) : null}
          {stats.length ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="metric-strip">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{stat.label}</p>
                    <p className="mt-2 text-2xl font-bold text-slate-950">{stat.value}</p>
                    {stat.caption ? <p className="mt-1 text-xs text-soft">{stat.caption}</p> : null}
                  </div>
                  {stat.icon ? <div className="text-slate-400">{stat.icon}</div> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
        {spotlight ? (
          <div className="spotlight-panel fade-in-delayed text-white">
            <div className="relative z-10">
              {spotlight.eyebrow ? <div className="micro-chip border-white/10 bg-white/5 text-white/80">{spotlight.eyebrow}</div> : null}
              <h2 className="mt-4 text-[1.7rem] font-bold tracking-tight">{spotlight.title}</h2>
              {spotlight.description ? <p className="mt-3 text-sm leading-6 text-slate-200">{spotlight.description}</p> : null}
              {spotlight.points?.length ? (
                <div className="mt-5 grid gap-3">
                  {spotlight.points.map((point) => (
                    <div key={point.label} className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">{point.label}</p>
                      <p className="mt-2 text-lg font-semibold text-white">{point.value}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
