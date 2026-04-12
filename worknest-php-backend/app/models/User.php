<?php

namespace App\Models;

use Core\Model;

class User extends Model
{
    protected string $table = 'users';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'email',
        'password_hash',
        'name',
        'role',
        'status',
        'avatar_url',
        'email_verified_at',
    ];
    protected array $hidden = ['password_hash', 'remember_token'];
    protected array $casts = [
        'id' => 'int',
        'email_verified_at' => 'datetime',
    ];

    public static function findByEmail(string $email): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE email = ?",
            [$email]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public static function findByRememberToken(string $token): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE remember_token = ? AND status = 'active'",
            [hash('sha256', $token)]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }

    public function setPasswordAttribute(string $password): void
    {
        $this->password_hash = password_hash($password, PASSWORD_BCRYPT);
    }

    public function verifyPassword(string $password): bool
    {
        return password_verify($password, $this->password_hash);
    }

    public function getProfile(): ?UserProfile
    {
        return UserProfile::findByUserId($this->id);
    }

    public function getTeams(): array
    {
        return Team::getByUserId($this->id);
    }

    public function isVerified(): bool
    {
        return $this->email_verified_at !== null;
    }

    public function markAsVerified(): void
    {
        $this->email_verified_at = date('Y-m-d H:i:s');
        $this->save();
    }

    public function getSetting(string $key, $default = null)
    {
        $db = $this->getDB();
        $result = $db->fetch(
            "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
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
            "INSERT INTO user_settings (user_id, key, value, created_at) VALUES (?, ?, ?, NOW())
             ON DUPLICATE KEY UPDATE value = ?, updated_at = NOW()",
            [$this->id, $key, $value, $value]
        );
    }

    public function getNotifications($unreadOnly = false): array
    {
        $db = $this->getDB();
        $where = "user_id = ?";
        $params = [$this->id];

        if ($unreadOnly) {
            $where .= " AND is_read = 0";
        }

        return $db->fetchAll(
            "SELECT * FROM notifications WHERE {$where} ORDER BY created_at DESC",
            $params
        );
    }

    public function getNotificationCount(): int
    {
        $db = $this->getDB();
        $result = $db->fetch(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
            [$this->id]
        );

        return (int) ($result['count'] ?? 0);
    }
}

class UserProfile extends Model
{
    protected string $table = 'user_profiles';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id',
        'bio',
        'phone',
        'company',
        'job_title',
        'location',
        'website',
        'timezone',
        'locale',
    ];

    public static function findByUserId(int $userId): ?self
    {
        $model = new static();
        $db = $model->getDB();

        $data = $db->fetch(
            "SELECT * FROM {$model->table} WHERE user_id = ?",
            [$userId]
        );

        if (!$data) {
            return null;
        }

        return static::hydrate($data);
    }
}