<?php

use Core\Router;
use App\Controllers\AuthController;
use App\Controllers\UserController;
use App\Controllers\TeamController;
use App\Controllers\TaskController;
use App\Controllers\CommentController;
use App\Controllers\AttachmentController;
use App\Controllers\NotificationController;
use App\Controllers\DashboardController;
use App\Controllers\HealthController;

$router->get('/api/health', [HealthController::class, 'index']);
$router->get('/api/auth/me', [AuthController::class, 'me']);
$router->post('/api/auth/register', [AuthController::class, 'register']);
$router->post('/api/auth/login', [AuthController::class, 'login']);
$router->post('/api/auth/logout', [AuthController::class, 'logout']);
$router->post('/api/auth/forgot-password', [AuthController::class, 'forgotPassword']);
$router->post('/api/auth/reset-password', [AuthController::class, 'resetPassword']);
$router->post('/api/auth/change-password', [AuthController::class, 'changePassword']);
$router->post('/api/auth/verify-email', [AuthController::class, 'verifyEmail']);

$router->get('/api/users/me', [UserController::class, 'me']);
$router->put('/api/users/me', [UserController::class, 'updateProfile']);
$router->post('/api/users/me/avatar', [UserController::class, 'uploadAvatar']);
$router->get('/api/users/me/settings', [UserController::class, 'getSettings']);
$router->put('/api/users/me/settings', [UserController::class, 'updateSettings']);
$router->get('/api/users/search', [UserController::class, 'search']);

$router->get('/api/teams', [TeamController::class, 'index']);
$router->post('/api/teams', [TeamController::class, 'create']);
$router->get('/api/teams/{id}', [TeamController::class, 'show']);
$router->put('/api/teams/{id}', [TeamController::class, 'update']);
$router->get('/api/teams/{id}/members', [TeamController::class, 'members']);
$router->put('/api/teams/{id}/members', [TeamController::class, 'updateMemberRole']);
$router->delete('/api/teams/{id}/members', [TeamController::class, 'removeMember']);
$router->get('/api/teams/{id}/invitations', [TeamController::class, 'invitations']);
$router->post('/api/teams/{id}/invitations', [TeamController::class, 'createInvitation']);

$router->get('/api/teams/{id}/tasks', [TaskController::class, 'index']);
$router->post('/api/teams/{id}/tasks', [TaskController::class, 'create']);
$router->get('/api/tasks/{id}', [TaskController::class, 'show']);
$router->put('/api/tasks/{id}', [TaskController::class, 'update']);
$router->delete('/api/tasks/{id}', [TaskController::class, 'delete']);
$router->put('/api/tasks/{id}/status', [TaskController::class, 'updateStatus']);
$router->post('/api/tasks/{id}/assign', [TaskController::class, 'assign']);
$router->delete('/api/tasks/{id}/assign', [TaskController::class, 'unassign']);
$router->post('/api/tasks/{id}/watch', [TaskController::class, 'addWatcher']);
$router->delete('/api/tasks/{id}/watch', [TaskController::class, 'removeWatcher']);
$router->post('/api/tasks/{id}/labels', [TaskController::class, 'addLabel']);
$router->delete('/api/tasks/{id}/labels', [TaskController::class, 'removeLabel']);
$router->post('/api/tasks/{id}/subtasks', [TaskController::class, 'addSubtask']);
$router->put('/api/subtasks/{id}', [TaskController::class, 'updateSubtask']);
$router->delete('/api/subtasks/{id}', [TaskController::class, 'deleteSubtask']);
$router->post('/api/tasks/{id}/time-log', [TaskController::class, 'addTimeLog']);

$router->get('/api/tasks/{id}/comments', [CommentController::class, 'index']);
$router->post('/api/tasks/{id}/comments', [CommentController::class, 'create']);
$router->put('/api/comments/{id}', [CommentController::class, 'update']);
$router->delete('/api/comments/{id}', [CommentController::class, 'delete']);
$router->post('/api/comments/{id}/reactions', [CommentController::class, 'addReaction']);
$router->delete('/api/comments/{id}/reactions', [CommentController::class, 'removeReaction']);

$router->get('/api/tasks/{id}/attachments', [AttachmentController::class, 'index']);
$router->post('/api/tasks/{id}/attachments', [AttachmentController::class, 'upload']);
$router->delete('/api/attachments/{id}', [AttachmentController::class, 'delete']);
$router->get('/api/attachments/{id}/download', [AttachmentController::class, 'download']);

$router->get('/api/notifications', [NotificationController::class, 'index']);
$router->get('/api/notifications/unread-count', [NotificationController::class, 'unreadCount']);
$router->post('/api/notifications/{id}/read', [NotificationController::class, 'markAsRead']);
$router->post('/api/notifications/read-all', [NotificationController::class, 'markAllAsRead']);
$router->get('/api/notifications/preferences', [NotificationController::class, 'getPreferences']);
$router->put('/api/notifications/preferences', [NotificationController::class, 'updatePreferences']);

$router->get('/api/dashboard/overview', [DashboardController::class, 'overview']);
$router->get('/api/dashboard/team/{id}', [DashboardController::class, 'teamOverview']);
$router->get('/api/dashboard/activity', [DashboardController::class, 'activity']);