<?php

namespace App\Services;

use App\Models\User;
use Core\DB;
use Core\Token;
use Core\Logger;
use Core\Session;
use Core\Auth;

class AuthService
{
    public function register(array $data): User
    {
        $db = DB::getInstance();

        $existing = $db->fetch(
            "SELECT id FROM users WHERE email = ?",
            [$data['email']]
        );

        if ($existing) {
            throw new \RuntimeException('Email already registered');
        }

        $userData = [
            'email' => $data['email'],
            'password_hash' => password_hash($data['password'], PASSWORD_BCRYPT),
            'name' => $data['name'],
            'role' => 'member',
            'status' => 'active',
            'created_at' => date('Y-m-d H:i:s'),
        ];

        $columns = implode(', ', array_keys($userData));
        $placeholders = implode(', ', array_fill(0, count($userData), '?'));

        $db->run(
            "INSERT INTO users ({$columns}) VALUES ({$placeholders})",
            array_values($userData)
        );

        $userId = $db->lastInsertId();

        Logger::logAudit($userId, 'user.registered', [
            'email' => $data['email'],
        ]);

        return User::find($userId);
    }

    public function login(array $credentials): ?User
    {
        $email = $credentials['email'];
        $password = $credentials['password'];
        $rememberMe = $credentials['remember'] ?? false;

        $user = User::findByEmail($email);

        if (!$user) {
            $this->logFailedAttempt($email);
            return null;
        }

        if ($user->status !== 'active') {
            throw new \RuntimeException('Account is not active');
        }

        if (!password_verify($password, $user->password_hash)) {
            $this->logFailedAttempt($email, $user->id);
            $user = null;
            return null;
        }

        $this->clearFailedAttempts($user->id);
        Auth::login($user->id);

        if ($rememberMe) {
            $this->createRememberToken($user->id);
        }

        Logger::logAudit($user->id, 'user.login');

        return $user;
    }

    public function logout(int $userId): void
    {
        Auth::logout();
        Logger::logAudit($userId, 'user.logout');
    }

    public function forgotPassword(string $email): bool
    {
        $user = User::findByEmail($email);

        if (!$user) {
            return false;
        }

        $token = Token::generateEmailToken();
        $hashed = Token::hash($token);
        $expiresAt = date('Y-m-d H:i:s', time() + 3600);

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO password_resets (email, token, expires_at, created_at) VALUES (?, ?, ?, NOW())",
            [$email, $hashed, $expiresAt]
        );

        Logger::logAudit($user->id, 'user.password_reset_requested');

        return true;
    }

    public function resetPassword(string $token, string $password): bool
    {
        $hashed = Token::hash($token);

        $db = DB::getInstance();
        $reset = $db->fetch(
            "SELECT * FROM password_resets WHERE token = ? AND used_at IS NULL AND expires_at > NOW()",
            [$hashed]
        );

        if (!$reset) {
            return false;
        }

        $user = User::findByEmail($reset['email']);
        if (!$user) {
            return false;
        }

        $user->password_hash = password_hash($password, PASSWORD_BCRYPT);
        $user->save();

        $db->run(
            "UPDATE password_resets SET used_at = NOW() WHERE id = ?",
            [$reset['id']]
        );

        $this->revokeAllTokens($user->id);

        Logger::logAudit($user->id, 'user.password_reset');

        return true;
    }

    public function verifyEmail(int $userId, string $token): bool
    {
        $hashed = Token::hash($token);

        $db = DB::getInstance();
        $verification = $db->fetch(
            "SELECT * FROM email_verifications WHERE user_id = ? AND token = ? AND used_at IS NULL AND expires_at > NOW()",
            [$userId, $hashed]
        );

        if (!$verification) {
            return false;
        }

        $user = User::find($userId);
        if (!$user) {
            return false;
        }

        $user->email_verified_at = date('Y-m-d H:i:s');
        $user->save();

        $db->run(
            "UPDATE email_verifications SET used_at = NOW() WHERE id = ?",
            [$verification['id']]
        );

        Logger::logAudit($userId, 'user.email_verified');

        return true;
    }

    public function changePassword(int $userId, string $currentPassword, string $newPassword): bool
    {
        $user = User::find($userId);

        if (!$user || !password_verify($currentPassword, $user->password_hash)) {
            return false;
        }

        $user->password_hash = password_hash($newPassword, PASSWORD_BCRYPT);
        $user->save();

        $this->revokeAllTokens($userId);

        Logger::logAudit($userId, 'user.password_changed');

        return true;
    }

    protected function createRememberToken(int $userId): void
    {
        $token = Token::generate(64);
        $hashed = Token::hash($token);
        $expiresAt = date('Y-m-d H:i:s', time() + 2592000);

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO remember_tokens (user_id, token, expires_at, created_at) VALUES (?, ?, ?, NOW())",
            [$userId, $hashed, $expiresAt]
        );

        Session::set('remember_token', $token);
    }

    protected function logFailedAttempt(string $email, ?int $userId = null): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO failed_login_attempts (email, user_id, ip_address, created_at) VALUES (?, ?, ?, NOW())",
            [$email, $userId, $_SERVER['REMOTE_ADDR'] ?? null]
        );
    }

    protected function clearFailedAttempts(int $userId): void
    {
        $db = DB::getInstance();
        $db->run(
            "DELETE FROM failed_login_attempts WHERE user_id = ?",
            [$userId]
        );
    }

    protected function revokeAllTokens(int $userId): void
    {
        Token::revokeAllUserTokens($userId);

        $db = DB::getInstance();
        $db->run("DELETE FROM remember_tokens WHERE user_id = ?", [$userId]);
        $db->run("DELETE FROM user_sessions WHERE user_id = ?", [$userId]);
    }

    public function isLocked(int $userId): bool
    {
        $db = DB::getInstance();
        $result = $db->fetch(
            "SELECT COUNT(*) as count FROM failed_login_attempts WHERE user_id = ? AND created_at > DATE_SUB(NOW(), INTERVAL 15 MINUTE)",
            [$userId]
        );

        return ($result['count'] ?? 0) >= 5;
    }
}