import { Link } from 'react-router-dom'
import AppLogo from './AppLogo'

const primaryLinks = [
  { label: 'About', to: '/about' },
  { label: 'Help Center', to: '/help-center' },
  { label: 'API Docs', to: '/api-docs' },
  { label: 'Status', to: '/status' },
  { label: 'Security', to: '/security' },
  { label: 'Contact', to: '/contact' },
]

const footerGroups = [
  {
    title: 'Product',
    links: [
      { label: 'Landing page', to: '/' },
      { label: 'About', to: '/about' },
      { label: 'Help Center', to: '/help-center' },
      { label: 'API Docs', to: '/api-docs' },
    ],
  },
  {
    title: 'Support',
    links: [
      { label: 'Support', to: '/support' },
      { label: 'Status', to: '/status' },
      { label: 'Security', to: '/security' },
      { label: 'Contact', to: '/contact' },
    ],
  },
]

export default function PublicPageLayout({ eyebrow, title, description, actions, children }) {
  return (
    <div className="min-h-screen bg-[#fafaf8] text-slate-950">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-[rgba(250,250,248,0.92)] backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <AppLogo
            to="/"
            subtitle="Task management for focused teams"
            imageClassName="h-11 w-11"
            titleClassName="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-700"
            subtitleClassName="text-sm text-slate-500"
          />

          <nav className="hidden items-center gap-6 lg:flex">
            {primaryLinks.map((item) => (
              <Link key={item.to} to={item.to} className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-950">
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login" className="hidden text-sm font-semibold text-slate-700 transition-colors hover:text-slate-950 sm:inline-flex">
              Sign In
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition-colors duration-200 hover:bg-emerald-700"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-20 pt-10 sm:px-6 md:pb-24 md:pt-14 lg:px-8">
        <section className="rounded-[34px] border border-slate-200 bg-white px-6 py-10 shadow-[0_16px_48px_rgba(15,23,42,0.06)] md:px-10 md:py-12">
          <div className="max-w-3xl">
            {eyebrow ? <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">{eyebrow}</p> : null}
            <h1 className="mt-4 text-balance font-display text-4xl font-bold tracking-tight text-slate-950 md:text-5xl">{title}</h1>
            {description ? <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600">{description}</p> : null}
            {actions ? <div className="mt-8 flex flex-wrap gap-3">{actions}</div> : null}
          </div>
        </section>

        <div className="mt-10 grid gap-6">{children}</div>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="grid gap-10 lg:grid-cols-[1.15fr,0.85fr]">
            <div>
              <AppLogo
                to="/"
                subtitle="Task management & team collaboration"
                imageClassName="h-11 w-11"
                titleClassName="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-700"
                subtitleClassName="text-sm text-slate-500"
              />
              <p className="mt-5 max-w-md text-sm leading-7 text-slate-600">
                WorkNest gives teams a calmer way to organize work, collaborate in context, and move from planning to delivery with confidence.
              </p>
            </div>

            <div className="grid gap-8 sm:grid-cols-2">
              {footerGroups.map((group) => (
                <div key={group.title}>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-950">{group.title}</h3>
                  <div className="mt-4 space-y-3">
                    {group.links.map((link) => (
                      <Link key={link.to} to={link.to} className="block text-sm text-slate-600 transition-colors hover:text-slate-950">
                        {link.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-10 flex flex-col gap-4 border-t border-slate-200 pt-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>© 2026 WorkNest. All rights reserved.</p>
            <div className="flex items-center gap-4">
              <Link to="/support" className="transition-colors hover:text-slate-950">
                Support
              </Link>
              <a
                href="https://github.com/kipruto45"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 transition-colors hover:text-slate-950"
                aria-label="WorkNest GitHub"
              >
                <GitHubIcon className="h-5 w-5" />
                <span>GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export function InfoCard({ title, description, children }) {
  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_10px_30px_rgba(15,23,42,0.04)] md:p-7">
      <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{title}</h2>
      {description ? <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">{description}</p> : null}
      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  )
}

export function BulletList({ items }) {
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <div key={item} className="flex gap-3 text-sm leading-7 text-slate-600">
          <span className="mt-2 h-2.5 w-2.5 rounded-full bg-emerald-600" />
          <span>{item}</span>
        </div>
      ))}
    </div>
  )
}

function GitHubIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.9.58.1.79-.25.79-.56 0-.28-.01-1.19-.02-2.15-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.69.08-.69 1.16.08 1.76 1.18 1.76 1.18 1.02 1.76 2.68 1.25 3.33.96.1-.74.4-1.25.72-1.54-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.17 1.18a10.98 10.98 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.62 1.58.23 2.75.11 3.04.73.8 1.18 1.83 1.18 3.08 0 4.41-2.7 5.39-5.27 5.67.41.35.78 1.05.78 2.11 0 1.52-.01 2.75-.01 3.13 0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  )
}
