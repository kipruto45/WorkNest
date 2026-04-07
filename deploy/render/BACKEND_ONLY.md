# Render Backend-Only Deploy

Use this path when you want to deploy only the Django API to Render and keep the frontend deployed somewhere else.

## Blueprint File

Point Render to:

- [render-backend.yaml](/home/kipruto/Desktop/TASK/deploy/render/render-backend.yaml)

This creates only one service:

- `worknest-backend`

## What You Still Get

- Django API
- Swagger docs at `/api/v1/docs/swagger/`
- health checks at `/api/v1/health/ready/`
- database migrations on deploy
- static file collection on deploy
- Google auth callback support
- password reset and invite link generation
- Supabase-backed attachment support

## What You Do Not Get Yet

If you deploy only the backend web service, these background features will not run asynchronously until you add worker services:

- Celery email queue processing
- scheduled deadline reminders
- websocket-backed Redis/Channels scaling

The API still deploys cleanly, but production background processing is better with the full Render blueprint in [render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml).

## Required Render Environment Variables

Set these on `worknest-backend`:

- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `FRONTEND_URL`
- `BACKEND_URL`
- `INVITE_LINK_BASE_URL`
- `PASSWORD_RESET_LINK_BASE_URL`
- `DEFAULT_FROM_EMAIL`
- `SUPPORT_EMAIL`

### If Using SMTP

- `EMAIL_PROVIDER=smtp`
- `EMAIL_FROM_NAME=WorkNest`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

### If Using SendGrid

- `EMAIL_PROVIDER=sendgrid`
- `EMAIL_FROM_NAME=WorkNest`
- `SENDGRID_API_KEY`

### Google OAuth

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Callback format:

- `https://your-backend.onrender.com/api/v1/auth/google/callback/`

### Supabase Storage

- `ATTACHMENTS_STORAGE_BACKEND=supabase`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ATTACHMENTS_SUPABASE_BUCKET`

Optional:

- `ATTACHMENTS_SIGNED_URL_TTL=300`
- `LOGO_URL=https://your-frontend-domain/logo_hd.png`

## Recommended Values

- `BACKEND_URL=https://your-backend.onrender.com`
- `FRONTEND_URL=https://your-frontend-domain`
- `INVITE_LINK_BASE_URL=https://your-frontend-domain/invitations`
- `PASSWORD_RESET_LINK_BASE_URL=https://your-frontend-domain/reset-password`
- `ALLOWED_HOSTS=your-backend.onrender.com`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain`
- `CSRF_TRUSTED_ORIGINS=https://your-backend.onrender.com,https://your-frontend-domain`

## Deploy Steps

1. In Render, click `New +`.
2. Choose `Blueprint`.
3. Connect this repository.
4. Select [render-backend.yaml](/home/kipruto/Desktop/TASK/deploy/render/render-backend.yaml).
5. Fill the required environment variables.
6. Deploy.

## First Checks

After deploy, open:

1. `https://your-backend.onrender.com/`
2. `https://your-backend.onrender.com/api/v1/docs/swagger/`
3. `https://your-backend.onrender.com/api/v1/health/ready/`

Then test:

1. email/password login
2. Google login
3. password reset request
4. invite email generation
5. attachment upload

## Upgrade Path

When you want async jobs and scheduled reminders, switch from the backend-only blueprint to the full multi-service Render setup in [render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml).
