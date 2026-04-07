export default function PageHero({ eyebrow, title, description, actions, aside, stats = [], spotlight }) {
  return (
    <section className="hero-panel fade-in">
      <div className="absolute -right-16 top-0 h-40 w-40 rounded-full bg-emerald-300/25 blur-3xl" />
      <div className="absolute bottom-0 left-8 h-24 w-24 rounded-full bg-teal-300/20 blur-2xl" />
      <div className="relative grid gap-6 xl:grid-cols-[1.35fr,0.65fr]">
        <div className="flex flex-col gap-6">
          {eyebrow ? <div className="stat-chip">{eyebrow}</div> : null}
          <h1 className="page-title text-balance">{title}</h1>
          {description ? <p className="page-subtitle">{description}</p> : null}
          {actions || aside ? (
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : <div />}
              {aside ? <div className="text-sm text-soft">{aside}</div> : null}
            </div>
          ) : null}
          {stats.length ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="metric-strip">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">{stat.label}</p>
                    <p className="mt-2 text-2xl font-bold text-emerald-950">{stat.value}</p>
                    {stat.caption ? <p className="mt-1 text-xs text-soft">{stat.caption}</p> : null}
                  </div>
                  {stat.icon ? <div className="text-emerald-600">{stat.icon}</div> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
        {spotlight ? (
          <div className="spotlight-panel fade-in-delayed text-white">
            <div className="relative z-10">
              {spotlight.eyebrow ? <div className="micro-chip border-white/20 bg-white/10 text-emerald-50">{spotlight.eyebrow}</div> : null}
              <h2 className="mt-4 text-2xl font-bold">{spotlight.title}</h2>
              {spotlight.description ? <p className="mt-3 text-sm leading-6 text-emerald-50/90">{spotlight.description}</p> : null}
              {spotlight.points?.length ? (
                <div className="mt-5 grid gap-3">
                  {spotlight.points.map((point) => (
                    <div key={point.label} className="rounded-[22px] border border-white/12 bg-white/10 px-4 py-3 backdrop-blur-md">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-50/70">{point.label}</p>
                      <p className="mt-2 text-lg font-semibold">{point.value}</p>
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
