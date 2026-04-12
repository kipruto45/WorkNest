<?php

return [
    'name' => getenv('APP_NAME') ?: 'WorkNest',
    'version' => getenv('APP_VERSION') ?: '1.0.0',
    'env' => getenv('APP_ENV') ?: 'local',
    'debug' => (bool) (getenv('APP_DEBUG') ?: true),
    'url' => getenv('APP_URL') ?: 'http://localhost:8000',
    'timezone' => getenv('APP_TIMEZONE') ?: 'UTC',
    'locale' => 'en',
    'fallback_locale' => 'en',
    'key' => getenv('APP_KEY') ?: 'default-key-change-in-production',
    'cipher' => 'AES-256-CBC',
];