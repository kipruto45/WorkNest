<?php

return [
    'driver' => getenv('MAIL_DRIVER') ?: 'smtp',
    'host' => getenv('MAIL_HOST') ?: 'localhost',
    'port' => (int) (getenv('MAIL_PORT') ?: 1025),
    'username' => getenv('MAIL_USERNAME') ?: '',
    'password' => getenv('MAIL_PASSWORD') ?: '',
    'encryption' => getenv('MAIL_ENCRYPTION') ?: null,
    'from' => [
        'address' => getenv('MAIL_FROM_ADDRESS') ?: 'noreply@worknest.local',
        'name' => getenv('MAIL_FROM_NAME') ?: 'WorkNest',
    ],
];