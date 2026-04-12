<?php

namespace Core;

class JsonResponse
{
    protected array $data = [];
    protected string $message = '';
    protected string $status = 'success';
    protected array $errors = [];
    protected array $meta = [];
    protected int $httpCode = 200;

    public static function make(
        array $data = [],
        string $message = '',
        string $status = 'success',
        int $httpCode = 200
    ): self {
        $response = new self();
        $response->data = $data;
        $response->message = $message;
        $response->status = $status;
        $response->httpCode = $httpCode;
        return $response;
    }

    public static function success(
        array $data = [],
        string $message = 'Success',
        int $httpCode = 200
    ): self {
        return self::make($data, $message, 'success', $httpCode);
    }

    public static function error(
        string $message = 'An error occurred',
        array $errors = [],
        int $httpCode = 400
    ): self {
        $response = new self();
        $response->message = $message;
        $response->errors = $errors;
        $response->status = 'error';
        $response->httpCode = $httpCode;
        return $response;
    }

    public static function notFound(string $message = 'Resource not found'): self
    {
        return self::error($message, [], 404);
    }

    public static function unauthorized(string $message = 'Unauthorized'): self
    {
        return self::error($message, [], 401);
    }

    public static function forbidden(string $message = 'Forbidden'): self
    {
        return self::error($message, [], 403);
    }

    public static function validationError(
        string $message = 'Validation failed',
        array $errors = []
    ): self {
        return self::error($message, $errors, 422);
    }

    public function setData(array $data): self
    {
        $this->data = $data;
        return $this;
    }

    public function setMeta(array $meta): self
    {
        $this->meta = $meta;
        return $this;
    }

    public function withMeta(string $key, $value): self
    {
        $this->meta[$key] = $value;
        return $this;
    }

    public function send(): void
    {
        http_response_code($this->httpCode);
        header('Content-Type: application/json');

        $response = [
            'status' => $this->status,
            'message' => $this->message,
            'data' => $this->data,
        ];

        if (!empty($this->errors)) {
            $response['errors'] = $this->errors;
        }

        if (!empty($this->meta)) {
            $response['meta'] = $this->meta;
        }

        echo json_encode($response);
    }

    public function toArray(): array
    {
        return [
            'status' => $this->status,
            'message' => $this->message,
            'data' => $this->data,
            'errors' => $this->errors,
            'meta' => $this->meta,
        ];
    }
}

class Response
{
    public static function json($data, int $code = 200): void
    {
        http_response_code($code);
        header('Content-Type: application/json');
        echo json_encode($data);
    }

    public static function redirect(string $url, int $code = 302): void
    {
        header("Location: {$url}", true, $code);
    }

    public static function download(string $filePath, string $filename = ''): void
    {
        if (!file_exists($filePath)) {
            http_response_code(404);
            exit;
        }

        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mimeType = finfo_file($finfo, $filePath);
        finfo_close($finfo);

        header('Content-Type: ' . $mimeType);
        header('Content-Length: ' . filesize($filePath));
        header('Content-Disposition: attachment; filename="' . ($filename ?: basename($filePath)) . '"');
        header('Cache-Control: no-cache, must-revalidate');

        readfile($filePath);
    }

    public static function file(string $filePath): void
    {
        if (!file_exists($filePath)) {
            http_response_code(404);
            exit;
        }

        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mimeType = finfo_file($finfo, $filePath);
        finfo_close($finfo);

        header('Content-Type: ' . $mimeType);
        header('Content-Length: ' . filesize($filePath));
        header('Cache-Control: max-age=86400');

        readfile($filePath);
    }
}