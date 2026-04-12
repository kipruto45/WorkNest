<?php

namespace Core;

class Request
{
    protected array $params = [];
    protected array $headers = [];

    public function __construct()
    {
        $this->params = array_merge($_GET, $_POST);
        $this->headers = $this->parseHeaders();
    }

    private function parseHeaders(): array
    {
        $headers = [];
        foreach ($_SERVER as $key => $value) {
            if (str_starts_with($key, 'HTTP_')) {
                $headers[strtolower(str_replace('_', '-', substr($key, 5)))] = $value;
            }
        }
        return $headers;
    }

    public function method(): string
    {
        return strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
    }

    public function isGet(): bool
    {
        return $this->method() === 'GET';
    }

    public function isPost(): bool
    {
        return $this->method() === 'POST';
    }

    public function isPut(): bool
    {
        return $this->method() === 'PUT';
    }

    public function isDelete(): bool
    {
        return $this->method() === 'DELETE';
    }

    public function isAjax(): bool
    {
        return isset($this->headers['x-requested-with']) &&
            strtolower($this->headers['x-requested-with']) === 'xmlhttprequest';
    }

    public function uri(): string
    {
        return $_SERVER['REQUEST_URI'] ?? '/';
    }

    public function path(): string
    {
        $uri = $this->uri();
        $path = parse_url($uri, PHP_URL_PATH);
        return $path ?? '/';
    }

    public function header(string $key, $default = null)
    {
        $key = strtolower($key);
        return $this->headers[$key] ?? $default;
    }

    public function get(string $key, $default = null)
    {
        return $this->params[$key] ?? $default;
    }

    public function post(string $key, $default = null)
    {
        return $_POST[$key] ?? $default;
    }

    public function input(string $key, $default = null)
    {
        $value = $_POST[$key] ?? $_GET[$key] ?? $default;

        if (is_string($value)) {
            return trim($value);
        }

        return $value;
    }

    public function all(): array
    {
        return $this->params;
    }

    public function has(string $key): bool
    {
        return isset($this->params[$key]);
    }

    public function only(array $keys): array
    {
        $data = [];
        foreach ($keys as $key) {
            if (isset($this->params[$key])) {
                $data[$key] = $this->params[$key];
            }
        }
        return $data;
    }

    public function except(array $keys): array
    {
        $data = $this->params;
        foreach ($keys as $key) {
            unset($data[$key]);
        }
        return $data;
    }

    public function bearerToken(): ?string
    {
        $header = $this->header('authorization', '');
        if (preg_match('/Bearer\s+(.+)/i', $header, $matches)) {
            return $matches[1];
        }
        return null;
    }

    public function ip(): string
    {
        return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }

    public function userAgent(): string
    {
        return $_SERVER['HTTP_USER_AGENT'] ?? '';
    }
}