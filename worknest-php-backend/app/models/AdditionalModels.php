<?php

namespace App\Models;

use Core\Model;
use Core\DB;

class UserProfile extends Model
{
    protected string $table = 'user_profiles';
    protected string $primaryKey = 'id';
    protected array $fillable = [
        'user_id', 'bio', 'phone', 'company', 'job_title', 'location', 'website', 'timezone', 'locale'
    ];

    public static function findByUserId(int $userId): ?self
    {
        $db = DB::getInstance();
        $data = $db->fetch("SELECT * FROM {$db->fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'user_profiles'")} WHERE user_id = ?", [$userId]);
        return $data ? static::hydrate($data) : null;
    }
}

class UserSetting extends Model
{
    protected string $table = 'user_settings';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'key', 'value'];
}

class PasswordReset extends Model
{
    protected string $table = 'password_resets';
    protected string $primaryKey = 'id';
    protected array $fillable = ['email', 'token', 'expires_at', 'used_at'];

    public static function findByToken(string $token): ?self
    {
        $db = DB::getInstance();
        $data = $db->fetch("SELECT * FROM password_resets WHERE token = ? AND used_at IS NULL AND expires_at > NOW()", [$token]);
        return $data ? static::hydrate($data) : null;
    }
}

class EmailVerification extends Model
{
    protected string $table = 'email_verifications';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'email', 'token', 'expires_at', 'used_at'];
}

class RememberToken extends Model
{
    protected string $table = 'remember_tokens';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'token', 'expires_at'];

    public static function findByToken(string $token): ?self
    {
        $db = DB::getInstance();
        $data = $db->fetch("SELECT * FROM remember_tokens WHERE token = ? AND expires_at > NOW()", [$token]);
        return $data ? static::hydrate($data) : null;
    }
}

class FailedLoginAttempt extends Model
{
    protected string $table = 'failed_login_attempts';
    protected string $primaryKey = 'id';
    protected array $fillable = ['email', 'user_id', 'ip_address'];
}

class UserSession extends Model
{
    protected string $table = 'user_sessions';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'session_id', 'ip_address', 'user_agent', 'last_activity'];
}

class ApiToken extends Model
{
    protected string $table = 'api_tokens';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'token', 'name', 'expires_at', 'last_used_at'];

    public static function findByToken(string $token): ?self
    {
        $db = DB::getInstance();
        $data = $db->fetch("SELECT * FROM api_tokens WHERE token = ? AND expires_at > NOW()", [$token]);
        return $data ? static::hydrate($data) : null;
    }
}