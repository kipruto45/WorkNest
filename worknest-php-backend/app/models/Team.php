<?php

namespace App\Models;

use Core\Model;

class Team extends Model
{
    protected string $table = 'teams';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'name',
        'slug',
        'description',
        'logo_url',
        'owner_id',
        'settings',
        'status',
    ];
    protected array $hidden = [];
    protected array $casts = [
        'settings' => 'json',
    ];

    public static function findBySlug(string $slug): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE slug = ? AND deleted_at IS NULL",
            [$slug]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public static function getByUserId(int $userId): array
    {
        $db = DB::getInstance();
        return $db->fetchAll(
            "SELECT t.* FROM teams t
             INNER JOIN memberships m ON t.id = m.team_id
             WHERE m.user_id = ? AND t.status = 'active' AND t.deleted_at IS NULL
             ORDER BY t.name",
            [$userId]
        );
    }

    public static function getByOwnerId(int $ownerId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE owner_id = ? AND deleted_at IS NULL ORDER BY name",
            [$ownerId]
        );
    }

    public function getMembers(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT u.id, u.name, u.email, u.avatar_url, m.role, m.status, m.created_at
             FROM users u
             INNER JOIN memberships m ON u.id = m.user_id
             WHERE m.team_id = ? AND m.status = 'active'
             ORDER BY m.role, u.name",
            [$this->id]
        );
    }

    public function getInvitations(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT * FROM invitations WHERE team_id = ? AND status = 'pending' ORDER BY created_at DESC",
            [$this->id]
        );
    }

    public function getTaskLists(): array
    {
        return TaskList::where(['team_id' => $this->id]);
    }

    public function getTasks(array $filters = []): array
    {
        $db = $this->getDB();
        $where = "team_id = ? AND deleted_at IS NULL";
        $params = [$this->id];

        if (isset($filters['status'])) {
            $where .= " AND status = ?";
            $params[] = $filters['status'];
        }

        if (isset($filters['task_list_id'])) {
            $where .= " AND task_list_id = ?";
            $params[] = $filters['task_list_id'];
        }

        return $db->fetchAll(
            "SELECT * FROM tasks WHERE {$where} ORDER BY position",
            $params
        );
    }

    public function getSetting(string $key, $default = null)
    {
        $db = $this->getDB();
        $result = $db->fetch(
            "SELECT value FROM team_settings WHERE team_id = ? AND `key` = ?",
            [$this->id, $key]
        );

        if (!$result) {
            return $default;
        }

        return $result['value'];
    }

    public function setSetting(string $key, $value): void
    {
        $db = $this->getDB();
        $db->run(
            "INSERT INTO team_settings (team_id, `key`, value, created_at) VALUES (?, ?, ?, NOW())
             ON DUPLICATE KEY UPDATE value = ?, updated_at = NOW()",
            [$this->id, $key, $value, $value]
        );
    }

    public function isOwner(int $userId): bool
    {
        return $this->owner_id === $userId;
    }

    public function hasMember(int $userId): bool
    {
        $db = $this->getDB();
        $result = $db->fetch(
            "SELECT id FROM memberships WHERE user_id = ? AND team_id = ? AND status = 'active'",
            [$userId, $this->id]
        );
        return (bool) $result;
    }

    public function addMember(int $userId, string $role = 'team_member'): self
    {
        $db = $this->getDB();
        $db->run(
            "INSERT INTO memberships (user_id, team_id, role, created_at) VALUES (?, ?, ?, NOW())
             ON DUPLICATE KEY UPDATE role = ?, updated_at = NOW()",
            [$userId, $this->id, $role, $role]
        );
        return $this;
    }

    public function removeMember(int $userId): void
    {
        $db = $this->getDB();
        $db->run(
            "DELETE FROM memberships WHERE user_id = ? AND team_id = ?",
            [$userId, $this->id]
        );
    }

    public function getStats(): array
    {
        $db = $this->getDB();

        $totalTasks = $db->fetch(
            "SELECT COUNT(*) as count FROM tasks WHERE team_id = ? AND deleted_at IS NULL",
            [$this->id]
        );

        $completedTasks = $db->fetch(
            "SELECT COUNT(*) as count FROM tasks WHERE team_id = ? AND status = 'done' AND deleted_at IS NULL",
            [$this->id]
        );

        $totalMembers = $db->fetch(
            "SELECT COUNT(*) as count FROM memberships WHERE team_id = ? AND status = 'active'",
            [$this->id]
        );

        $overdueTasks = $db->fetch(
            "SELECT COUNT(*) as count FROM tasks WHERE team_id = ? AND due_date < CURDATE() AND status != 'done' AND deleted_at IS NULL",
            [$this->id]
        );

        return [
            'total_tasks' => (int) ($totalTasks['count'] ?? 0),
            'completed_tasks' => (int) ($completedTasks['count'] ?? 0),
            'total_members' => (int) ($totalMembers['count'] ?? 0),
            'overdue_tasks' => (int) ($overdueTasks['count'] ?? 0),
        ];
    }
}

class Membership extends Model
{
    protected string $table = 'memberships';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id',
        'team_id',
        'role',
        'status',
    ];

    public static function findByUserAndTeam(int $userId, int $teamId): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE user_id = ? AND team_id = ?",
            [$userId, $teamId]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public function getTeam(): ?Team
    {
        return Team::find($this->team_id);
    }

    public function getUser(): ?User
    {
        return User::find($this->user_id);
    }
}

class Invitation extends Model
{
    protected string $table = 'invitations';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'email',
        'team_id',
        'role',
        'invited_by',
        'status',
        'expires_at',
    ];

    public static function findByEmailAndTeam(string $email, int $teamId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE email = ? AND team_id = ? ORDER BY created_at DESC",
            [$email, $teamId]
        );
    }

    public function getTeam(): ?Team
    {
        return Team::find($this->team_id);
    }

    public function getInviter(): ?User
    {
        return User::find($this->invited_by);
    }

    public function isExpired(): bool
    {
        return strtotime($this->expires_at) < time();
    }

    public function accept(int $userId): void
    {
        $db = $this->getDB();
        $db->run(
            "UPDATE {$this->table} SET status = 'accepted', accepted_at = NOW() WHERE id = ?",
            [$this->id]
        );

        $db->run(
            "INSERT INTO memberships (user_id, team_id, role, created_at) VALUES (?, ?, ?, NOW())",
            [$userId, $this->team_id, $this->role]
        );
    }

    public function revoke(): void
    {
        $db = $this->getDB();
        $db->run(
            "UPDATE {$this->table} SET status = 'revoked', updated_at = NOW() WHERE id = ?",
            [$this->id]
        );
    }
}

class TaskList extends Model
{
    protected string $table = 'task_lists';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'team_id',
        'name',
        'description',
        'position',
        'created_by',
    ];

    public function getTasks(): array
    {
        $db = $this->getDB();
        return $db->fetchAll(
            "SELECT * FROM tasks WHERE task_list_id = ? AND deleted_at IS NULL ORDER BY position",
            [$this->id]
        );
    }
}

class TaskStatus extends Model
{
    protected string $table = 'task_statuses';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'team_id',
        'name',
        'slug',
        'color',
        'position',
        'is_default',
    ];

    public static function getDefaultsForTeam(int $teamId): array
    {
        $model = new static();
        $db = $model->getDB();

        return $db->fetchAll(
            "SELECT * FROM {$model->table} WHERE team_id = ? ORDER BY position",
            [$teamId]
        );
    }
}