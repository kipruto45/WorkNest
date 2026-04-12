<?php

namespace App\Models;

use Core\Model;
use Core\DB;

class Notification extends Model
{
    protected string $table = 'notifications';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id',
        'type',
        'title',
        'message',
        'data',
        'link',
        'is_read',
        'read_at',
    ];
    protected array $casts = [
        'data' => 'json',
        'is_read' => 'bool',
    ];

    public static function findByUserId(int $userId, ?int $limit = 20): array
    {
        $model = new static();
        $db = $model->getDB();

        $query = "SELECT * FROM {$model->table} WHERE user_id = ? ORDER BY created_at DESC";
        $params = [$userId];

        if ($limit) {
            $query .= " LIMIT ?";
            $params[] = $limit;
        }

        return $db->fetchAll($query, $params);
    }

    public static function findUnreadByUserId(int $userId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC",
            [$userId]
        );
    }

    public static function getUnreadCount(int $userId): int
    {
        $db = DB::getInstance();
        $result = $db->fetch(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
            [$userId]
        );
        return (int) ($result['count'] ?? 0);
    }

    public function markAsRead(): void
    {
        $db = $this->getDB();
        $db->run(
            "UPDATE {$this->table} SET is_read = 1, read_at = NOW() WHERE id = ?",
            [$this->id]
        );
    }

    public static function markAllAsRead(int $userId): void
    {
        $db = DB::getInstance();
        $db->run(
            "UPDATE notifications SET is_read = 1, read_at = NOW() WHERE user_id = ? AND is_read = 0",
            [$userId]
        );
    }

    public function getUser(): ?User
    {
        return User::find($this->user_id);
    }

    public static function createTaskNotification(int $userId, int $taskId, string $title, string $message, int $actorId): self
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO notifications (user_id, type, title, message, data, link, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                'task',
                $title,
                $message,
                json_encode(['task_id' => $taskId, 'actor_id' => $actorId]),
                "/api/tasks/{$taskId}",
            ]
        );

        $id = $db->lastInsertId();
        return static::find($id);
    }

    public static function createTeamNotification(int $userId, int $teamId, string $title, string $message, int $actorId): self
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO notifications (user_id, type, title, message, data, link, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                'team',
                $title,
                $message,
                json_encode(['team_id' => $teamId, 'actor_id' => $actorId]),
                "/api/teams/{$teamId}",
            ]
        );

        $id = $db->lastInsertId();
        return static::find($id);
    }

    public static function createCommentNotification(int $userId, int $commentId, string $title, string $message, int $actorId): self
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO notifications (user_id, type, title, message, data, link, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                'comment',
                $title,
                $message,
                json_encode(['comment_id' => $commentId, 'actor_id' => $actorId]),
                "/api/comments/{$commentId}",
            ]
        );

        $id = $db->lastInsertId();
        return static::find($id);
    }
}

class AuditLog extends Model
{
    protected string $table = 'audit_logs';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id',
        'action',
        'entity_type',
        'entity_id',
        'details',
        'ip_address',
        'user_agent',
    ];
    protected array $casts = [
        'details' => 'json',
    ];

    public static function findByUserId(int $userId, int $limit = 50): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT al.*, u.name as user_name
             FROM {$model->table} al
             LEFT JOIN users u ON al.user_id = u.id
             WHERE al.user_id = ?
             ORDER BY al.created_at DESC
             LIMIT ?",
            [$userId, $limit]
        );
    }

    public static function findByEntity(string $entityType, int $entityId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT al.*, u.name as user_name
             FROM {$model->table} al
             LEFT JOIN users u ON al.user_id = u.id
             WHERE al.entity_type = ? AND al.entity_id = ?
             ORDER BY al.created_at DESC",
            [$entityType, $entityId]
        );
    }

    public static function log(int $userId, string $action, ?string $entityType = null, ?int $entityId = null, array $details = []): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO {$model->table} (user_id, action, entity_type, entity_id, details, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                $action,
                $entityType,
                $entityId,
                json_encode($details),
                $_SERVER['REMOTE_ADDR'] ?? null,
                $_SERVER['HTTP_USER_AGENT'] ?? null,
            ]
        );
    }
}

class ActivityLog extends Model
{
    protected string $table = 'activity_logs';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id',
        'team_id',
        'action',
        'entity_type',
        'entity_id',
        'metadata',
    ];
    protected array $casts = [
        'metadata' => 'json',
    ];

    public static function findByTeamId(int $teamId, int $limit = 50): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT al.*, u.name as user_name
             FROM {$model->table} al
             LEFT JOIN users u ON al.user_id = u.id
             WHERE al.team_id = ?
             ORDER BY al.created_at DESC
             LIMIT ?",
            [$teamId, $limit]
        );
    }

    public static function logActivity(int $userId, int $teamId, string $action, ?string $entityType = null, ?int $entityId = null, array $metadata = []): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO activity_logs (user_id, team_id, action, entity_type, entity_id, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                $teamId,
                $action,
                $entityType,
                $entityId,
                json_encode($metadata),
            ]
        );
    }
}