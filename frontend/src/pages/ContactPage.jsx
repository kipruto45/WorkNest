import PublicPageLayout, { InfoCard } from '../components/PublicPageLayout'

export default function ContactPage() {
  return (
    <PublicPageLayout
      eyebrow="Contact"
      title="Talk to the WorkNest team."
      description="Reach out for product questions, collaboration opportunities, onboarding help, or general platform guidance."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <InfoCard title="General">
          <a href="mailto:kiprutovictor39@gmail.com" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            kiprutovictor39@gmail.com
          </a>
        </InfoCard>
        <InfoCard title="Support">
          <a href="mailto:kiprutovictor39@gmail.com" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            kiprutovictor39@gmail.com
          </a>
        </InfoCard>
        <InfoCard title="GitHub">
          <a href="https://github.com/kipruto45" target="_blank" rel="noreferrer" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            github.com/kipruto45
          </a>
        </InfoCard>
      </div>
    </PublicPageLayout>
  )
}
