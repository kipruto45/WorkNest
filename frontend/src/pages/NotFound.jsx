import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="hero-panel max-w-2xl text-center fade-in">
        <div className="stat-chip mx-auto">404</div>
        <h1 className="mt-5 font-display text-5xl font-bold text-emerald-950">This page drifted out of view.</h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-soft">
          The route you tried to open does not exist or is no longer available in this workspace.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/" className="btn-primary">
            Go to dashboard
          </Link>
          <Link to="/teams" className="btn-secondary">
            Browse teams
          </Link>
        </div>
      </div>
    </div>
  )
}
