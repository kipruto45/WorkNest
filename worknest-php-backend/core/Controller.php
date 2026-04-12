<?php

namespace Core;

abstract class Controller
{
    protected Request $request;
    protected array $middleware = [];

    public function __construct()
    {
        $this->request = new Request();
    }

    public function getRequest(): Request
    {
        return $this->request;
    }

    protected function json(array $data, int $code = 200): void
    {
        Response::json($data, $code);
    }

    protected function success(array $data = [], string $message = 'Success'): void
    {
        JsonResponse::success($data, $message)->send();
    }

    protected function error(string $message, array $errors = [], int $code = 400): void
    {
        JsonResponse::error($message, $errors, $code)->send();
    }

    protected function notFound(string $message = 'Resource not found'): void
    {
        JsonResponse::notFound($message)->send();
    }

    protected function unauthorized(string $message = 'Unauthorized'): void
    {
        JsonResponse::unauthorized($message)->send();
    }

    protected function forbidden(string $message = 'Forbidden'): void
    {
        JsonResponse::forbidden($message)->send();
    }

    protected function validationError(string $message, array $errors): void
    {
        JsonResponse::validationError($message, $errors)->send();
    }

    protected function redirect(string $url): void
    {
        Response::redirect($url);
    }

    protected function input(string $key, $default = null)
    {
        return $this->request->input($key, $default);
    }

    protected function all(): array
    {
        return $this->request->all();
    }

    protected function user()
    {
        return Auth::user();
    }

    protected function authenticate(): bool
    {
        return Auth::check();
    }

    protected function authorize(?string $permission = null): bool
    {
        return Auth::can($permission);
    }
}