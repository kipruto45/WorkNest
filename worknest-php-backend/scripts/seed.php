<?php

require __DIR__ . '/../vendor/autoload.php';

use Core\DB;

echo "=== WorkNest Database Seeder ===\n\n";

$db = DB::getInstance();

$users = [
    ['name' => 'John Owner', 'email' => 'owner@example.com', 'password' => 'password123', 'role' => 'owner'],
    ['name' => 'Jane Admin', 'email' => 'admin@example.com', 'password' => 'password123', 'role' => 'admin'],
    ['name' => 'Bob Member', 'email' => 'member1@example.com', 'password' => 'password123', 'role' => 'member'],
    ['name' => 'Alice Member', 'email' => 'member2@example.com', 'password' => 'password123', 'role' => 'member'],
    ['name' => 'Charlie Member', 'email' => 'member3@example.com', 'password' => 'password123', 'role' => 'member'],
];

echo "Seeding users...\n";
foreach ($users as $user) {
    $hash = password_hash($user['password'], PASSWORD_BCRYPT);
    $db->run(
        "INSERT INTO users (email, password_hash, name, role, status, email_verified_at, created_at) VALUES (?, ?, ?, ?, 'active', NOW(), NOW())",
        [$user['email'], $hash, $user['name'], $user['role']]
    );
    $userId = $db->lastInsertId();
    $db->run("INSERT INTO user_profiles (user_id, bio, created_at) VALUES (?, ?, NOW())", [$userId, "Bio for {$user['name']}"]);
    echo "  Created user: {$user['email']}\n";
}

echo "\nSeeding teams...\n";
$teams = [
    ['name' => 'Engineering Team', 'slug' => 'engineering', 'description' => 'Main engineering team'],
    ['name' => 'Product Team', 'slug' => 'product', 'description' => 'Product development team'],
];

foreach ($teams as $team) {
    $db->run(
        "INSERT INTO teams (name, slug, description, owner_id, status, created_at) VALUES (?, ?, ?, 1, 'active', NOW())",
        [$team['name'], $team['slug'], $team['description']]
    );
    $teamId = $db->lastInsertId();
    
    $db->run("INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (1, ?, 'team_owner', 'active', NOW())", [$teamId]);
    $db->run("INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (2, ?, 'team_admin', 'active', NOW())", [$teamId]);
    $db->run("INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (3, ?, 'team_member', 'active', NOW())", [$teamId]);
    $db->run("INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (4, ?, 'team_member', 'active', NOW())", [$teamId]);
    $db->run("INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (5, ?, 'team_member', 'active', NOW())", [$teamId]);
    
    $statuses = [['name' => 'To Do', 'slug' => 'todo', 'color' => '#6b7280'], ['name' => 'In Progress', 'slug' => 'in_progress', 'color' => '#3b82f6'], ['name' => 'In Review', 'slug' => 'in_review', 'color' => '#f59e0b'], ['name' => 'Done', 'slug' => 'done', 'color' => '#10b981']];
    foreach ($statuses as $i => $status) {
        $db->run("INSERT INTO task_statuses (team_id, name, slug, color, position, is_default, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())", [$teamId, $status['name'], $status['slug'], $status['color'], $i + 1, $i === 0 ? 1 : 0]);
    }
    echo "  Created team: {$team['name']}\n";
}

echo "\nSeeding tasks...\n";
$taskTitles = [
    ['title' => 'Setup development environment', 'status' => 'done', 'priority' => 'high'],
    ['title' => 'Design database schema', 'status' => 'done', 'priority' => 'high'],
    ['title' => 'Implement authentication', 'status' => 'done', 'priority' => 'high'],
    ['title' => 'Create user profiles', 'status' => 'in_progress', 'priority' => 'high'],
    ['title' => 'Build team management', 'status' => 'in_progress', 'priority' => 'medium'],
    ['title' => 'Task creation UI', 'status' => 'in_progress', 'priority' => 'medium'],
    ['title' => 'Comment system', 'status' => 'todo', 'priority' => 'medium'],
    ['title' => 'File attachments', 'status' => 'todo', 'priority' => 'medium'],
    ['title' => 'Notifications', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'Dashboard widgets', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'Search functionality', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'Export reports', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'User settings page', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'Team settings', 'status' => 'todo', 'priority' => 'medium'],
    ['title' => 'API documentation', 'status' => 'todo', 'priority' => 'low'],
    ['title' => 'Testing & bug fixes', 'status' => 'todo', 'priority' => 'urgent'],
];

foreach ($taskTitles as $i => $task) {
    $db->run(
        "INSERT INTO tasks (team_id, title, status, priority, created_by, created_at) VALUES (1, ?, ?, ?, 1, NOW())",
        [$task['title'], $task['status'], $task['priority']]
    );
    $taskId = $db->lastInsertId();
    $db->run("INSERT INTO task_assignees (task_id, user_id, assigned_by, created_at) VALUES (?, ?, 1, NOW())", [$taskId, ($i % 5) + 1]);
    
    if ($i < 3) {
        $db->run("INSERT INTO subtasks (task_id, title, is_completed, position, created_by, created_at) VALUES (?, 'Subtask 1', 1, 1, 1, NOW())", [$taskId]);
        $db->run("INSERT INTO subtasks (task_id, title, is_completed, position, created_by, created_at) VALUES (?, 'Subtask 2', 1, 2, 1, NOW())", [$taskId]);
    }
}

echo "  Created 16 tasks\n";

echo "\nSeeding comments...\n";
$db->run("INSERT INTO comments (task_id, user_id, content, created_at) VALUES (1, 1, 'Great progress on this task!', NOW())");
$db->run("INSERT INTO comments (task_id, user_id, content, created_at) VALUES (1, 2, 'Looks good, please review.', NOW())");
$db->run("INSERT INTO comments (task_id, user_id, content, created_at) VALUES (2, 3, 'Schema needs some adjustments.', NOW())");
echo "  Created 3 comments\n";

echo "\nSeeding notifications...\n";
foreach (range(1, 5) as $userId) {
    $db->run("INSERT INTO notifications (user_id, type, title, message, is_read, created_at) VALUES (?, 'system', 'Welcome to WorkNest', 'Welcome! Start collaborating with your team.', 0, NOW())", [$userId]);
}
$db->run("INSERT INTO notifications (user_id, type, title, message, is_read, created_at) VALUES (1, 'task', 'Task Assigned', 'You have been assigned to a new task', 0, NOW())");
$db->run("INSERT INTO notifications (user_id, type, title, message, is_read, created_at) VALUES (2, 'task', 'Task Completed', 'A task has been marked as completed', 1, NOW())");
echo "  Created notifications\n";

echo "\nSeeding activity logs...\n";
$db->run("INSERT INTO activity_logs (user_id, team_id, action, entity_type, entity_id, metadata, created_at) VALUES (1, 1, 'team.created', 'team', 1, '{\"name\":\"Engineering Team\"}', NOW())");
$db->run("INSERT INTO activity_logs (user_id, team_id, action, entity_type, entity_id, metadata, created_at) VALUES (1, 1, 'task.created', 'task', 1, '{\"title\":\"Setup development environment\"}', NOW())");
$db->run("INSERT INTO activity_logs (user_id, team_id, action, entity_type, entity_id, metadata, created_at) VALUES (3, 1, 'task.completed', 'task', 1, '{\"title\":\"Setup development environment\"}', NOW())");
echo "  Created activity logs\n";

echo "\nSeeding audit logs...\n";
$db->run("INSERT INTO audit_logs (user_id, action, details, ip_address, created_at) VALUES (1, 'user.login', '{\"method\":\"password\"}', '127.0.0.1', NOW())");
$db->run("INSERT INTO audit_logs (user_id, action, details, ip_address, created_at) VALUES (1, 'team.created', '{\"team_id\":1}', '127.0.0.1', NOW())");
echo "  Created audit logs\n";

echo "\n=== Seeding Complete! ===\n\n";
echo "Sample credentials:\n";
echo "  owner@example.com / password123\n";
echo "  admin@example.com / password123\n";
echo "  member1@example.com / password123\n";
echo "  member2@example.com / password123\n";
echo "  member3@example.com / password123\n";