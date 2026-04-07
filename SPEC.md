# Task Management & Team Collaboration Web Application - SPEC.md

## 1. Project Overview

**Project Name:** WorkNest - Task Management & Team Collaboration Platform

**Project Type:** Full-stack Web Application (Django + React)

**Core Functionality:** A modern task management system enabling users to create, manage, and collaborate on tasks within teams. Features include Kanban boards, real-time notifications, team management with role-based permissions, comments, and file attachments.

**Target Users:** Individual professionals, small to medium teams, project managers, and organizations requiring collaborative task management.

---

## 2. Technical Stack

### Frontend
- **Framework:** React.js 18 with Vite
- **Styling:** TailwindCSS 3.x
- **State Management:** Redux Toolkit
- **Routing:** React Router DOM v6
- **HTTP Client:** Axios
- **Notifications:** React Toastify
- **Forms:** React Hook Form + Zod
- **Drag & Drop:** @dnd-kit/core, @dnd-kit/sortable

### Backend
- **Framework:** Django 4.2 with Django REST Framework
- **Authentication:** djangorestframework-simplejwt
- **Real-time:** Django Channels with Redis
- **Task Scheduling:** Celery with Redis broker
- **Database:** PostgreSQL (Supabase)

### Database (Supabase)
- PostgreSQL database
- Supabase Auth (OAuth2)
- Supabase Storage (file attachments)
- Supabase Realtime (live updates)

### DevOps
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Deployment:** Vercel (frontend) + Render (backend)

---

## 3. UI/UX Specification

### Color Palette
```
Primary:        #6366F1 (Indigo-500)
Primary Dark:   #4F46E5 (Indigo-600)
Primary Light:  #818CF8 (Indigo-400)
Secondary:      #10B981 (Emerald-500)
Accent:         #F59E0B (Amber-500)
Background:     #F8FAFC (Slate-50)
Surface:        #FFFFFF
Text Primary:   #1E293B (Slate-800)
Text Secondary: #64748B (Slate-500)
Border:         #E2E8F0 (Slate-200)
Error:          #EF4444 (Red-500)
Warning:        #F59E0B (Amber-500)
Success:        #10B981 (Emerald-500)
```

### Typography
- **Font Family:** Inter (Google Fonts)
- **Headings:** 
  - H1: 32px/40px, font-weight: 700
  - H2: 24px/32px, font-weight: 600
  - H3: 20px/28px, font-weight: 600
  - H4: 16px/24px, font-weight: 600
- **Body:** 14px/20px, font-weight: 400
- **Small:** 12px/16px, font-weight: 400

### Spacing System
- Base unit: 4px
- xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px, 2xl: 48px

### Responsive Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Layout Structure

#### Main Layout
- **Sidebar:** 260px fixed width (collapsible on mobile)
- **Header:** 64px height with user menu, notifications bell
- **Content Area:** Fluid with max-width 1440px, padding 24px

#### Pages
1. **Login/Register:** Centered card layout, 400px max-width
2. **Dashboard:** Grid layout with stat cards, task lists
3. **Team Workspace:** Kanban board with 4 columns
4. **Task Detail:** Two-column (details + comments)

### Components

#### Navigation
- Sidebar with collapsible menu
- Active state: indigo background with white text
- Hover state: slate-100 background

#### Buttons
- Primary: Indigo-500, white text, 8px radius, 40px height
- Secondary: White, indigo border, indigo text
- Danger: Red-500 for destructive actions
- Hover: Darken by 10%

#### Cards
- White background, 12px radius, subtle shadow (0 1px 3px rgba(0,0,0,0.1))
- Hover: Elevated shadow

#### Form Inputs
- 40px height, 8px radius, slate-200 border
- Focus: Indigo-500 ring (2px)
- Error: Red-500 border with error message below

#### Task Cards (Kanban)
- Draggable with smooth transitions
- Color-coded priority indicator (left border 4px)
- Priority colors: Critical (red), High (orange), Medium (yellow), Low (gray)

#### Modals
- Centered overlay with backdrop blur
- Max-width 500px, 16px padding
- Close button in top-right

### Animations
- Page transitions: Fade in (200ms ease)
- Button hover: Scale 1.02 (150ms)
- Card hover: Translate Y -2px (150ms)
- Drag: Opacity 0.8, scale 1.05
- Notifications: Slide in from right (300ms)

---

## 4. Functionality Specification

### 4.1 Authentication

#### Registration
- Fields: name, email, password, confirm password
- Validation: Email format, password min 8 chars
- On success: Auto-login and redirect to dashboard

#### Login
- Fields: email, password
- "Remember me" checkbox (extends token expiry)
- "Forgot password" link
- Social login: Google OAuth button

#### JWT Tokens
- Access token: 15 minutes expiry (stored in memory)
- Refresh token: 7 days (stored in httpOnly cookie)
- Auto-refresh on 401 response

#### Password Reset
- Request reset: Enter email
- Email with reset link (token valid 1 hour)
- New password form

### 4.2 User Profile
- View/edit profile: name, avatar, bio
- Avatar: Upload or select from presets
- Role display (Admin/Manager/Member)

### 4.3 Task Management

#### Create Task
- Required: title, team assignment
- Optional: description, priority, status, due date, assignees, attachments
- Auto-generate unique task ID (e.g., TASK-001)

#### Task Fields
- **Title:** Text, max 200 chars
- **Description:** Rich text (textarea), max 5000 chars
- **Status:** To-Do, In Progress, In Review, Done
- **Priority:** Low, Medium, High, Critical
- **Due Date:** Date picker, future dates
- **Assignees:** Multi-select from team members
- **Attachments:** Files up to 10MB each

#### Task Operations
- Edit: All fields editable by creator, assignee, or team admin
- Delete: Only by creator or team admin
- Mark Complete: Any assignee can change status to Done
- Overdue: Auto-highlight red when past due date and not Done

#### Filtering & Sorting
- Filter by: status, priority, assignee, date range
- Sort by: created date, due date, priority
- Search: Full-text search on title and description

### 4.4 Kanban Board

#### Columns
- To-Do, In Progress, In Review, Done
- Each column shows task count
- Scrollable within column

#### Drag & Drop
- Drag tasks between columns
- Reorder within column
- Optimistic UI update with rollback on failure

### 4.5 Team Management

#### Create Team
- Required: name, description
- Creator becomes Team Admin automatically
- Generate team invite link

#### Team Members
- Invite via email or invite link
- Roles: Admin (full control), Manager (assign tasks), Member (update status)
- Remove members (Admin only)
- Leave team (Members only)

#### Team Dashboard
- Member list with roles
- Team stats: total tasks, completed, pending
- Activity feed

### 4.6 Comments

#### Add Comment
- Text input with @mention support
- Submit on Enter (Shift+Enter for new line)
- Save with author and timestamp

#### Thread Replies
- Reply button on existing comment
- Nested display (max 3 levels)
- Edit/delete own comments

#### Mentions
- Type @ to trigger autocomplete
- Mentioned user receives notification
- Highlight mention in comment

### 4.7 Notifications

#### Types
- Task assigned to you
- Task deadline approaching (24h before)
- New comment on your task
- Mentioned in comment
- Team invitation
- Member added to team

#### Display
- Bell icon in header with unread count badge
- Dropdown list of recent notifications
- Mark as read (click) or mark all read
- Real-time update via WebSocket

#### Email Notifications
- Optional (user preference)
- Send via Celery background task
- Batch notifications (max 1 per hour)

### 4.8 Dashboard

#### Personal Dashboard
- "My Tasks" widget: Tasks assigned to current user
- "Overdue" widget: Past due date tasks highlighted
- "Completed This Week" count
- Quick add task button

#### Team Dashboard
- Task summary: Total, Completed, Pending, Overdue
- Progress bar per team
- Member activity (last 7 days)
- Calendar view of upcoming deadlines

---

## 5. API Endpoints

### Authentication
```
POST   /api/auth/register/
POST   /api/auth/login/
POST   /api/auth/logout/
POST   /api/auth/refresh/
POST   /api/auth/password/reset/
POST   /api/auth/password/reset/confirm/
GET    /api/auth/google/login/
GET    /api/auth/google/callback/
```

### Users
```
GET    /api/users/me/
PUT    /api/users/me/
GET    /api/users/{id}/
```

### Teams
```
GET    /api/teams/
POST   /api/teams/
GET    /api/teams/{id}/
PUT    /api/teams/{id}/
DELETE /api/teams/{id}/
POST   /api/teams/{id}/invite/
GET    /api/teams/{id}/members/
POST   /api/teams/{id}/members/
DELETE /api/teams/{id}/members/{user_id}/
```

### Tasks
```
GET    /api/tasks/
POST   /api/tasks/
GET    /api/tasks/{id}/
PUT    /api/tasks/{id}/
DELETE /api/tasks/{id}/
GET    /api/tasks/kanban/{team_id}/
```

### Comments
```
GET    /api/tasks/{task_id}/comments/
POST   /api/tasks/{task_id}/comments/
PUT    /api/comments/{id}/
DELETE /api/comments/{id}/
```

### Notifications
```
GET    /api/notifications/
PUT    /api/notifications/{id}/read/
POST   /api/notifications/read-all/
```

---

## 6. Database Schema

### Users
```sql
id              UUID PRIMARY KEY
email           VARCHAR(255) UNIQUE
name            VARCHAR(100)
password_hash   VARCHAR(255)
avatar          VARCHAR(500) NULL
bio             TEXT NULL
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

### Teams
```sql
id              UUID PRIMARY KEY
name            VARCHAR(100)
description     TEXT
created_by      UUID FK -> Users
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

### TeamMembers
```sql
id              UUID PRIMARY KEY
team_id         UUID FK -> Teams
user_id         UUID FK -> Users
role            ENUM('admin', 'manager', 'member')
joined_at       TIMESTAMP
UNIQUE(team_id, user_id)
```

### Tasks
```sql
id              UUID PRIMARY KEY
team_id         UUID FK -> Teams
title           VARCHAR(200)
description     TEXT
status          ENUM('todo', 'in_progress', 'in_review', 'done')
priority        ENUM('low', 'medium', 'high', 'critical')
deadline        TIMESTAMP NULL
created_by      UUID FK -> Users
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

### TaskAssignees
```sql
task_id         UUID FK -> Tasks
user_id         UUID FK -> Users
PRIMARY KEY(task_id, user_id)
```

### Comments
```sql
id              UUID PRIMARY KEY
task_id         UUID FK -> Tasks
user_id         UUID FK -> Users
content         TEXT
parent_id       UUID FK -> Comments NULL
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

### Notifications
```sql
id              UUID PRIMARY KEY
user_id         UUID FK -> Users
type            VARCHAR(50)
message         TEXT
is_read         BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP
```

### Attachments
```sql
id              UUID PRIMARY KEY
task_id         UUID FK -> Tasks
file_url        VARCHAR(500)
file_name       VARCHAR(255)
file_size       INTEGER
uploaded_by     UUID FK -> Users
created_at      TIMESTAMP
```

---

## 7. Acceptance Criteria

### Authentication
- [ ] User can register with email/password
- [ ] User can login and receive JWT tokens
- [ ] Protected routes redirect to login
- [ ] Google OAuth login works
- [ ] Password reset flow works

### Tasks
- [ ] User can create tasks with all fields
- [ ] User can edit and delete own tasks
- [ ] Kanban board displays and allows drag-drop
- [ ] Filters work correctly
- [ ] Overdue tasks highlighted in red

### Teams
- [ ] User can create teams
- [ ] User can invite members
- [ ] Role permissions enforced
- [ ] Team dashboard shows stats

### Comments
- [ ] User can add comments to tasks
- [ ] User can reply to comments
- [ ] @mentions trigger notifications
- [ ] User can edit/delete own comments

### Notifications
- [ ] Real-time notifications via WebSocket
- [ ] Notification bell shows unread count
- [ ] User can mark as read
- [ ] Email notifications sent

### Dashboard
- [ ] Personal dashboard shows assigned tasks
- [ ] Team dashboard shows team stats
- [ ] Calendar shows deadlines

### Deployment
- [ ] Docker Compose works for local dev
- [ ] CI pipeline runs tests on push
- [ ] CD deploys to production
- [ ] Live URL accessible

---

## 8. Project Structure

```
worknest/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── apps/
│   │   ├── users/
│   │   ├── tasks/
│   │   ├── teams/
│   │   ├── comments/
│   │   └── notifications/
│   ├── config/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── manage.py
│
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── SPEC.md
└── README.md
```
