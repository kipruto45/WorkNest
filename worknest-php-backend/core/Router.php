<?php

namespace Core;

class Router
{
    protected array $routes = [];
    protected array $groupMiddleware = [];
    protected array $groupPrefix = '';
    protected array $groupNamespace = '';

    public function get(string $path, $handler): self
    {
        return $this->addRoute('GET', $path, $handler);
    }

    public function post(string $path, $handler): self
    {
        return $this->addRoute('POST', $path, $handler);
    }

    public function put(string $path, $handler): self
    {
        return $this->addRoute('PUT', $path, $handler);
    }

    public function patch(string $path, $handler): self
    {
        return $this->addRoute('PATCH', $path, $handler);
    }

    public function delete(string $path, $handler): self
    {
        return $this->addRoute('DELETE', $path, $handler);
    }

    public function any(string $path, $handler): self
    {
        $methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
        foreach ($methods as $method) {
            $this->addRoute($method, $path, $handler);
        }
        return $this;
    }

    protected function addRoute(string $method, string $path, $handler): self
    {
        $path = $this->groupPrefix . $path;
        $path = trim($path, '/');
        $path = $path ?: '/';

        $route = [
            'method' => $method,
            'path' => $path,
            'handler' => $handler,
            'middleware' => $this->groupMiddleware,
            'namespace' => $this->groupNamespace,
        ];

        $this->routes[] = $route;
        return $this;
    }

    public function group(array $options, callable $callback): void
    {
        $previousPrefix = $this->groupPrefix;
        $previousMiddleware = $this->groupMiddleware;
        $previousNamespace = $this->groupNamespace;

        if (isset($options['prefix'])) {
            $this->groupPrefix = $options['prefix'];
        }

        if (isset($options['middleware'])) {
            $this->groupMiddleware = array_merge($this->groupMiddleware, $options['middleware']);
        }

        if (isset($options['namespace'])) {
            $this->groupNamespace = $options['namespace'];
        }

        $callback($this);

        $this->groupPrefix = $previousPrefix;
        $this->groupMiddleware = $previousMiddleware;
        $this->groupNamespace = $previousNamespace;
    }

    public function dispatch(): void
    {
        $request = new Request();
        $method = $request->method();
        $path = $request->path();

        $route = $this->findRoute($method, $path);

        if (!$route) {
            $this->handleNotFound();
            return;
        }

        $this->runMiddleware($route['middleware'], function() use ($route, $request) {
            $this->executeHandler($route, $request);
        });
    }

    protected function findRoute(string $method, string $path): ?array
    {
        foreach ($this->routes as $route) {
            if ($route['method'] !== $method) {
                continue;
            }

            $pattern = $this->convertToRegex($route['path']);
            if (preg_match($pattern, $path, $matches)) {
                unset($matches[0]);
                $route['params'] = $matches;
                return $route;
            }
        }

        return null;
    }

    protected function convertToRegex(string $path): string
    {
        $pattern = preg_replace('/\//', '\\/', $path);
        $pattern = preg_replace('/\{([a-zA-Z_]+)\}/', '(?P<$1>[^/]+)', $pattern);
        return '/^' . $pattern . '$/';
    }

    protected function handleNotFound(): void
    {
        http_response_code(404);
        header('Content-Type: application/json');
        echo json_encode(['status' => 'error', 'message' => 'Endpoint not found']);
    }

    protected function runMiddleware(array $middlewares, callable $next): void
    {
        if (empty($middlewares)) {
            $next();
            return;
        }

        $middleware = array_shift($middlewares);
        $this->runMiddleware($middlewares, $next);

        if (is_string($middleware) && class_exists($middleware)) {
            $instance = new $middleware();
            if (method_exists($instance, 'handle')) {
                $instance->handle(function() use ($next) {
                    $next();
                });
            }
        }
    }

    protected function executeHandler(array $route, Request $request): void
    {
        $handler = $route['handler'];
        $params = $route['params'] ?? [];

        if (is_callable($handler)) {
            call_user_func_array($handler, array_values($params));
            return;
        }

        if (is_string($handler)) {
            $parts = explode('@', $handler);
            if (count($parts) !== 2) {
                throw new \RuntimeException('Invalid handler format');
            }

            $controllerNamespace = $route['namespace'] ?? '';
            $controllerClass = $controllerNamespace . '\\' . $parts[0];
            $method = $parts[1];

            if (!class_exists($controllerClass)) {
                throw new \RuntimeException("Controller not found: {$controllerClass}");
            }

            $controller = new $controllerClass();

            if (!method_exists($controller, $method)) {
                throw new \RuntimeException("Method not found: {$method}");
            }

            call_user_func_array([$controller, $method], array_values($params));
            return;
        }

        throw new \RuntimeException('Invalid handler');
    }

    public function getRoutes(): array
    {
        return $this->routes;
    }
}