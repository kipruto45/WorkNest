# WorkNest PHP Backend

A full-featured team collaboration and task management backend built with PHP 8.2+ and MySQL.

## Features

- User authentication (register, login, logout, password reset)
- Team management with roles and memberships
- Task management with subtasks, labels, and priorities
- Comments with mentions and reactions
- File attachments
- Real-time notifications
- Dashboard and analytics
- Audit logging
- Email notifications (SMTP)
- PDF/CSV export

## Requirements

- PHP 8.2+
- MySQL 8+
- Composer
- PHPMailer (included via Composer)
- Dompdf (included via Composer)

## Installation

1. Clone the repository:
```bash
git clone <repo-url> worknest-php-backend
cd worknest-php-backend
```

2. Install dependencies:
```bash
composer install
```

3. Create the database:
```bash
mysql -u root -p -e "CREATE DATABASE worknest;"
```

4. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Run migrations:
```bash
php scripts/migrate.php
```

6. Seed the database (optional):
```bash
php database/seeders/Seeder.php
```

## Running Locally

### Using PHP built-in server:
```bash
php -S localhost:8000 -t public
```

### Using Apache:
Configure VirtualHost to point to the `public` directory.

## Demo Credentials

After running seeders:
| Email | Password |
|-------|----------|
| owner@worknest.local | password123 |
| admin@worknest.local | password123 |
| bob@worknest.local | password123 |

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password

### Users
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile
- `POST /api/users/me/avatar` - Upload avatar

### Teams
- `GET /api/teams` - List teams
- `POST /api/teams` - Create team
- `GET /api/teams/{id}` - Get team
- `PUT /api/teams/{id}` - Update team
- `GET /api/teams/{id}/members` - Get members
- `POST /api/teams/{id}/invitations` - Invite member

### Tasks
- `GET /api/teams/{id}/tasks` - List tasks
- `POST /api/teams/{id}/tasks` - Create task
- `GET /api/tasks/{id}` - Get task
- `PUT /api/tasks/{id}` - Update task
- `PUT /api/tasks/{id}/status` - Update status

### Health
- `GET /api/health` - Health check

## Project Structure

```
worknest-php-backend/
├── app/
│   ├── controllers/    # HTTP controllers
│   ├── models/        # Database models
│   ├── services/     # Business logic
│   └── ...
├── config/           # Configuration files
├── core/             # Core framework
├── database/
│   ├── schema/       # SQL schema
│   └── seeders/      # Data seeders
├── public/           # Web root
├── routes/           # Route definitions
├── scripts/          # Utility scripts
├── storage/          # Uploads and logs
└── vendor/          # Composer dependencies
```

## License

MIT