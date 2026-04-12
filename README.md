# WorkNest

A full-stack task management and team collaboration platform with realtime notifications, attachments, and audit logs.

## Tech Stack

- **Frontend**: React + Vite
- **Backend**: Choose either:
  - **Python**: Django REST API with Channels (websocket), Celery (background jobs)
  - **PHP**: Slim framework REST API
- **Database**: PostgreSQL or MySQL
- **Cache/Queue**: Redis

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
- MySQL: `localhost:3306`
- Redis: `localhost:6379`

## Environment Variables

### PHP Backend
```env
DB_CONNECTION=mysql
DB_HOST=localhost
DB_PORT=3306
DB_DATABASE=worknest
DB_USERNAME=root
DB_PASSWORD=any

DATABASE_URL=mysql://root:@localhost:3306/worknest
```

### Python Backend
```env
DATABASE_URL=postgresql://user:password@localhost:5432/worknest
REDIS_URL=redis://localhost:6379/0
```

## Deployment

- Frontend: Vercel, Netlify, or Docker
- Backend (Python): Render, Railway, Fly.io
- Backend (PHP): Any PHP hosting (Railway, Render, shared hosting)

## PHP Services

PHP backend is located in `worknest-php-backend/`:

- **Database Schema**: `database/schema/schema.sql` (MySQL 8+)
- **Seeders**: `database/seeders/`
- **Routes**: `routes/api.php`
- **Config**: `config/`
- **Storage**: `storage/`

## Live URLs

- **Frontend**: https://work-nest-lemon.vercel.app/
- **Backend (Python)**: https://worknest-backend-t6dw.onrender.com
- **Backend (PHP)**: https://worknest-php.onrender.com
- **Database**: dpg-d7a9punpm1nc73c1jsdg-a
