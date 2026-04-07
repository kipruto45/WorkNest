import { Link } from 'react-router-dom'

export default function ServerError() {
  return (
    <div className="app-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="hero-panel max-w-2xl text-center fade-in">
        <div className="stat-chip mx-auto">500</div>
        <h1 className="mt-5 font-display text-5xl font-bold text-emerald-950">Something broke on the server side.</h1>
        <p className="mt-4 text-base leading-7 text-soft">
          The workspace hit an unexpected issue. Retry the action or return to a stable page while it recovers.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link to="/" className="btn-primary">
            Back to dashboard
          </Link>
          <Link to="/notifications" className="btn-secondary">
            Review updates
          </Link>
        </div>
      </div>
    </div>
  )
}
