<?php

namespace App\Services\Providers;

interface EmailProviderInterface
{
    public function send(array $to, string $subject, string $body, ?string $altBody = null): bool;
    public function sendTemplate(string $template, array $data, array $to): bool;
}

interface StorageProviderInterface
{
    public function put(string $path, string $content): bool;
    public function get(string $path): ?string;
    public function exists(string $path): bool;
    public function delete(string $path): bool;
    public function getUrl(string $path): string;
}

interface OAuthProviderInterface
{
    public function getAuthUrl(): string;
    public function getToken(string $code): ?array;
    public function getUserInfo(string $accessToken): ?array;
    public function refreshToken(string $refreshToken): ?array;
}

class LocalStorageProvider implements StorageProviderInterface
{
    protected string $basePath;

    public function __construct(string $basePath = 'storage/uploads')
    {
        $this->basePath = $basePath;
        if (!is_dir($this->basePath)) {
            mkdir($this->basePath, 0755, true);
        }
    }

    public function put(string $path, string $content): bool
    {
        $fullPath = $this->basePath . '/' . $path;
        $dir = dirname($fullPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        return file_put_contents($fullPath, $content) !== false;
    }

    public function get(string $path): ?string
    {
        $fullPath = $this->basePath . '/' . $path;
        return file_exists($fullPath) ? file_get_contents($fullPath) : null;
    }

    public function exists(string $path): bool
    {
        return file_exists($this->basePath . '/' . $path);
    }

    public function delete(string $path): bool
    {
        $fullPath = $this->basePath . '/' . $path;
        return file_exists($fullPath) ? unlink($fullPath) : false;
    }

    public function getUrl(string $path): string
    {
        return '/storage/' . $path;
    }
}

class SmtpEmailProvider implements EmailProviderInterface
{
    protected array $config;

    public function __construct(array $config = [])
    {
        $this->config = $config;
    }

    public function send(array $to, string $subject, string $body, ?string $altBody = null): bool
    {
        $config = require __DIR__ . '/../../../config/mail.php';
        
        $headers = [];
        $headers[] = "MIME-Version: 1.0";
        $headers[] = "Content-type:text/html;charset=UTF-8";
        $headers[] = "From: {$config['from']['name']} <{$config['from']['address']}>";
        $headers[] = "Reply-To: {$config['from']['address']}";
        
        $toEmail = is_array($to) ? ($to['email'] ?? reset($to)) : $to;
        
        return mail($toEmail, $subject, $body, implode("\r\n", $headers));
    }

    public function sendTemplate(string $template, array $data, array $to): bool
    {
        $body = $this->renderTemplate($template, $data);
        $subject = $data['subject'] ?? 'WorkNest Notification';
        return $this->send($to, $subject, $body);
    }

    protected function renderTemplate(string $template, array $data): string
    {
        $html = '<html><body>';
        foreach ($data as $key => $value) {
            $html .= "<p>{$key}: {$value}</p>";
        }
        $html .= '</body></html>';
        return $html;
    }
}

class GoogleOAuthProvider implements OAuthProviderInterface
{
    protected string $clientId;
    protected string $clientSecret;
    protected string $redirectUri;

    public function __construct()
    {
        $config = require __DIR__ . '/../../../config/integrations.php';
        $google = $config['oauth']['google'] ?? [];
        $this->clientId = $google['client_id'] ?? '';
        $this->clientSecret = $google['client_secret'] ?? '';
        $this->redirectUri = $google['redirect_uri'] ?? '';
    }

    public function getAuthUrl(): string
    {
        $config = require __DIR__ . '/../../../config/integrations.php';
        $scopes = implode(' ', $config['oauth']['google']['scopes'] ?? []);
        
        return 'https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query([
            'client_id' => $this->clientId,
            'redirect_uri' => $this->redirectUri,
            'response_type' => 'code',
            'scope' => $scopes,
            'access_type' => 'offline',
        ]);
    }

    public function getToken(string $code): ?array
    {
        return null;
    }

    public function getUserInfo(string $accessToken): ?array
    {
        return null;
    }

    public function refreshToken(string $refreshToken): ?array
    {
        return null;
    }
}
