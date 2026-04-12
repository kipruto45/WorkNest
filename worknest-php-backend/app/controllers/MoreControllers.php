<?php

namespace App\Controllers;

use Core\Controller;

class MembershipController extends Controller
{
    public function index(int $teamId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $members = $db->fetchAll("SELECT u.id, u.name, u.email, u.avatar_url, m.role, m.status FROM users u INNER JOIN memberships m ON u.id = m.user_id WHERE m.team_id = ?", [$teamId]);
        $this->success(['members' => $members]);
    }

    public function update(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("UPDATE memberships SET role = ?, updated_at = NOW() WHERE id = ?", [$data['role'] ?? 'team_member', $id]);
        $this->success([], 'Membership updated');
    }

    public function remove(int $teamId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("DELETE FROM memberships WHERE team_id = ? AND user_id = ?", [$teamId, $data['user_id'] ?? 0]);
        $this->success([], 'Member removed');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class SubtaskController extends Controller
{
    public function index(int $taskId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $subtasks = $db->fetchAll("SELECT * FROM subtasks WHERE task_id = ? ORDER BY position", [$taskId]);
        $this->success(['subtasks' => $subtasks]);
    }

    public function create(int $taskId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("INSERT INTO subtasks (task_id, title, created_by, created_at) VALUES (?, ?, ?, NOW())", [$taskId, $data['title'] ?? '', $this->user()->id]);
        $this->success(['id' => $db->lastInsertId()], 'Subtask created');
    }

    public function update(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("UPDATE subtasks SET title = ?, is_completed = ?, updated_at = NOW() WHERE id = ?", [$data['title'] ?? '', $data['is_completed'] ?? 0, $id]);
        $this->success([], 'Subtask updated');
    }

    public function delete(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $db->run("DELETE FROM subtasks WHERE id = ?", [$id]);
        $this->success([], 'Subtask deleted');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class ChecklistController extends Controller
{
    public function index(int $taskId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $checklists = $db->fetchAll("SELECT * FROM task_checklists WHERE task_id = ?", [$taskId]);
        $this->success(['checklists' => $checklists]);
    }

    public function create(int $taskId): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("INSERT INTO task_checklists (task_id, title, created_by, created_at) VALUES (?, ?, ?, NOW())", [$taskId, $data['title'] ?? '', $this->user()->id]);
        $this->success(['id' => $db->lastInsertId()], 'Checklist created');
    }

    public function addItem(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        $db->run("INSERT INTO task_checklist_items (checklist_id, title, created_by, created_at) VALUES (?, ?, ?, NOW())", [$id, $data['title'] ?? '', $this->user()->id]);
        $this->success([], 'Item added');
    }

    public function toggleItem(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $db->run("UPDATE task_checklist_items SET is_completed = IF(is_completed=1,0,1) WHERE id = ?", [$id]);
        $this->success([], 'Item toggled');
    }

    public function delete(int $id): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $db->run("DELETE FROM task_checklists WHERE id = ?", [$id]);
        $this->success([], 'Checklist deleted');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class SettingsController extends Controller
{
    public function index(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $settings = $db->fetchAll("SELECT `key`, value FROM settings");
        $this->success(['settings' => $settings]);
    }

    public function update(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $db = \Core\DB::getInstance();
        foreach ($data as $key => $value) {
            $db->run("INSERT INTO settings (`key`, value, created_at) VALUES (?, ?, NOW()) ON DUPLICATE KEY UPDATE value = ?, updated_at = NOW()", [$key, $value, $value]);
        }
        $this->success([], 'Settings updated');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class ProfileController extends Controller
{
    public function show(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $user = $this->user();
        $db = \Core\DB::getInstance();
        $profile = $db->fetch("SELECT * FROM user_profiles WHERE user_id = ?", [$user->id]);
        $this->success(['profile' => $profile, 'user' => $user->toArray()]);
    }

    public function update(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $userId = $this->user()->id;
        $db = \Core\DB::getInstance();
        
        if (isset($data['name'])) {
            $db->run("UPDATE users SET name = ?, updated_at = NOW() WHERE id = ?", [$data['name'], $userId]);
        }
        
        $db->run("INSERT INTO user_profiles (user_id, bio, phone, company, job_title, location, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW()) ON DUPLICATE KEY UPDATE bio = COALESCE(?, bio), phone = COALESCE(?, phone), company = COALESCE(?, company), job_title = COALESCE(?, job_title), location = COALESCE(?, location), updated_at = NOW()",
            $userId, $data['bio'] ?? '', $data['phone'] ?? '', $data['company'] ?? '', $data['job_title'] ?? '', $data['location'] ?? '', $data['bio'] ?? null, $data['phone'] ?? null, $data['company'] ?? null, $data['job_title'] ?? null, $data['location'] ?? null);
        
        $this->success([], 'Profile updated');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class ActivityLogController extends Controller
{
    public function index(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $teamId = $this->input('team_id');
        $db = \Core\DB::getInstance();
        $logs = $db->fetchAll("SELECT al.*, u.name as user_name FROM activity_logs al LEFT JOIN users u ON al.user_id = u.id WHERE al.team_id = ? ORDER BY al.created_at DESC LIMIT 50", [$teamId]);
        $this->success(['activity' => $logs]);
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}

class IntegrationController extends Controller
{
    public function index(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $db = \Core\DB::getInstance();
        $providers = $db->fetchAll("SELECT * FROM integration_providers WHERE is_enabled = 1");
        $this->success(['providers' => $providers]);
    }

    public function connect(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $this->success([], 'Integration connection initiated');
    }

    public function disconnect(): void
    {
        if (!$this->authenticate()) { $this->unauthorized(); return; }
        $data = $this->all();
        $this->success([], 'Integration disconnected');
    }

    protected function user() { return \Core\Auth::user(); }
    protected function authenticate(): bool { return \Core\Auth::check(); }
}