import { Link } from 'react-router-dom'
import PublicPageLayout, { BulletList, InfoCard } from '../components/PublicPageLayout'

export default function HelpCenter() {
  return (
    <PublicPageLayout
      eyebrow="Help Center"
      title="Answers for getting your workspace running smoothly."
      description="Use these starting points to onboard faster, troubleshoot common questions, and understand how the core WorkNest flows are designed."
      actions={
        <>
          <Link to="/support" className="btn-primary">
            Contact support
          </Link>
          <Link to="/api-docs" className="btn-secondary">
            View API docs
          </Link>
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <InfoCard title="Getting started">
          <BulletList
            items={[
              'Create your account and complete your profile.',
              'Create a team or accept an invitation from an admin.',
              'Add tasks, assign ownership, and set due dates early.',
              'Use comments and mentions inside the task instead of external chat where possible.',
            ]}
          />
        </InfoCard>

        <InfoCard title="Most common questions">
          <BulletList
            items={[
              'How do I invite a teammate and assign a role?',
              'How do notifications and mentions work?',
              'How do I reset my password safely?',
              'How do I find overdue or due-soon tasks from the dashboard?',
            ]}
          />
        </InfoCard>
      </div>

      <InfoCard title="Need direct help?" description="If you are blocked on access, invitations, uploads, notifications, or team permissions, our support page lists the quickest ways to reach the team.">
        <Link to="/support" className="btn-secondary">
          Go to support
        </Link>
      </InfoCard>
    </PublicPageLayout>
  )
}
