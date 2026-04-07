import PublicPageLayout, { InfoCard } from '../components/PublicPageLayout'

const services = [
  { name: 'Application API', status: 'Operational', note: 'Core requests, authentication, and dashboards are responding normally.' },
  { name: 'Notifications', status: 'Operational', note: 'In-app notifications and unread counters are functioning normally.' },
  { name: 'Background jobs', status: 'Operational', note: 'Email delivery and scheduled reminder jobs are processing as expected.' },
]

export default function StatusPage() {
  return (
    <PublicPageLayout
      eyebrow="System Status"
      title="Current platform health at a glance."
      description="This page is where users can confirm whether WorkNest services are operating normally before escalating support issues."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        {services.map((service) => (
          <InfoCard key={service.name} title={service.name} description={service.note}>
            <div className="inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
              {service.status}
            </div>
          </InfoCard>
        ))}
      </div>

      <InfoCard
        title="Need to report an incident?"
        description="If your issue appears isolated to your workspace, include the affected team, task, and time range when you contact support. That helps us triage much faster."
      />
    </PublicPageLayout>
  )
}
