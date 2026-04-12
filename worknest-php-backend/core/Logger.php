<?php

namespace Core;

class Logger
{
    protected string $path = 'storage/logs';
    protected string $filename = '';

    public function __construct(string $filename = 'app.log')
    {
        $this->filename = $filename;
        $this->path = App::config('app.log_path', 'storage/logs') ?? 'storage/logs';

        if (!is_dir($this->path)) {
            mkdir($this->path, 0755, true);
        }
    }

    public function log(string $level, string $message, array $context = []): void
    {
        $timestamp = date('Y-m-d H:i:s');
        $contextString = empty($context) ? '' : ' ' . json_encode($context);
        $logMessage = "[{$timestamp}] {$level}: {$message}{$contextString}" . PHP_EOL;

        $filepath = $this->path . '/' . $this->filename;
        file_put_contents($filepath, $logMessage, FILE_APPEND);
    }

    public function debug(string $message, array $context = []): void
    {
        $this->log('DEBUG', $message, $context);
    }

    public function info(string $message, array $context = []): void
    {
        $this->log('INFO', $message, $context);
    }

    public function warning(string $message, array $context = []): void
    {
        $this->log('WARNING', $message, $context);
    }

    public function error(string $message, array $context = []): void
    {
        $this->log('ERROR', $message, $context);
    }

    public function critical(string $message, array $context = []): void
    {
        $this->log('CRITICAL', $message, $context);
    }

    public static function logException(\Throwable $e): void
    {
        $logger = new self();
        $logger->error($e->getMessage(), [
            'file' => $e->getFile(),
            'line' => $e->getLine(),
            'trace' => $e->getTraceAsString(),
        ]);
    }

    public static function logActivity(int $userId, string $action, string $entityType, int $entityId, array $metadata = []): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO activity_logs (user_id, action, entity_type, entity_id, metadata, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
            [$userId, $action, $entityType, $entityId, json_encode($metadata)]
        );
    }

    public static function logAudit(int $userId, string $action, array $details = []): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO audit_logs (user_id, action, details, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
            [
                $userId,
                $action,
                json_encode($details),
                $_SERVER['REMOTE_ADDR'] ?? null,
                $_SERVER['HTTP_USER_AGENT'] ?? null,
            ]
        );
    }
}