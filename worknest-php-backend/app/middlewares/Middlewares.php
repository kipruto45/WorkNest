<?php

namespace App\Middlewares;

use Core\Auth;

class AuthMiddleware
{
    public function handle(callable $next): void
    {
        if (!Auth::check()) {
            http_response_code(401);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Unauthorized']);
            exit;
        }
        $next();
    }
}

class GuestMiddleware
{
    public function handle(callable $next): void
    {
        if (Auth::check()) {
            http_response_code(302);
            header('Location: /dashboard');
            exit;
        }
        $next();
    }
}

class ApiAuthMiddleware
{
    public function handle(callable $next): void
    {
        $request = new \Core\Request();
        $token = $request->bearerToken();
        
        if (!$token) {
            http_response_code(401);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Token required']);
            exit;
        }
        
        $tokenData = \Core\Token::validateApiToken($token);
        if (!$tokenData) {
            http_response_code(401);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Invalid token']);
            exit;
        }
        
        Auth::login($tokenData['user_id']);
        $next();
    }
}

class RoleMiddleware
{
    protected string $role;

    public function __construct(string $role = 'member')
    {
        $this->role = $role;
    }

    public function handle(callable $next): void
    {
        $user = Auth::user();
        if (!$user || !in_array($user->role, ['owner', 'admin', $this->role])) {
            http_response_code(403);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Forbidden']);
            exit;
        }
        $next();
    }
}

class PermissionMiddleware
{
    protected string $permission;

    public function __construct(string $permission)
    {
        $this->permission = $permission;
    }

    public function handle(callable $next): void
    {
        if (!Auth::can($this->permission)) {
            http_response_code(403);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Permission denied']);
            exit;
        }
        $next();
    }
}

class OwnershipMiddleware
{
    protected string $model;
    protected string $field;

    public function __construct(string $model, string $field = 'user_id')
    {
        $this->model = $model;
        $this->field = $field;
    }

    public function handle(callable $next): void
    {
        $request = new \Core\Request();
        $id = $request->input('id') ?? 0;
        
        $modelClass = "App\\Models\\{$this->model}";
        if (!class_exists($modelClass)) {
            $next();
            return;
        }
        
        $record = $modelClass::find($id);
        if (!$record || !Auth::owns($record->{$this->field})) {
            http_response_code(403);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Ownership required']);
            exit;
        }
        $next();
    }
}

class CSRFMiddleware
{
    public function handle(callable $next): void
    {
        $request = new \Core\Request();
        if ($request->isPost()) {
            $token = $request->input('_token');
            if (!\Core\CSRF::verify($token)) {
                http_response_code(419);
                header('Content-Type: application/json');
                echo json_encode(['status' => 'error', 'message' => 'CSRF token mismatch']);
                exit;
            }
        }
        $next();
    }
}

class RateLimitMiddleware
{
    protected int $maxAttempts;
    protected int $decaySeconds;

    public function __construct(int $maxAttempts = 5, int $decaySeconds = 300)
    {
        $this->maxAttempts = $maxAttempts;
        $this->decaySeconds = $decaySeconds;
    }

    public function handle(callable $next): void
    {
        $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
        $key = "rate_limit:{$ip}";
        
        $attempts = (int) ($_SESSION[$key] ?? 0);
        if ($attempts >= $this->maxAttempts) {
            http_response_code(429);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Too many requests']);
            exit;
        }
        
        $_SESSION[$key] = $attempts + 1;
        $next();
    }
}

class TeamAccessMiddleware
{
    public function handle(callable $next): void
    {
        $request = new \Core\Request();
        $teamId = $request->input('team_id') ?? 0;
        
        if ($teamId && !Auth::isTeamMember($teamId)) {
            http_response_code(403);
            header('Content-Type: application/json');
            echo json_encode(['status' => 'error', 'message' => 'Team access denied']);
            exit;
        }
        $next();
    }
}
