<?php

namespace Core;

class Auth
{
    protected static ?int $userId = null;
    protected static ?object $user = null;

    public static function login(int $userId): void
    {
        static::$userId = $userId;
        Session::set('auth_user_id', $userId);
        Session::regenerate();
    }

    public static function logout(): void
    {
        static::$userId = null;
        static::$user = null;
        Session::forget('auth_user_id');
        Session::regenerate();
    }

    public static function check(): bool
    {
        if (static::$userId === null) {
            static::$userId = Session::get('auth_user_id');
        }

        return static::$userId !== null;
    }

    public static function id(): ?int
    {
        if (static::$userId === null) {
            static::$userId = Session::get('auth_user_id');
        }

        return static::$userId;
    }

    public static function user(): ?object
    {
        if (!static::check()) {
            return null;
        }

        if (static::$user === null) {
            $userId = static::id();
            if ($userId) {
                $db = DB::getInstance();
                $data = $db->fetch(
                    "SELECT * FROM users WHERE id = ? AND status = 'active'",
                    [$userId]
                );

                if ($data) {
                    static::$user = (object) $data;
                } else {
                    static::logout();
                }
            }
        }

        return static::$user;
    }

    public static function attempt(array $credentials): bool
    {
        $email = $credentials['email'] ?? '';
        $password = $credentials['password'] ?? '';

        if (empty($email) || empty($password)) {
            return false;
        }

        $db = DB::getInstance();
        $user = $db->fetch(
            "SELECT * FROM users WHERE email = ? AND status = 'active'",
            [$email]
        );

        if (!$user) {
            static::logFailedAttempt($email);
            return false;
        }

        if (!password_verify($password, $user['password_hash'])) {
            static::logFailedAttempt($email, $user['id']);
            return false;
        }

        static::clearFailedAttempts($user['id']);
        static::login($user['id']);

        return true;
    }

    public static function can(?string $permission): bool
    {
        $user = static::user();

        if (!$user) {
            return false;
        }

        if ($user->role === 'owner' || $user->role === 'admin') {
            return true;
        }

        if ($permission === null) {
            return true;
        }

        $config = require __DIR__ . '/../config/permissions.php';
        $permissions = $config['roles'][$user->role] ?? [];

        return in_array($permission, $permissions);
    }

    public static function canTeam(string $permission, int $teamId): bool
    {
        $user = static::user();

        if (!$user) {
            return false;
        }

        if ($user->role === 'owner' || $user->role === 'admin') {
            return true;
        }

        $db = DB::getInstance();
        $membership = $db->fetch(
            "SELECT * FROM memberships WHERE user_id = ? AND team_id = ?",
            [$user->id, $teamId]
        );

        if (!$membership) {
            return false;
        }

        $config = require __DIR__ . '/../config/permissions.php';
        $permissions = $config['team_roles'][$membership['role']] ?? [];

        return in_array($permission, $permissions);
    }

    public static function isTeamOwner(int $teamId): bool
    {
        $user = static::user();
        if (!$user) {
            return false;
        }

        $db = DB::getInstance();
        $membership = $db->fetch(
            "SELECT role FROM memberships WHERE user_id = ? AND team_id = ?",
            [$user->id, $teamId]
        );

        return $membership && $membership['role'] === 'team_owner';
    }

    public static function isTeamMember(int $teamId): bool
    {
        $user = static::user();
        if (!$user) {
            return false;
        }

        $db = DB::getInstance();
        return (bool) $db->fetch(
            "SELECT id FROM memberships WHERE user_id = ? AND team_id = ?",
            [$user->id, $teamId]
        );
    }

    public static function owns(int $resourceUserId): bool
    {
        $user = static::user();
        return $user && $user->id === $resourceUserId;
    }

    protected static function logFailedAttempt(string $email, ?int $userId = null): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO failed_login_attempts (email, user_id, ip_address, created_at) VALUES (?, ?, ?, NOW())",
            [$email, $userId, Request::capture()->ip()]
        );
    }

    protected static function clearFailedAttempts(int $userId): void
    {
        $db = DB::getInstance();
        $db->run(
            "DELETE FROM failed_login_attempts WHERE user_id = ?",
            [$userId]
        );
    }
}

class Request
{
    public static function capture(): self
    {
        return new self();
    }

    public function ip(): string
    {
        return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }
}