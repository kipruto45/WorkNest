<?php

namespace App\Models;

use Core\Model;
use Core\DB;

class Task extends Model
{
    protected string $table = 'tasks';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'team_id',
        'task_list_id',
        'status_id',
        'title',
        'description',
        'priority',
        'position',
        'due_date',
        'due_time',
        'estimated_hours',
        'actual_hours',
        'created_by',
        'status',
    ];
    protected array $hidden = [];
    protected array $casts = [
        'due_date' => 'date',
        'due_time' => 'time',
    ];

    public static function findById(int $id): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE id = ? AND deleted_at IS NULL",
            [$id]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public function getAssignees(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT u.id, u.name, u.email, u.avatar_url
             FROM users u
             INNER JOIN task_assignees ta ON u.id = ta.user_id
             WHERE ta.task_id = ?",
            [$this->id]
        );
    }

    public function getWatchers(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT u.id, u.name, u.email, u.avatar_url
             FROM users u
             INNER JOIN task_watchers tw ON u.id = tw.user_id
             WHERE tw.task_id = ?",
            [$this->id]
        );
    }

    public function getLabels(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT tl.*
             FROM task_labels tl
             INNER JOIN task_label_links tll ON tl.id = tll.label_id
             WHERE tll.task_id = ?",
            [$this->id]
        );
    }

    public function getSubtasks(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY is_completed, position",
            [$this->id]
        );
    }

    public function getComments(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT c.*, u.name as user_name, u.avatar_url
             FROM comments c
             INNER JOIN users u ON c.user_id = u.id
             WHERE c.task_id = ? AND c.deleted_at IS NULL
             ORDER BY c.created_at DESC",
            [$this->id]
        );
    }

    public function getAttachments(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT * FROM attachments WHERE task_id = ? AND is_deleted = 0 ORDER BY created_at DESC",
            [$this->id]
        );
    }

    public function getChecklists(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT * FROM task_checklists WHERE task_id = ? ORDER BY position",
            [$this->id]
        );
    }

    public function getTimeLogs(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT tl.*, u.name as user_name
             FROM task_time_logs tl
             INNER JOIN users u ON tl.user_id = u.id
             WHERE tl.task_id = ?
             ORDER BY tl.logged_at DESC",
            [$this->id]
        );
    }

    public function assignTo(int $userId, int $assignedBy): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT INTO task_assignees (task_id, user_id, assigned_by, created_at) VALUES (?, ?, ?, NOW())
             ON DUPLICATE KEY UPDATE assigned_by = ?, updated_at = NOW()",
            [$this->id, $userId, $assignedBy, $assignedBy]
        );
    }

    public function unassign(int $userId): void
    {
        $db = $this->getDB();
        $db->run(
            "DELETE FROM task_assignees WHERE task_id = ? AND user_id = ?",
            [$this->id, $userId]
        );
    }

    public function addWatcher(int $userId): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT IGNORE INTO task_watchers (task_id, user_id, created_at) VALUES (?, ?, NOW())",
            [$this->id, $userId]
        );
    }

    public function removeWatcher(int $userId): void
    {
        $db = $this->getDB();
        $db->run(
            "DELETE FROM task_watchers WHERE task_id = ? AND user_id = ?",
            [$this->id, $userId]
        );
    }

    public function addLabel(int $labelId): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT IGNORE INTO task_label_links (task_id, label_id, created_at) VALUES (?, ?, NOW())",
            [$this->id, $labelId]
        );
    }

    public function removeLabel(int $labelId): void
    {
        $db = $this->getDB();
        $db->run(
            "DELETE FROM task_label_links WHERE task_id = ? AND label_id = ?",
            [$this->id, $labelId]
        );
    }

    public function updateStatus(string $status): void
    {
        $completedAt = $status === 'done' ? date('Y-m-d H:i:s') : null;
        $db = $this->getDB();
        $db->run(
            "UPDATE {$this->table} SET status = ?, completed_at = ? WHERE id = ?",
            [$status, $completedAt, $this->id]
        );
    }

    public function addTimeLog(int $userId, float $hours, ?string $description = null): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT INTO task_time_logs (task_id, user_id, hours, description, logged_at, created_at) VALUES (?, ?, ?, ?, NOW(), NOW())",
            [$this->id, $userId, $hours, $description]
        );

        $this->actual_hours = ($this->actual_hours ?? 0) + $hours;
        $this->save();
    }

    public function isOverdue(): bool
    {
        if (!$this->due_date) {
            return false;
        }
        return strtotime($this->due_date) < time() && $this->status !== 'done';
    }

    public function isDueSoon(): bool
    {
        if (!$this->due_date) {
            return false;
        }
        $dueTimestamp = strtotime($this->due_date);
        $now = time();
        return $dueTimestamp >= $now && $dueTimestamp <= strtotime('+3 days');
    }
}

class Subtask extends Model
{
    protected string $table = 'subtasks';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'task_id',
        'title',
        'is_completed',
        'position',
        'created_by',
    ];

    public static function findByTaskId(int $taskId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE task_id = ? ORDER BY is_completed, position",
            [$taskId]
        );
    }

    public function toggle(): void
    {
        $this->is_completed = $this->is_completed ? 0 : 1;
        $this->save();
    }
}

class TaskAssignee extends Model
{
    protected string $table = 'task_assignees';
    protected string $primaryKey = 'id';
}

class TaskWatcher extends Model
{
    protected string $table = 'task_watchers';
    protected string $primaryKey = 'id';
}

class TaskLabel extends Model
{
    protected string $table = 'task_labels';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'team_id',
        'name',
        'color',
        'created_by',
    ];
}

class Comment extends Model
{
    protected string $table = 'comments';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'task_id',
        'user_id',
        'parent_id',
        'content',
        'is_edited',
    ];

    public static function findByTaskId(int $taskId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT c.*, u.name as user_name, u.avatar_url
             FROM {$model->table} c
             INNER JOIN users u ON c.user_id = u.id
             WHERE c.task_id = ? AND c.deleted_at IS NULL
             ORDER BY c.created_at DESC",
            [$taskId]
        );
    }

    public function getReactions(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT emoji, COUNT(*) as count, GROUP_CONCAT(u.name) as users
             FROM comment_reactions cr
             INNER JOIN users u ON cr.user_id = u.id
             WHERE cr.comment_id = ?
             GROUP BY emoji",
            [$this->id]
        );
    }

    public function addReaction(int $userId, string $emoji): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT INTO comment_reactions (comment_id, user_id, emoji, created_at) VALUES (?, ?, ?, NOW())
             ON DUPLICATE KEY UPDATE emoji = emoji",
            [$this->id, $userId, $emoji]
        );
    }

    public function removeReaction(int $userId, string $emoji): void
    {
        $db = $this->getDB();
        $db->run(
            "DELETE FROM comment_reactions WHERE comment_id = ? AND user_id = ? AND emoji = ?",
            [$this->id, $userId, $emoji]
        );
    }
}

class Attachment extends Model
{
    protected string $table = 'attachments';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'team_id',
        'task_id',
        'comment_id',
        'user_id',
        'filename',
        'original_name',
        'mime_type',
        'size',
        'path',
        'url',
        'version',
    ];
    protected array $casts = [
        'size' => 'int',
    ];

    public static function findByTaskId(int $taskId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT a.*, u.name as user_name, u.avatar_url
             FROM {$model->table} a
             INNER JOIN users u ON a.user_id = u.id
             WHERE a.task_id = ? AND a.is_deleted = 0
             ORDER BY a.created_at DESC",
            [$taskId]
        );
    }

    public function softDelete(): void
    {
        $db = $this->getDB();
        $db->run(
            "UPDATE {$this->table} SET is_deleted = 1, deleted_at = NOW() WHERE id = ?",
            [$this->id]
        );
    }
}