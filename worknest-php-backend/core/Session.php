<?php

namespace Core;

class Session
{
    protected static bool $started = false;

    public static function start(): void
    {
        if (static::$started) {
            return;
        }

        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }

        static::$started = true;
    }

    public static function get(string $key, $default = null)
    {
        static::start();
        return $_SESSION[$key] ?? $default;
    }

    public static function set(string $key, $value): void
    {
        static::start();
        $_SESSION[$key] = $value;
    }

    public static function has(string $key): bool
    {
        static::start();
        return isset($_SESSION[$key]);
    }

    public static function forget(string $key): void
    {
        static::start();
        unset($_SESSION[$key]);
    }

    public static function flush(): void
    {
        static::start();
        $_SESSION = [];
    }

    public static function destroy(): void
    {
        static::start();
        session_destroy();
        static::$started = false;
    }

    public static function regenerate(): void
    {
        static::start();
        session_regenerate_id(true);
    }

    public static function token(): string
    {
        static::start();
        if (!isset($_SESSION['_token'])) {
            $_SESSION['_token'] = bin2hex(random_bytes(32));
        }
        return $_SESSION['_token'];
    }

    public static function flash(string $key, $value = null)
    {
        static::start();
        if ($value === null) {
            $value = $_SESSION['_flash'][$key] ?? null;
            unset($_SESSION['_flash'][$key]);
            return $value;
        }

        if (!isset($_SESSION['_flash'])) {
            $_SESSION['_flash'] = [];
        }
        $_SESSION['_flash'][$key] = $value;
    }

    public static function flashAll(): array
    {
        static::start();
        $flash = $_SESSION['_flash'] ?? [];
        $_SESSION['_flash'] = [];
        return $flash;
    }

    public static function id(): string
    {
        static::start();
        return session_id();
    }

    public static function getAll(): array
    {
        static::start();
        return $_SESSION;
    }
}