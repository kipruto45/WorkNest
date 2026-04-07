# Render Deployment Guide

This project is prepared for Render using the blueprint in [render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml).

If you want to deploy only the backend API first, use [render-backend.yaml](/home/kipruto/Desktop/TASK/deploy/render/render-backend.yaml) and follow [BACKEND_ONLY.md](/home/kipruto/Desktop/TASK/deploy/render/BACKEND_ONLY.md).

## Services

Render should create these three backend services:

- `worknest-backend` (`web`)
- `worknest-celery-worker` (`worker`)
- `worknest-celery-beat` (`worker`)

## Blueprint Setup

1. In Render, choose `New +`.
2. Select `Blueprint`.
3. Connect this repository.
4. Point Render to [render.yaml](/home/kipruto/Desktop/TASK/deploy/render/render.yaml).
5. Create the services.

The blueprint already sets these non-secret production values:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `ENVIRONMENT=production`
- `APP_SERVER=gunicorn`
- `RUN_MIGRATIONS=1`
- `RUN_COLLECTSTATIC=1`
- `ATTACHMENTS_STORAGE_BACKEND=supabase`
- `AUTH_COOKIE_SECURE=True`
- `AUTH_COOKIE_SAMESITE=None`

## Required Environment Variables

Add these in the Render dashboard. Any variable marked `all services` should be set on:

- `worknest-backend`
- `worknest-celery-worker`
- `worknest-celery-beat`

### Core Runtime

Set on `all services`:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `FRONTEND_URL`
- `BACKEND_URL`
- `APP_NAME`
- `SUPPORT_EMAIL`

Database note:

- if you use Supabase Postgres from Render, set `DATABASE_URL` to the Supabase
  **pooler** connection string rather than the direct `db.<project>.supabase.co`
  host when possible
- for Supabase SSL, also set:
  - `DATABASE_SSL_REQUIRE=True`
  - `DB_SSL_MODE=require`

Set on `worknest-backend`:

- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `INVITE_LINK_BASE_URL`
- `PASSWORD_RESET_LINK_BASE_URL`

Recommended examples after you know your live domains:

- `ALLOWED_HOSTS=your-backend.onrender.com`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain`
- `CSRF_TRUSTED_ORIGINS=https://your-frontend-domain,https://your-backend.onrender.com`
- `BACKEND_URL=https://your-backend.onrender.com`
- `FRONTEND_URL=https://your-frontend-domain`
- `INVITE_LINK_BASE_URL=https://your-frontend-domain/invitations`
- `PASSWORD_RESET_LINK_BASE_URL=https://your-frontend-domain/reset-password`

## Email Provider

Set on `worknest-backend` and `worknest-celery-worker`.

### If using SMTP

- `EMAIL_PROVIDER=smtp`
- `EMAIL_DELIVERY_MODE=async`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_FROM_NAME`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`

### If using SendGrid

- `EMAIL_PROVIDER=sendgrid`
- `EMAIL_DELIVERY_MODE=async`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_FROM_NAME`
- `SENDGRID_API_KEY`

Do not set both providers unless you know why.

If you deploy only the backend web service and do not run the Celery worker,
set `EMAIL_DELIVERY_MODE=sync` so welcome emails, password resets, invites,
and notification emails are sent directly from the web process.

## Google OAuth

Set on `worknest-backend`:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Production callback format:

- `https://your-backend.onrender.com/api/v1/auth/google/callback/`

Also make sure the same callback URL is added in your Google Cloud OAuth configuration.

## Supabase Storage

Set on `worknest-backend` and `worknest-celery-worker`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ATTACHMENTS_SUPABASE_BUCKET`

Optional:

- `ATTACHMENTS_SIGNED_URL_TTL=300`
- `LOGO_URL=https://your-frontend-domain/logo_hd.png`

## Redis

Render web + workers need Redis for:

- Channels
- Celery broker
- Celery result backend

If you use Render Redis:

- point `REDIS_URL` to the Render Redis internal URL
- set `CELERY_BROKER_URL` to the same Redis instance
- set `CELERY_RESULT_BACKEND` to the same Redis instance

## Health Check

Use this for the web service:

- `/api/v1/health/ready/`

The blueprint already sets that path.

If you use the backend-only blueprint in
[render-backend.yaml](/home/kipruto/Desktop/TASK/deploy/render/render-backend.yaml),
the health check uses:

- `/api/v1/health/live/`

## First Deploy Checklist

After the first deploy:

1. Open `https://your-backend.onrender.com/api/v1/health/ready/`
2. Open `https://your-backend.onrender.com/api/v1/docs/swagger/`
3. Verify static files load correctly.
4. Confirm the Celery worker is running.
5. Confirm the Celery beat process is running.
6. Test login with email/password.
7. Test Google login.
8. Request a password reset email.
9. Send a team invitation email.
10. Upload an attachment and confirm it lands in Supabase Storage.

## Common Failure Points

- using the direct Supabase database host instead of the pooler connection URL
- Wrong `GOOGLE_REDIRECT_URI`
- Missing `ALLOWED_HOSTS`
- Missing `CSRF_TRUSTED_ORIGINS`
- Web service has Redis configured but worker/beat do not
- `SUPABASE_SERVICE_ROLE_KEY` missing on worker while attachment or email jobs need it
- `FRONTEND_URL` / `BACKEND_URL` still pointing to localhost
- SMTP credentials valid locally but blocked by the provider in production

## Frontend

If you deploy the frontend separately, set:

- `VITE_API_URL=https://your-backend.onrender.com/api/v1`
- `VITE_APP_ENV=production`
- `VITE_GOOGLE_CLIENT_ID=your-google-client-id`
- `VITE_GOOGLE_REDIRECT_URI=https://your-frontend-domain/auth/google/callback`
