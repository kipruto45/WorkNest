import { Link } from 'react-router-dom'
import PublicPageLayout, { BulletList, InfoCard } from '../components/PublicPageLayout'

export default function About() {
  return (
    <PublicPageLayout
      eyebrow="About WorkNest"
      title="A calmer workspace for teams that want clarity over noise."
      description="WorkNest is built for teams that need structure, accountability, and better visibility across tasks, deadlines, invites, and collaboration."
      actions={
        <>
          <Link to="/register" className="btn-primary">
            Start your workspace
          </Link>
          <Link to="/help-center" className="btn-secondary">
            Explore help center
          </Link>
        </>
      }
    >
      <InfoCard
        title="Why WorkNest exists"
        description="Many teams outgrow chat threads and scattered task trackers long before they find a workspace that actually feels coherent. WorkNest brings tasks, collaboration, notifications, dashboards, and member management into one product flow."
      >
        <BulletList
          items={[
            'Organize work by team, role, status, deadline, and ownership.',
            'Keep comments, mentions, files, and updates attached to the work itself.',
            'Give managers and admins strong controls without making the product heavy.',
          ]}
        />
      </InfoCard>

      <div className="grid gap-6 lg:grid-cols-3">
        <InfoCard title="Focused execution" description="Clear boards, deadlines, and ownership keep teams moving without duplicate follow-up." />
        <InfoCard title="Collaboration in context" description="Updates, mentions, and notifications stay tied to the exact task or team activity they belong to." />
        <InfoCard title="Operational visibility" description="Personal and team dashboards make progress, workload, and deadlines easy to understand at a glance." />
      </div>
    </PublicPageLayout>
  )
}
