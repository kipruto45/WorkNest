<?php

use App\Controllers\InvitationController;
use App\Controllers\ReportController;
use App\Controllers\AuditLogController;
use Core\Router;

$router->post('/api/invitations/accept', [InvitationController::class, 'accept']);
$router->post('/api/invitations/revoke', [InvitationController::class, 'revoke']);

$router->get('/api/reports/tasks', [ReportController::class, 'taskReport']);
$router->get('/api/reports/team-activity', [ReportController::class, 'teamActivity']);
$router->get('/api/reports/member-workload', [ReportController::class, 'memberWorkload']);
$router->get('/api/reports/export', [ReportController::class, 'exportReport']);

$router->get('/api/audit-logs', [AuditLogController::class, 'index']);
$router->get('/api/audit-logs/entity', [AuditLogController::class, 'showByEntity']);