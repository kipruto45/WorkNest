<?php

namespace App\Controllers;

use Core\Controller;
use Core\DB;
use Core\Auth;

class ReportController extends Controller
{
    public function taskReport(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teamId = $this->input('team_id');
        $status = $this->input('status');

        $db = DB::getInstance();
        $where = "team_id = ? AND deleted_at IS NULL";
        $params = [$teamId];

        if ($status) {
            $where .= " AND status = ?";
            $params[] = $status;
        }

        $tasks = $db->fetchAll(
            "SELECT * FROM tasks WHERE {$where} ORDER BY created_at DESC",
            $params
        );

        $this->success(['tasks' => $tasks, 'total' => count($tasks)]);
    }

    public function teamActivity(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teamId = $this->input('team_id');

        $db = DB::getInstance();
        $activity = $db->fetchAll(
            "SELECT al.*, u.name as user_name FROM activity_logs al LEFT JOIN users u ON al.user_id = u.id WHERE al.team_id = ? ORDER BY al.created_at DESC LIMIT 50",
            [$teamId]
        );

        $this->success(['activity' => $activity]);
    }

    public function memberWorkload(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teamId = $this->input('team_id');

        $db = DB::getInstance();
        $workload = $db->fetchAll(
            "SELECT u.id, u.name, COUNT(t.id) as task_count, SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as completed_count
             FROM users u
             INNER JOIN memberships m ON u.id = m.user_id
             LEFT JOIN tasks t ON m.user_id = t.created_by AND t.team_id = m.team_id
             WHERE m.team_id = ? AND m.status = 'active'
             GROUP BY u.id, u.name",
            [$teamId]
        );

        $this->success(['workload' => $workload]);
    }

    public function exportReport(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teamId = $this->input('team_id');
        $format = $this->input('format', 'csv');

        $db = DB::getInstance();
        $tasks = $db->fetchAll(
            "SELECT t.*, u.name as creator_name FROM tasks t LEFT JOIN users u ON t.created_by = u.id WHERE t.team_id = ? AND t.deleted_at IS NULL",
            [$teamId]
        );

        if ($format === 'csv') {
            header('Content-Type: text/csv');
            header('Content-Disposition: attachment; filename="tasks.csv"');
            
            echo "ID,Title,Status,Priority,Due Date,Created By\n";
            foreach ($tasks as $task) {
                echo "{$task['id']},\"{$task['title']}\",{$task['status']},{$task['priority']},{$task['due_date']},{$task['creator_name']}\n";
            }
            exit;
        }

        $this->success(['tasks' => $tasks, 'total' => count($tasks)]);
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