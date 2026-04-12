<?php

namespace App\Controllers;

use App\Models\AuditLog;
use Core\Controller;
use Core\DB;
use Core\Auth;

class AuditLogController extends Controller
{
    public function index(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        if (!$this->authorize('view_audit_logs')) {
            $this->forbidden();
            return;
        }

        $db = DB::getInstance();
        $logs = $db->fetchAll(
            "SELECT al.*, u.name as user_name FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id ORDER BY al.created_at DESC LIMIT 50"
        );

        $this->success(['logs' => $logs]);
    }

    public function showByEntity(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $entityType = $this->input('entity_type');
        $entityId = $this->input('entity_id');

        if (!$entityType || !$entityId) {
            $this->error('Entity type and ID required');
            return;
        }

        $logs = AuditLog::findByEntity($entityType, $entityId);
        $this->success(['logs' => $logs]);
    }

    protected function user()
    {
        return Auth::user();
    }

    protected function authenticate(): bool
    {
        return Auth::check();
    }

    protected function authorize(string $permission): bool
    {
        return Auth::can($permission);
    }
}