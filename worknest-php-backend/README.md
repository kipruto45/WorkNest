# WorkNest PHP Backend

A full-featured team collaboration and task management backend built with PHP 8.2+ and MySQL.

## Project Overview

WorkNest PHP Backend is a standalone, production-style backend for team collaboration and task management. It provides RESTful API endpoints for user authentication, team management, task workflows, notifications, and more.

## Requirements

- PHP 8.2 or higher
- MySQL 8.0 or higher
- Composer

## Installation

### 1. Clone and Install

```bash
git clone <repo-url> worknest-php-backend
cd worknest-php-backend
composer install
```

### 2. Create Database

```bash
mysql -u root -p -e "CREATE DATABASE worknest_php CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```
DB_DATABASE=worknest_php
DB_USERNAME=root
DB_PASSWORD=your_password
```

### 4. Run Migrations

```bash
php scripts/migrate.php
```

### 5. Seed Demo Data (Optional)

```bash
php scripts/seed.php
```

### 6. Start Server

```bash
php -S localhost:8000 -t public
```

## Running Commands

| Command | Description |
|---------|-------------|
| `php scripts/migrate.php` | Run database migrations |
| `php scripts/seed.php` | Seed demo data |
| `php scripts/reset-db.php` | Reset database (drops all tables) |
| `php scripts/health-check.php` | Check system health |
| `php -S localhost:8000 -t public` | Start local server |

## Demo Credentials

After running seeders:

| Email | Password | Role |
|-------|----------|------|
| owner@example.com | password123 | owner |
| admin@example.com | password123 | admin |
| member1@example.com | password123 | member |
| member2@example.com | password123 | member |
| member3@example.com | password123 | member |

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password
- `POST /api/auth/change-password` - Change password
- `GET /api/auth/me` - Get current user

### Users
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile
- `POST /api/users/me/avatar` - Upload avatar
- `GET /api/users/me/settings` - Get settings
- `PUT /api/users/me/settings` - Update settings
- `GET /api/users/search` - Search users

### Teams
- `GET /api/teams` - List teams
- `POST /api/teams` - Create team
- `GET /api/teams/{id}` - Get team
- `PUT /api/teams/{id}` - Update team
- `DELETE /api/teams/{id}` - Delete team
- `GET /api/teams/{id}/members` - Get members
- `POST /api/teams/{id}/invitations` - Invite member

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{id}` - Get task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `PUT /api/tasks/{id}/status` - Update status
- `POST /api/tasks/{id}/assignees` - Assign user
- `POST /api/tasks/{id}/subtasks` - Add subtask
- `POST /api/tasks/{id}/time-logs` - Log time

### Comments
- `GET /api/tasks/{id}/comments` - List comments
- `POST /api/tasks/{id}/comments` - Add comment
- `PUT /api/comments/{id}` - Update comment
- `DELETE /api/comments/{id}` - Delete comment

### Attachments
- `GET /api/tasks/{id}/attachments` - List attachments
- `POST /api/tasks/{id}/attachments` - Upload attachment
- `DELETE /api/attachments/{id}` - Delete attachment

### Notifications
- `GET /api/notifications` - List notifications
- `GET /api/notifications/unread-count` - Unread count
- `POST /api/notifications/{id}/read` - Mark as read
- `POST /api/notifications/read-all` - Mark all as read

### Dashboard
- `GET /api/dashboard/overview` - Overview stats
- `GET /api/dashboard/team/{id}` - Team stats

### Reports
- `GET /api/reports/tasks` - Task report
- `GET /api/reports/activity` - Activity report
- `GET /api/reports/productivity` - Productivity report
- `GET /api/reports/export/csv` - Export CSV

### Health
- `GET /api/health` - Health check

## API Response Format

All API responses follow this format:

```json
{
  "status": "success",
  "message": "Operation successful",
  "data": {},
  "errors": {},
  "meta": {}
}
```

## Testing with curl

```bash
# Health check
curl http://localhost:8000/api/health

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@example.com","password":"password123"}'
```

## Storage Folders

The backend creates these directories automatically:

- `storage/uploads/avatars` - User avatars
- `storage/uploads/attachments` - Task attachments
- `storage/uploads/exports` - Export files
- `storage/uploads/temp` - Temporary files
- `storage/logs` - Application logs

## Troubleshooting

### Database Connection Failed
- Check MySQL is running
- Verify credentials in `.env`
- Ensure database exists

### 401 Unauthorized
- Include Authorization header: `Authorization: Bearer <token>`
- Token expires after 24 hours by default

### File Upload Errors
- Check storage folder permissions
- Verify upload size limits in php.ini

### Permission Errors
- Ensure storage folders are writable
- Check PHP has write permissions

## Security Notes

- Passwords are hashed using bcrypt
- API uses Bearer token authentication
- CSRF protection enabled for web routes
- SQL injection prevention via PDO prepared statements
- Rate limiting on authentication endpoints

## Project Structure

```
worknest-php-backend/
├── app/
│   ├── controllers/    - HTTP controllers
│   ├── models/         - Database models
│   ├── services/       - Business logic
│   ├── middlewares/   - Request middleware
│   ├── requests/      - Input validation
│   ├── policies/      - Authorization
│   ├── transformers/  - API response formatting
│   └── viewmodels/    - View data models
├── config/             - Configuration files
├── core/               - Core framework
├── database/
│   ├── schema/         - SQL schema
│   └── seeders/        - Data seeders
├── public/             - Web entry point
├── routes/             - Route definitions
├── scripts/            - CLI scripts
└── storage/            - File storage
```

## License

MIT
