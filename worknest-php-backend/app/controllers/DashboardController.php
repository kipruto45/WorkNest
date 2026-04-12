<?php

namespace App\Controllers;

use Core\Controller;
use Core\DB;
use Core\Auth;

class DashboardController extends Controller
{
    public function overview(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $userId = $this->user()->id;
        $db = DB::getInstance();

        $taskCount = $db->fetch("SELECT COUNT(*) as count FROM tasks t INNER JOIN memberships m ON t.team_id = m.team_id WHERE m.user_id = ? AND t.deleted_at IS NULL", [$userId]);
        $completedCount = $db->fetch("SELECT COUNT(*) as count FROM tasks t INNER JOIN memberships m ON t.team_id = m.team_id WHERE m.user_id = ? AND t.status = 'done'", [$userId]);
        $overdueCount = $db->fetch("SELECT COUNT(*) as count FROM tasks t INNER JOIN memberships m ON t.team_id = m.team_id WHERE m.user_id = ? AND t.due_date < CURDATE() AND t.status != 'done'", [$userId]);
        $teamCount = $db->fetch("SELECT COUNT(*) as count FROM memberships WHERE user_id = ?", [$userId]);
        $notificationCount = $db->fetch("SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0", [$userId]);

        $this->success([
            'stats' => [
                'total_tasks' => $taskCount['count'] ?? 0,
                'completed_tasks' => $completedCount['count'] ?? 0,
                'overdue_tasks' => $overdueCount['count'] ?? 0,
                'teams' => $teamCount['count'] ?? 0,
                'unread_notifications' => $notificationCount['count'] ?? 0,
            ]
        ]);
    }

    public function teamOverview(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $db = DB::getInstance();

        $stats = [
            'total_tasks' => $db->fetch("SELECT COUNT(*) as count FROM tasks WHERE team_id = ? AND deleted_at IS NULL", [$id])['count'] ?? 0,
            'completed_tasks' => $db->fetch("SELECT COUNT(*) as count FROM tasks WHERE team_id = ? AND status = 'done'", [$id])['count'] ?? 0,
            'members' => $db->fetch("SELECT COUNT(*) as count FROM memberships WHERE team_id = ? AND status = 'active'", [$id])['count'] ?? 0,
        ];

        $this->success(['stats' => $stats]);
    }

    public function activity(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $db = DB::getInstance();
        $activity = $db->fetchAll(
            "SELECT * FROM activity_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
            [$this->user()->id]
        );

        $this->success(['activity' => $activity]);
    }

    protected function user()
    {
        return Auth::user();
    }

    protected function authenticate(): bool
    {
        return Auth::check();
    }
}