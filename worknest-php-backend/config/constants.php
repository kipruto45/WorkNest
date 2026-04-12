<?php

return [
    'USER_ROLES' => [
        'owner' => 'owner',
        'admin' => 'admin',
        'member' => 'member',
    ],
    'TEAM_ROLES' => [
        'team_owner' => 'team_owner',
        'team_admin' => 'team_admin',
        'team_member' => 'team_member',
        'guest' => 'guest',
    ],
    'TASK_STATUSES' => [
        'todo' => 'todo',
        'in_progress' => 'in_progress',
        'in_review' => 'in_review',
        'done' => 'done',
        'archived' => 'archived',
    ],
    'TASK_PRIORITIES' => [
        'low' => 'low',
        'medium' => 'medium',
        'high' => 'high',
        'urgent' => 'urgent',
    ],
    'INVITATION_STATUSES' => [
        'pending' => 'pending',
        'accepted' => 'accepted',
        'expired' => 'expired',
        'revoked' => 'revoked',
    ],
    'PERMISSIONS' => [
        'create_team',
        'edit_team',
        'delete_team',
        'invite_member',
        'remove_member',
        'create_task',
        'edit_task',
        'delete_task',
        'assign_task',
        'comment_task',
        'upload_attachment',
        'manage_notifications',
        'export_reports',
        'view_audit_logs',
    ],
    'USER_STATUSES' => [
        'active' => 'active',
        'inactive' => 'inactive',
        'suspended' => 'suspended',
    ],
    'ATTACHMENT_MAX_SIZE' => 10485760,
    'AVATAR_MAX_SIZE' => 2097152,
    'PAGINATION_DEFAULT' => 15,
    'PAGINATION_MAX' => 100,
];