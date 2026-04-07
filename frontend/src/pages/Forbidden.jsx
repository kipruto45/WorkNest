import { Link } from 'react-router-dom'

export default function Forbidden() {
  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="hero-panel max-w-2xl text-center fade-in">
        <div className="stat-chip mx-auto">403</div>
        <h1 className="mt-5 font-display text-5xl font-bold text-emerald-950">You do not have access to this area.</h1>
        <p className="mt-4 text-base leading-7 text-soft">
          This page is protected by workspace permissions. Ask a team admin if you believe you should be able to view it.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link to="/" className="btn-primary">
            Go to dashboard
          </Link>
          <Link to="/teams" className="btn-secondary">
            Open teams
          </Link>
        </div>
      </div>
    </div>
  )
}
