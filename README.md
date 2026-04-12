# WorkNest

WorkNest is a full-stack task management and team collaboration platform with a Django backend, React/Vite frontend, realtime notifications, attachments, audit logs, integrations, Celery jobs, and deployment-ready infrastructure.

1. Project Overview
This document provides a comprehensive technical specification and project documentation for the Task Management Web Application. It covers system architecture, feature descriptions, technology stack, flow diagrams, team collaboration guidelines, and deployment strategies.
1.1 Project Summary
Project Title
Task Management Web Application
Objective
Build a web application enabling users to manage tasks and collaborate in teams
Target Users
Students, professionals, and teams requiring structured task and project management
Deployment
Cloud-based, accessible via web browser, CI/CD pipeline
Development Type
Full-Stack Web Application
Link to the project
https://github.com/kipruto45/WorkNest


https://work-nest-lemon.vercel.app




1. Why I Chose This Project
I chose this project because task management and team collaboration are real problems that affect students, small teams, and growing organizations every day. Many people use separate tools for planning tasks, sharing progress, tracking deadlines, and communicating with team members. That creates confusion, duplicated work, and missed deadlines.
The project gave me a chance to build one system that brings these activities together in a single platform. Through WorkNest, a user can manage personal tasks, while teams can create workspaces, assign tasks, track progress, comment on work, and monitor deadlines from one dashboard.
I also chose this project because it allowed me to apply both software engineering and product design thinking. It is not only a coding project; it is a practical system that requires authentication, databases, APIs, dashboards, permissions, notifications, and a user experience that feels modern and professional.
2. How Each Technology Was Used
The project uses a modern full-stack architecture. The table below summarizes the main technologies and how each one supports the system.
Technology
How It Was Used
React / Vite
Used to build the frontend interface, including the landing page, login and registration pages, personal dashboard, team dashboard, task pages, members page, invitations page, and settings pages.
Django
Used as the main backend framework. It handles project structure, business logic, models, administration, and secure server-side processing.
Django REST Framework
Used to expose APIs between the frontend and backend. It powers registration, login, team creation, tasks, invitations, notifications, and other application workflows.
PostgreSQL
Used as the main relational database for storing users, teams, memberships, tasks, deadlines, comments, notifications, and settings in a structured and reliable way.
JWT Authentication
Used to manage secure login sessions between frontend and backend. It allows users to sign in and access protected pages according to their role and workspace.
Redis and Celery
Used for background jobs and asynchronous processing such as notifications, email sending, SMS sending, and other delayed or scheduled tasks.
Docker
Used to make development and deployment more consistent by packaging the application and its services into containers.
Supabase Storage / Cloud Storage
Used for storing uploaded files such as task attachments, profile media, and other user documents in a scalable way.
GitHub
Used for version control, collaboration, and keeping track of changes in the project source code.


3. One Challenge I Faced and How I Solved It
One major challenge in the project was handling role-based access in the team workspace. The system had to support different types of users: an individual user with a personal dashboard, a team admin, a manager, and an invited member. The difficult part was making sure the same application could show the correct dashboard, navigation, and actions for each role without giving the wrong permissions.
For example, an invited team member needed to be able to log in and access the team dashboard, but only as a member—not as an admin. At the same time, the same person might still have a personal dashboard as their default workspace. This created a challenge in routing, permissions, and workspace switching.
I solved this by separating the system into clear workspace contexts: Personal Workspace and Team Workspace. I then designed role-based rules on the backend and matched them with role-aware interface controls on the frontend. This means the backend remains the final authority on permissions, while the frontend only shows the actions the user is allowed to perform. As a result, invited members can join a team successfully, switch to the team dashboard, and work within safe member-level limitations.
4. One Improvement I Would Add in Future
One improvement I would add in future is deeper calendar integration, especially Google Calendar sync. At the moment, the system can support start dates, due dates, reminders, and calendar import and export. However, a full Google Calendar integration would make the product much more useful in real life.
With this improvement, users would be able to connect their Google account, choose a calendar, and automatically sync selected tasks into their personal or team schedule. This would help users manage deadlines outside the application and make WorkNest more practical for daily productivity.
I would also extend this feature carefully with role-based controls for team workspaces, so only authorized team roles can sync team tasks to shared calendars. This would improve planning, deadline visibility, and collaboration while keeping the system secure and organized.

4.4Deployment:
I deployed client and servers side separately using vercel and render respectively.
I then connected them using APIs.

5.4 ScreenShots
5.4.1 Landing page

5.4.2 Login page


5.4.3 Register page







5.4.4 Team Dashboard



5.4.5 Personal Dashboard






5.4.6 Admin dashboard




