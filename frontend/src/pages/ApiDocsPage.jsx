import PublicPageLayout, { BulletList, InfoCard } from '../components/PublicPageLayout'

import { API_BASE_URL } from '../utils/clientConfig.js'

const apiBase = API_BASE_URL
const backendBase = apiBase.replace(/\/api\/v1\/?$/, '')
const swaggerUrl = `${backendBase}/api/v1/docs/swagger/`
const redocUrl = `${backendBase}/api/v1/docs/redoc/`
const schemaUrl = `${backendBase}/api/v1/schema/`

export default function ApiDocsPage() {
  return (
    <PublicPageLayout
      eyebrow="API Docs"
      title="Developer documentation for the WorkNest backend."
      description="Use the live API references to explore authentication, teams, invitations, tasks, comments, notifications, dashboards, attachments, and health endpoints."
      actions={
        <>
          <a href={swaggerUrl} target="_blank" rel="noreferrer" className="btn-primary">
            Open Swagger
          </a>
          <a href={redocUrl} target="_blank" rel="noreferrer" className="btn-secondary">
            Open ReDoc
          </a>
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <InfoCard title="Swagger UI" description="Interactive endpoint exploration with request and response examples.">
          <a href={swaggerUrl} target="_blank" rel="noreferrer" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            {swaggerUrl}
          </a>
        </InfoCard>
        <InfoCard title="ReDoc" description="A cleaner reference view for browsing routes and schemas by resource.">
          <a href={redocUrl} target="_blank" rel="noreferrer" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            {redocUrl}
          </a>
        </InfoCard>
        <InfoCard title="OpenAPI schema" description="Machine-readable schema for integrations, SDK generation, or collection imports.">
          <a href={schemaUrl} target="_blank" rel="noreferrer" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            {schemaUrl}
          </a>
        </InfoCard>
      </div>

      <InfoCard title="What the API covers">
        <BulletList
          items={[
            'JWT auth, Google sign-in, password reset, and current-user session endpoints.',
            'Teams, invitations, memberships, and role-aware access control.',
            'Tasks, board views, comments, mentions, attachments, dashboards, and notifications.',
          ]}
        />
      </InfoCard>
    </PublicPageLayout>
  )
}
