<?php

namespace Core;

function config(string $key, $default = null)
{
    return App::config($key, $default);
}

function env(string $key, $default = null)
{
    return getenv($key) ?: $default;
}

function now(): string
{
    return date('Y-m-d H:i:s');
}

function today(): string
{
    return date('Y-m-d');
}

function dd(...$vars): void
{
    foreach ($vars as $var) {
        var_dump($var);
    }
    exit;
}

function array_get(array $array, string $key, $default = null)
{
    $keys = explode('.', $key);
    $value = $array;

    foreach ($keys as $k) {
        if (!isset($value[$k])) {
            return $default;
        }
        $value = $value[$k];
    }

    return $value;
}

function array_only(array $array, array $keys): array
{
    return array_intersect_key($array, array_flip($keys));
}

function array_except(array $array, array $keys): array
{
    return array_diff_key($array, array_flip($keys));
}

function array_pluck(array $array, string $key): array
{
    return array_map(fn($item) => is_array($item) ? ($item[$key] ?? null) : ($item->$key ?? null), $array);
}

function array_sum_by(array $array, string $key): float
{
    return array_sum(array_pluck($array, $key));
}

function str_slug(string $string): string
{
    $string = strtolower($string);
    $string = preg_replace('/[^a-z0-9-]/', '-', $string);
    $string = preg_replace('/-+/', '-', $string);
    return trim($string, '-');
}

function str_limit(string $string, int $limit = 100, string $end = '...'): string
{
    if (mb_strlen($string) <= $limit) {
        return $string;
    }
    return mb_substr($string, 0, $limit) . $end;
}

function str_random(int $length = 16): string
{
    return bin2hex(random_bytes($length / 2));
}

function str_finish(string $string, string $finish): string
{
    $string = trim($string);
    if (!str_ends_with($string, $finish)) {
        $string .= $finish;
    }
    return $string;
}

function starts_with(string $string, string $needle): bool
{
    return str_starts_with($string, $needle);
}

function ends_with(string $string, string $needle): bool
{
    return str_ends_with($string, $needle);
}

function contains(string $string, string $needle): bool
{
    return str_contains($string, $needle);
}

function redirect(string $url, int $code = 302): void
{
    Response::redirect($url, $code);
}

function back(): void
{
    Response::redirect($_SERVER['HTTP_REFERER'] ?? '/');
}

function view(string $template, array $data = []): void
{
    extract($data);
    include __DIR__ . '/../resources/views/' . $template . '.php';
}

function e(string $string): string
{
    return htmlspecialchars($string, ENT_QUOTES, 'UTF-8');
}

function old(string $key, $default = ''): string
{
    return Session::get('old.' . $key, $default);
}

function auth(): ?object
{
    return Auth::user();
}

function user(): ?object
{
    return Auth::user();
}

function user_id(): ?int
{
    return Auth::id();
}

function can(string $permission): bool
{
    return Auth::can($permission);
}

function can_team(string $permission, int $teamId): bool
{
    return Auth::canTeam($permission, $teamId);
}

function route(string $name, array $params = []): string
{
    return Route::get($name, $params);
}

function asset(string $path): string
{
    return App::config('app.url') . '/assets/' . ltrim($path, '/');
}

function storage(string $path): string
{
    return App::config('app.url') . '/storage/' . ltrim($path, '/');
}

function current_url(): string
{
    return App::config('app.url') . $_SERVER['REQUEST_URI'];
}

function current_full_url(): string
{
    $scheme = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http';
    return $scheme . '://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
}

function isAjax(): bool
{
    return isset($_SERVER['HTTP_X_REQUESTED_WITH']) &&
        strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
}

function request(): Request
{
    return new Request();
}

function response(): JsonResponse
{
    return new JsonResponse();
}