<?php

session_start();

define('ROOT_PATH', dirname(__DIR__));

require ROOT_PATH . '/vendor/autoload.php';

$dotenv = ROOT_PATH . '/.env';
if (file_exists($dotenv)) {
    $lines = file($dotenv, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (str_starts_with($line, '#')) continue;
        $parts = explode('=', $line, 2);
        if (count($parts) === 2) {
            $_ENV[$parts[0]] = $parts[1];
            putenv("{$parts[0]}={$parts[1]}");
        }
    }
}

\Core\App::loadConfig();

require ROOT_PATH . '/core/Logger.php';

set_error_handler(function($severity, $message, $file, $line) {
    throw new \ErrorException($message, 0, $severity, $file, $line);
});

set_exception_handler(function($e) {
    $log = new \Core\Logger();
    $log->error($e->getMessage(), [
        'file' => $e->getFile(),
        'line' => $e->getLine(),
    ]);

    if (\Core\App::isDebug()) {
        echo json_encode([
            'status' => 'error',
            'message' => $e->getMessage(),
            'file' => $e->getFile(),
            'line' => $e->getLine(),
        ]);
    } else {
        echo json_encode([
            'status' => 'error',
            'message' => 'An error occurred',
        ]);
    }
    exit(1);
});

$router = new \Core\Router();

require ROOT_PATH . '/routes/api.php';
require ROOT_PATH . '/routes/auth.php';

$router->dispatch();