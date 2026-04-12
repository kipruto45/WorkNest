<?php

require __DIR__ . '/../vendor/autoload.php';

use Core\DB;

$schemaFile = __DIR__ . '/../database/schema/schema.sql';

if (!file_exists($schemaFile)) {
    die("Schema file not found. Run migrate.php first.\n");
}

$db = DB::getInstance();

echo "=== WorkNest Database Reset ===\n\n";
echo "Dropping all tables...\n";

$tables = [
    'health_checks', 'jobs_log', 'settings', 'storage_providers', 'email_deliveries',
    'webhook_logs', 'oauth_connections', 'integration_settings', 'integration_providers',
    'activity_logs', 'audit_logs', 'report_exports', 'widget_preferences', 'dashboard_snapshots',
    'notification_preferences', 'notification_reads', 'notifications', 'attachment_links',
    'attachment_versions', 'attachments', 'comment_reactions', 'comment_mentions', 'comments',
    'task_time_logs', 'task_due_dates', 'task_checklist_items', 'task_checklists', 'subtasks',
    'task_label_links', 'task_labels', 'task_watchers', 'task_assignees', 'tasks',
    'task_priorities', 'task_statuses', 'task_lists', 'invitation_tokens', 'invitations',
    'membership_roles', 'memberships', 'team_settings', 'teams', 'api_tokens', 'user_sessions',
    'failed_login_attempts', 'remember_tokens', 'email_verifications', 'password_resets',
    'user_profiles', 'users'
];

foreach ($tables as $table) {
    try {
        $db->run("DROP TABLE IF EXISTS {$table}");
        echo ".";
    } catch (Exception $e) {
        echo "F";
    }
}

echo "\n\nRunning migrations...\n";
$content = file_get_contents($schemaFile);
$statements = array_filter(array_map('trim', explode(';', $content)));

foreach ($statements as $statement) {
    if (!empty($statement) && !str_starts_with($statement, '--')) {
        try {
            $db->run($statement);
        } catch (Exception $e) {
            // Ignore errors from statements that depend on each other
        }
    }
    echo ".";
}

echo "\n\n=== Database Reset Complete! ===\n\n";
echo "You can now run: php scripts/seed.php\n";