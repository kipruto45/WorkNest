# WorkNest

WorkNest is a full-stack task management and team collaboration platform with a Django backend, React/Vite frontend, realtime notifications, attachments, audit logs, integrations, Celery jobs, and deployment-ready infrastructure.

## Recommended Deployment Setup

Use one GitHub repository for both apps:

- `backend/`
- `frontend/`

You do not need separate repos. The recommended production layout is:

- frontend on Vercel or Netlify
- backend API on Render
- Celery worker on Render
- Celery beat on Render
- PostgreSQL managed database
- Redis managed instance

This keeps the codebase simple while still deploying the frontend and backend as separate services.

## Architecture

- `backend/`: Django REST API, Channels websocket layer, Celery worker/beat, Swagger/OpenAPI, and provider abstractions
- `frontend/`: React + Vite single-page app
- `docker-compose.yml`: local development stack with Postgres, Redis, backend, Celery, and frontend
- `deploy/`: deployment blueprints for Render, Railway, and Fly.io
- `.github/workflows/`: CI and CD automation

## Integration Architecture

WorkNest keeps third-party integrations behind shared services in [backend/apps/integrations](/home/kipruto/Desktop/TASK/backend/apps/integrations):

- `email/`: SMTP and SendGrid providers, Celery-backed delivery, branded HTML and text templates
- `oauth/`: Google OAuth configuration helpers and login URL generation
- `storage/`: local development storage and Supabase Storage adapters
- `supabase/`: low-level Supabase HTTP clients for storage operations and signed URLs

Business modules call these integration services instead of talking to provider SDKs directly. That keeps auth, attachments, notifications, and invitations provider-agnostic and easier to test.

## Core Features

- JWT authentication with refresh-cookie support and Google OAuth helper flow
- Teams, memberships, invitations, tasks, comments, attachments, notifications, dashboards, realtime updates, and audit logs
- Email, OAuth, storage, and Supabase integrations behind shared provider abstractions
- Dockerized local development and production-aware startup scripts
- OpenAPI schema plus Swagger/ReDoc documentation

## Local Development

### Docker Compose

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Local services:

- Backend API: `http://localhost:8000/api/v1/`
- Swagger UI: `http://localhost:8000/api/v1/docs/swagger/`
- ReDoc: `http://localhost:8000/api/v1/docs/redoc/`
- Health: `http://localhost:8000/api/v1/health/`
- Frontend: `http://localhost:5173/`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

### Manual Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

### Manual Frontend Setup

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

## Runtime Scripts

Backend startup scripts live in [backend/scripts/start-web.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-web.sh), [backend/scripts/start-worker.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-worker.sh), [backend/scripts/start-beat.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-beat.sh), [backend/scripts/start-release.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-release.sh), and [backend/scripts/export-openapi.sh](/home/kipruto/Desktop/TASK/backend/scripts/export-openapi.sh).

Supported backend server modes:

- `APP_SERVER=daphne` for websocket-friendly local development
- `APP_SERVER=uvicorn` for lightweight ASGI serving
- `APP_SERVER=gunicorn` for production using `uvicorn.workers.UvicornWorker`

Useful commands:

```bash
cd backend
python manage.py test --settings=config.settings.test
./scripts/start-release.sh
./scripts/export-openapi.sh
```

## Health and API Docs

- `GET /api/v1/health/` overall health summary
- `GET /api/v1/health/live/` liveness probe
- `GET /api/v1/health/ready/` readiness probe
- `GET /api/v1/schema/` OpenAPI schema
- `GET /api/v1/docs/swagger/` Swagger UI
- `GET /api/v1/docs/redoc/` ReDoc

## Docker and Deployment

### Backend

- Multi-stage Docker build in [backend/Dockerfile](/home/kipruto/Desktop/TASK/backend/Dockerfile)
- Migration and collectstatic strategy handled by [backend/scripts/start-release.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-release.sh) and [backend/scripts/start-web.sh](/home/kipruto/Desktop/TASK/backend/scripts/start-web.sh)
- Celery worker and beat run as separate processes/containers

### Frontend

- Multi-stage Docker build in [frontend/Dockerfile](/home/kipruto/Desktop/TASK/frontend/Dockerfile)
- SPA nginx fallback config in [frontend/nginx.conf](/home/kipruto/Desktop/TASK/frontend/nginx.conf)
- Vercel config in [vercel.json](/home/kipruto/Desktop/TASK/vercel.json)
- Netlify config in [netlify.toml](/home/kipruto/Desktop/TASK/netlify.toml)

### Platform Blueprints

- Render: [deploy/render/render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml)
- Render guide: [deploy/render/README.md](/home/kipruto/Desktop/TASK/deploy/render/README.md)
- Railway: [deploy/railway/railway.json](/home/kipruto/Desktop/TASK/deploy/railway/railway.json)
- Fly.io: [deploy/fly/fly.toml](/home/kipruto/Desktop/TASK/deploy/fly/fly.toml)

## Single-Repo GitHub Deployment Flow

### 1. Push this repository to GitHub

Keep the current monorepo structure:

- `backend/`
- `frontend/`
- `deploy/`

Do not split the repo unless you later need separate ownership or release cycles.

### 2. Deploy the backend on Render

Use the Render blueprint in [deploy/render/render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml).

That creates:

- `worknest-backend`
- `worknest-celery-worker`
- `worknest-celery-beat`

### 3. Deploy the frontend from the same repo

You can use either:

- Vercel with [vercel.json](/home/kipruto/Desktop/TASK/vercel.json)
- Netlify with [netlify.toml](/home/kipruto/Desktop/TASK/netlify.toml)

For Vercel:

- import the same GitHub repo
- keep the project pointed at the repo root
- `vercel.json` already installs and builds from `frontend/`

For Netlify:

- import the same GitHub repo
- `netlify.toml` already uses `frontend` as the build base

### 4. Set the production environment variables

Backend:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `BACKEND_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `INVITE_LINK_BASE_URL`
- `PASSWORD_RESET_LINK_BASE_URL`
- email provider settings
- Google OAuth settings
- storage settings

Frontend:

- `VITE_API_URL=https://your-backend-domain/api/v1`
- `VITE_APP_ENV=production`
- `VITE_GOOGLE_CLIENT_ID=your-google-client-id`
- `VITE_GOOGLE_REDIRECT_URI=https://your-frontend-domain/auth/google/callback`

### 5. Point each side at the other

Recommended final URL pattern:

- frontend: `https://app.yourdomain.com`
- backend: `https://api.yourdomain.com`

Then set:

- `FRONTEND_URL=https://app.yourdomain.com`
- `BACKEND_URL=https://api.yourdomain.com`
- `INVITE_LINK_BASE_URL=https://app.yourdomain.com/invitations`
- `PASSWORD_RESET_LINK_BASE_URL=https://app.yourdomain.com/reset-password`
- `VITE_API_URL=https://api.yourdomain.com/api/v1`

### Render Backend Checklist

For Render, the backend is prepared to run as three Docker services:

- `worknest-backend` web service
- `worknest-celery-worker` worker service
- `worknest-celery-beat` beat service

The Render blueprint already sets:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `ENVIRONMENT=production`
- `APP_SERVER=gunicorn`
- `RUN_MIGRATIONS=1`
- `RUN_COLLECTSTATIC=1`
- `ATTACHMENTS_STORAGE_BACKEND=supabase`

You still need to set the secret/platform values in the Render dashboard:

- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `BACKEND_URL`
- `INVITE_LINK_BASE_URL`
- `PASSWORD_RESET_LINK_BASE_URL`
- `DEFAULT_FROM_EMAIL`
- `SUPPORT_EMAIL`
- `SMTP_*` or `SENDGRID_API_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ATTACHMENTS_SUPABASE_BUCKET`
- `LOGO_URL`

Recommended Render health check:

- `/api/v1/health/ready/`

## CI/CD

- CI workflow: [ci.yml](/home/kipruto/Desktop/TASK/.github/workflows/ci.yml)
- CD workflow: [cd.yml](/home/kipruto/Desktop/TASK/.github/workflows/cd.yml)

CI includes:

- backend compile and Django system checks
- backend test suite
- frontend build
- backend and frontend Docker image builds with cache

CD supports:

- Render deploy hook
- Railway deploy hook
- Fly.io deployment
- Vercel deployment
- Netlify deployment

## Environment Variables

Backend variables are documented in [backend/.env.example](/home/kipruto/Desktop/TASK/backend/.env.example). Key groups include:

- Django/runtime: `DJANGO_SETTINGS_MODULE`, `ENVIRONMENT`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- web process: `APP_SERVER`, `PORT`, `WEB_CONCURRENCY`, `GUNICORN_TIMEOUT`, `RUN_MIGRATIONS`, `RUN_COLLECTSTATIC`
- database/cache: `DATABASE_URL`, `POSTGRES_*`, `DB_*`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- email/providers: `EMAIL_PROVIDER`, `DEFAULT_FROM_EMAIL`, `EMAIL_FROM_NAME`, `SMTP_*`, `SENDGRID_API_KEY`
- OAuth/storage: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `ATTACHMENTS_STORAGE_BACKEND`
- app URLs and branding: `FRONTEND_URL`, `BACKEND_URL`, `INVITE_LINK_BASE_URL`, `PASSWORD_RESET_LINK_BASE_URL`, `APP_NAME`, `SUPPORT_EMAIL`, `LOGO_URL`

Frontend variables are documented in [frontend/.env.example](/home/kipruto/Desktop/TASK/frontend/.env.example):

- `VITE_API_URL`
- `VITE_APP_ENV`
- `VITE_GOOGLE_CLIENT_ID`
- `VITE_GOOGLE_REDIRECT_URI`

For GitHub Actions, configure secrets such as:

- `RENDER_DEPLOY_HOOK_URL`
- `RAILWAY_DEPLOY_HOOK_URL`
- `FLY_API_TOKEN`
- `FLY_APP_NAME`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `NETLIFY_AUTH_TOKEN`
- `NETLIFY_SITE_ID`
- `VITE_API_URL`

## Deployment Notes

- Use `config.settings.production` in hosted environments
- Set `APP_SERVER=gunicorn` for production containers
- Keep Redis available for Channels and Celery
- Run migrations and collectstatic during release or container startup
- Point platform health checks to `/api/v1/health/ready/`
- Keep secrets in provider dashboards or GitHub Secrets, never in source control

## Integration Setup Guide

### Google Authentication

- Backend supports both redirect-based Google OAuth and frontend token verification.
- Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` on the backend.
- If your provider dashboard uses the shorter names, `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are accepted aliases.
- Set `GOOGLE_REDIRECT_URI` in production when the backend sits behind a proxy or hosted domain.
- Set `VITE_GOOGLE_CLIENT_ID` on the frontend to enable the Google Identity popup flow.

### Email Providers

- `EMAIL_PROVIDER=smtp` uses Django email delivery with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, and `SMTP_PASSWORD`.
- `EMAIL_PROVIDER=sendgrid` uses `SENDGRID_API_KEY`.
- All transactional emails are queued through Celery and rendered with both HTML and plain-text bodies.

### Storage Providers

- `ATTACHMENTS_STORAGE_BACKEND=local` keeps attachments in Django media storage for local development.
- `ATTACHMENTS_STORAGE_BACKEND=supabase` uses Supabase Storage with `SUPABASE_URL` and either `SUPABASE_KEY` or `SUPABASE_SERVICE_ROLE_KEY`.
- Signed download URLs are generated server-side and team-scoped permissions are enforced before download links are issued.

### Redis, Celery, and Realtime

- `REDIS_URL` is used by Django cache and Channels.
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` point Celery at Redis.
- Start the API with Daphne or another ASGI server for websocket support, plus a separate Celery worker and optional beat scheduler.

### Invite and Reset Links

- `INVITE_LINK_BASE_URL` controls the base frontend route used in invitation emails.
- `PASSWORD_RESET_LINK_BASE_URL` controls the frontend password reset route embedded in reset emails.
- If unset, both default to the `FRONTEND_URL` SPA routes.

## Live URLs

Production URLs are not created in this repository automatically. After first deployment, add your live backend and frontend URLs here for lecturer/demo handoff:

- Backend: `https://your-backend-domain`
- Frontend: `https://your-frontend-domain`
