<?php

use Core\Router;
use App\Controllers\AuthController;
use App\Controllers\UserController;
use App\Controllers\ProfileController;
use App\Controllers\TeamController;
use App\Controllers\MembershipController;
use App\Controllers\InvitationController;
use App\Controllers\TaskController;
use App\Controllers\SubtaskController;
use App\Controllers\ChecklistController;
use App\Controllers\CommentController;
use App\Controllers\AttachmentController;
use App\Controllers\NotificationController;
use App\Controllers\DashboardController;
use App\Controllers\AuditLogController;
use App\Controllers\ActivityLogController;
use App\Controllers\IntegrationController;
use App\Controllers\ReportController;
use App\Controllers\HealthController;
use App\Controllers\SettingsController;

$router->get('/api/health', [HealthController::class, 'index']);

$router->post('/api/auth/register', [AuthController::class, 'register']);
$router->post('/api/auth/login', [AuthController::class, 'login']);
$router->post('/api/auth/logout', [AuthController::class, 'logout']);
$router->post('/api/auth/forgot-password', [AuthController::class, 'forgotPassword']);
$router->post('/api/auth/reset-password', [AuthController::class, 'resetPassword']);
$router->post('/api/auth/change-password', [AuthController::class, 'changePassword']);
$router->post('/api/auth/verify-email', [AuthController::class, 'verifyEmail']);
$router->get('/api/auth/me', [AuthController::class, 'me']);

$router->get('/api/users/me', [UserController::class, 'me']);
$router->put('/api/users/me', [UserController::class, 'updateProfile']);
$router->post('/api/users/me/avatar', [UserController::class, 'uploadAvatar']);
$router->get('/api/users/me/settings', [UserController::class, 'getSettings']);
$router->put('/api/users/me/settings', [UserController::class, 'updateSettings']);
$router->get('/api/users/search', [UserController::class, 'search']);

$router->get('/api/profile', [ProfileController::class, 'show']);
$router->put('/api/profile', [ProfileController::class, 'update']);

$router->get('/api/teams', [TeamController::class, 'index']);
$router->post('/api/teams', [TeamController::class, 'create']);
$router->get('/api/teams/{id}', [TeamController::class, 'show']);
$router->put('/api/teams/{id}', [TeamController::class, 'update']);
$router->delete('/api/teams/{id}', [TeamController::class, 'delete']);
$router->get('/api/teams/{id}/members', [TeamController::class, 'members']);
$router->put('/api/teams/{id}/members/{membershipId}', [TeamController::class, 'updateMemberRole']);
$router->delete('/api/teams/{id}/members/{membershipId}', [TeamController::class, 'removeMember']);
$router->get('/api/teams/{id}/invitations', [TeamController::class, 'invitations']);
$router->post('/api/teams/{id}/invitations', [TeamController::class, 'createInvitation']);
$router->post('/api/teams/{id}/invitations/{invitationId}/resend', [TeamController::class, 'resendInvitation']);
$router->delete('/api/teams/{id}/invitations/{invitationId}', [TeamController::class, 'revokeInvitation']);

$router->post('/api/invitations/accept', [InvitationController::class, 'accept']);
$router->post('/api/invitations/revoke', [InvitationController::class, 'revoke']);

$router->get('/api/tasks', [TaskController::class, 'index']);
$router->post('/api/tasks', [TaskController::class, 'create']);
$router->get('/api/tasks/{id}', [TaskController::class, 'show']);
$router->put('/api/tasks/{id}', [TaskController::class, 'update']);
$router->delete('/api/tasks/{id}', [TaskController::class, 'delete']);
$router->put('/api/tasks/{id}/status', [TaskController::class, 'updateStatus']);
$router->post('/api/tasks/{id}/assignees', [TaskController::class, 'assign']);
$router->delete('/api/tasks/{id}/assignees/{userId}', [TaskController::class, 'unassign']);
$router->post('/api/tasks/{id}/watchers', [TaskController::class, 'addWatcher']);
$router->delete('/api/tasks/{id}/watchers/{userId}', [TaskController::class, 'removeWatcher']);
$router->post('/api/tasks/{id}/subtasks', [TaskController::class, 'addSubtask']);
$router->put('/api/subtasks/{id}', [TaskController::class, 'updateSubtask']);
$router->delete('/api/subtasks/{id}', [TaskController::class, 'deleteSubtask']);
$router->post('/api/tasks/{id}/checklists', [TaskController::class, 'addChecklist']);
$router->put('/api/checklist-items/{id}', [TaskController::class, 'toggleChecklistItem']);
$router->post('/api/tasks/{id}/time-logs', [TaskController::class, 'addTimeLog']);

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

$router->get('/api/audit-logs', [AuditLogController::class, 'index']);
$router->get('/api/audit-logs/entity', [AuditLogController::class, 'showByEntity']);

$router->get('/api/activity-logs', [ActivityLogController::class, 'index']);

$router->get('/api/integrations', [IntegrationController::class, 'index']);
$router->post('/api/integrations/connect', [IntegrationController::class, 'connect']);
$router->post('/api/integrations/disconnect', [IntegrationController::class, 'disconnect']);

$router->get('/api/reports/tasks', [ReportController::class, 'taskReport']);
$router->get('/api/reports/activity', [ReportController::class, 'teamActivity']);
$router->get('/api/reports/productivity', [ReportController::class, 'memberWorkload']);
$router->get('/api/reports/export/csv', [ReportController::class, 'exportCsv']);
$router->get('/api/reports/export/pdf', [ReportController::class, 'exportPdf']);

$router->get('/api/settings', [SettingsController::class, 'index']);
$router->put('/api/settings', [SettingsController::class, 'update']);