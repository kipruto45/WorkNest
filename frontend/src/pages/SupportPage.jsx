import PublicPageLayout, { BulletList, InfoCard } from '../components/PublicPageLayout'

export default function SupportPage() {
  return (
    <PublicPageLayout
      eyebrow="Support"
      title="Help for access, invitations, notifications, and day-to-day workspace issues."
      description="If something in your workspace is blocked or behaving unexpectedly, start here. Share the team name, affected page, and a short timeline so we can investigate faster."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <InfoCard title="Fastest path">
          <BulletList
            items={[
              'Use the Help Center for common questions and setup guidance.',
              'Use the Status page first if you suspect a broader service issue.',
              'Email support with the affected route, action, and expected result.',
            ]}
          />
        </InfoCard>

        <InfoCard title="Support contact">
          <a href="mailto:supportworknest@gmail.com" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            supportworknest@gmail.com
          </a>
        </InfoCard>
      </div>
    </PublicPageLayout>
  )
}
