import AppLogo from './AppLogo'

export default function AuthShell({
  title,
  subtitle,
  footer,
  children,
  compact = false,
  heroLabel = 'WorkNest Studio',
  heroHeadline = 'Calm task execution for focused teams.',
  heroDescription = 'Plan work, assign owners, and keep deadlines clear in one clean workspace built for daily use.',
  heroImageSrc = '',
  heroImageAlt = '',
  heroVisual = null,
  heroBottom = null,
  mobileHero = null,
  shellClassName = '',
  heroPanelClassName = '',
  cardClassName = '',
  logoTitle = 'WorkNest',
  logoSubtitle = '',
}) {
  return (
    <div className={`app-shell auth-shell relative flex min-h-dvh items-center justify-center overflow-hidden px-4 ${compact ? 'py-2 lg:py-3' : 'py-4 lg:py-6'} ${shellClassName}`}>
      <div className="auth-shell-glow auth-shell-glow-left" />
      <div className="auth-shell-glow auth-shell-glow-right" />
      <div className="auth-shell-grid" />

      <div className={`relative grid w-full ${compact ? 'max-w-6xl gap-4 lg:grid-cols-[0.96fr,1.04fr]' : 'max-w-5xl gap-6 lg:grid-cols-[1.02fr,0.98fr]'}`}>
        {mobileHero ? <div className="mb-4 lg:hidden">{mobileHero}</div> : null}

        <div className={`hero-panel auth-hero-panel hidden flex-col lg:flex ${compact ? 'min-h-[420px] gap-4' : 'min-h-[460px] justify-between'} ${heroPanelClassName}`}>
          <div>
            <div className="stat-chip inline-flex items-center gap-2">
              <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
              {heroLabel}
            </div>
            <h1 className="mt-4 font-display text-[2.75rem] font-bold leading-tight text-slate-950">
              {heroHeadline}
            </h1>
            <p className="mt-4 max-w-lg text-sm leading-6 text-soft">
              {heroDescription}
            </p>
          </div>

          {heroVisual ? (
            heroVisual
          ) : heroImageSrc ? (
            <div className="overflow-hidden rounded-[24px] border-2 border-emerald-300 bg-white p-2 shadow-[0_18px_42px_rgba(16,185,129,0.12)]">
              <img
                src={heroImageSrc}
                alt={heroImageAlt || 'Register preview'}
                className="h-[176px] w-full rounded-[18px] object-cover"
              />
            </div>
          ) : null}

          {heroBottom || (
            <div className="glass-panel p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Workflow</p>
              <div className="mt-3 grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-sm font-semibold text-slate-950">Capture</p>
                  <p className="mt-2 text-sm text-soft">Create tasks, assign owners, and set deadlines fast.</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-950">Collaborate</p>
                  <p className="mt-2 text-sm text-soft">Comments, mentions, notifications, and team context stay connected.</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-950">Deliver</p>
                  <p className="mt-2 text-sm text-soft">Boards, calendars, and analytics keep momentum visible.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className={`page-shell fade-in w-full ${compact ? 'px-4 py-4 md:px-5 md:py-5' : 'px-5 py-6 md:px-7 md:py-7'} ${cardClassName}`}>
          <AppLogo
            to="/login"
            title={logoTitle}
            subtitle={logoSubtitle}
            imageClassName="h-9 w-9"
            titleClassName="text-sm font-semibold text-slate-800"
            subtitleClassName="text-xs text-slate-500"
          />
          <div className={compact ? 'mt-3' : 'mt-6'}>
            <h2 className="font-display text-2xl font-bold text-slate-950 md:text-3xl">{title}</h2>
            <p className={`text-soft ${compact ? 'mt-1.5 text-sm leading-5' : 'mt-2 text-sm leading-6'}`}>{subtitle}</p>
          </div>
          <div className={compact ? 'mt-3' : 'mt-6'}>{children}</div>
          {footer ? <div className={`${compact ? 'mt-3' : 'mt-6'} text-sm text-soft`}>{footer}</div> : null}
        </div>
      </div>
    </div>
  )
}
