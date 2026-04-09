import { Link } from 'react-router-dom'
import AppLogo from './AppLogo'

export default function AuthShell({ title, subtitle, footer, children }) {
  return (
    <div className="app-shell relative flex min-h-dvh items-center justify-center overflow-hidden px-4 py-4 lg:py-6">
      <div className="ambient-orb -left-12 top-24 h-48 w-48 bg-emerald-400/10" />
      <div className="ambient-orb right-0 top-8 h-60 w-60 bg-emerald-300/6" />
      <div className="ambient-orb bottom-8 left-1/3 h-40 w-40 bg-slate-300/8" />

      <div className="relative grid w-full max-w-5xl gap-6 lg:grid-cols-[1.02fr,0.98fr]">
        <div className="hero-panel hidden min-h-[460px] flex-col justify-between lg:flex">
          <div>
            <div className="stat-chip inline-flex items-center gap-2">
              <img src="/logo_hd.png" alt="WorkNest logo" className="h-5 w-5 rounded-md object-cover" />
              WorkNest Studio
            </div>
            <h1 className="mt-4 font-display text-[2.75rem] font-bold leading-tight text-slate-950">
              Calm task execution for focused teams.
            </h1>
            <p className="mt-4 max-w-lg text-sm leading-6 text-soft">
              Plan work, assign owners, and keep deadlines clear in one clean workspace built for daily use.
            </p>
          </div>

          <div className="grid gap-4">
            <div className="spotlight-panel">
              <div className="relative z-10">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">Presentation edge</p>
                <h2 className="mt-3 text-2xl font-bold text-white">Polished enough to present.</h2>
                <p className="mt-3 text-sm leading-6 text-slate-200">
                  Thoughtful hierarchy, premium surfaces, and clear workflow visibility without the noise.
                </p>
              </div>
            </div>

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
          </div>
        </div>

        <div className="page-shell fade-in w-full px-5 py-6 md:px-7 md:py-7">
          <AppLogo
            to="/login"
            imageClassName="h-9 w-9"
            titleClassName="text-sm font-semibold text-slate-800"
          />
          <div className="mt-6">
            <h2 className="font-display text-2xl font-bold text-slate-950 md:text-3xl">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-soft">{subtitle}</p>
          </div>
          <div className="mt-6">{children}</div>
          {footer ? <div className="mt-6 text-sm text-soft">{footer}</div> : null}
        </div>
      </div>
    </div>
  )
}
