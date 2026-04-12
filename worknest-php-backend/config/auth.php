<?php

return [
    'providers' => [
        'email' => true,
        'google' => false,
    ],
    'password_min_length' => 8,
    'password_require_uppercase' => true,
    'password_require_lowercase' => true,
    'password_require_numbers' => true,
    'password_require_special' => false,
    'max_login_attempts' => 5,
    'lockout_duration' => 900,
    'session_lifetime' => (int) (getenv('SESSION_LIFETIME') ?: 120),
    'token_lifetime' => (int) (getenv('API_TOKEN_LIFETIME') ?: 86400),
    'remember_token_lifetime' => 2592000,
    'csrf_token_name' => '_token',
    'csrf_enabled' => true,
];