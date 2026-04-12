<?php

return [
    'oauth' => [
        'google' => [
            'enabled' => false,
            'client_id' => '',
            'client_secret' => '',
            'redirect_uri' => '',
            'scopes' => [
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
            ],
        ],
    ],
    'webhooks' => [
        'enabled' => false,
        'providers' => [
            'slack' => [
                'enabled' => false,
                'webhook_url' => '',
            ],
            'discord' => [
                'enabled' => false,
                'webhook_url' => '',
            ],
        ],
    ],
    'storage' => [
        'default' => 'local',
        'local' => [
            'path' => 'storage/uploads',
        ],
    ],
];