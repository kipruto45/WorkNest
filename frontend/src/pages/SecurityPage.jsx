import PublicPageLayout, { BulletList, InfoCard } from '../components/PublicPageLayout'

export default function SecurityPage() {
  return (
    <PublicPageLayout
      eyebrow="Security"
      title="Designed for controlled access, safer collaboration, and secure workflows."
      description="WorkNest uses permission-aware backend rules, invite validation, protected routes, scoped team access, and provider-backed integrations to keep workspace data appropriately contained."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <InfoCard title="Platform controls">
          <BulletList
            items={[
              'Role-based access for admins, managers, and members.',
              'Team-scoped backend permissions to prevent cross-team data exposure.',
              'JWT-based authentication plus secure invitation and password-reset flows.',
              'Protected attachment access and signed URL support where configured.',
            ]}
          />
        </InfoCard>

        <InfoCard title="Operational practices">
          <BulletList
            items={[
              'Secrets are expected through environment variables, not source control.',
              'Critical user and team events are recorded in audit logs.',
              'Integrations are isolated behind service layers for cleaner failure handling.',
              'Health checks and deployment readiness paths support safer operations.',
            ]}
          />
        </InfoCard>
      </div>
    </PublicPageLayout>
  )
}
