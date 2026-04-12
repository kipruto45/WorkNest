# WorkNest

A full-stack task management and team collaboration platform with realtime notifications, attachments, and audit logs.

## Tech Stack

- **Frontend**: React + Vite
- **Backend**: Choose either:
  - **Python**: Django REST API with Channels (websocket), Celery (background jobs)
  - **PHP**: Slim framework REST API
- **Database**: PostgreSQL or MySQL
- **Cache/Queue**: Redis

## Folder Structure

```
worknest-php-backend/  # PHP backend (Slim)
backend/               # Python backend (Django)
frontend/              # React + Vite frontend
deploy/                # Deployment blueprints
docker-compose.yml     # Local development stack
```

## Quick Start

### Using Python Backend (Django)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Frontend:
```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

### Using PHP Backend

```bash
cd worknest-php-backend
composer install
cp .env.example .env
php -S localhost:8000 -t public
```

### Docker Compose (Python Backend)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

## Services

- Backend API: `http://localhost:8000/api/v1/` (Python) or `http://localhost:8000/` (PHP)
- Frontend: `http://localhost:5173/`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Deployment

- Frontend: Vercel, Netlify, or Docker
- Backend (Python): Render, Railway, Fly.io
- Backend (PHP): Any PHP hosting (Railway, Render, shared hosting)
