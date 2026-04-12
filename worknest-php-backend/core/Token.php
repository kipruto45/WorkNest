<?php

namespace Core;

class Token
{
    public static function generate(int $length = 32): string
    {
        return bin2hex(random_bytes($length / 2));
    }

    public static function generateSecure(int $length = 32): string
    {
        if (version_compare(PHP_VERSION, '7.0', '>=')) {
            return bin2hex(random_bytes($length / 2));
        }

        $characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
        $charactersLength = strlen($characters);
        $token = '';

        for ($i = 0; $i < $length; $i++) {
            $token .= $characters[random_int(0, $charactersLength - 1)];
        }

        return $token;
    }

    public static function generateApiToken(): string
    {
        return 'wkn_' . static::generateSecure(48);
    }

    public static function generateEmailToken(): string
    {
        return static::generateSecure(32);
    }

    public static function hash(string $token): string
    {
        return hash('sha256', $token);
    }

    public static function verify(string $token, string $hashed): bool
    {
        return hash_equals($token, $hashed);
    }

    public static function storeApiToken(string $token, int $userId, int $expiresIn = 86400): void
    {
        $db = DB::getInstance();
        $hashed = static::hash($token);
        $expiresAt = date('Y-m-d H:i:s', time() + $expiresIn);

        $db->run(
            "DELETE FROM api_tokens WHERE user_id = ? AND expires_at < NOW()",
            [$userId]
        );

        $db->run(
            "INSERT INTO api_tokens (user_id, token, expires_at, created_at) VALUES (?, ?, ?, NOW())",
            [$userId, $hashed, $expiresAt]
        );
    }

    public static function validateApiToken(string $token): ?array
    {
        $hashed = static::hash($token);
        $db = DB::getInstance();

        $result = $db->fetch(
            "SELECT * FROM api_tokens WHERE token = ? AND expires_at > NOW()",
            [$hashed]
        );

        if (!$result) {
            return null;
        }

        return $result;
    }

    public static function revokeApiToken(string $token): void
    {
        $hashed = static::hash($token);
        $db = DB::getInstance();
        $db->run("DELETE FROM api_tokens WHERE token = ?", [$hashed]);
    }

    public static function revokeAllUserTokens(int $userId): void
    {
        $db = DB::getInstance();
        $db->run("DELETE FROM api_tokens WHERE user_id = ?", [$userId]);
    }
}