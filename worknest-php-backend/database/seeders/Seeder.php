<?php

require __DIR__ . '/../vendor/autoload.php';

use Core\DB;

class Seeder
{
    protected DB $db;
    protected array $users = [];
    protected array $teams = [];

    public function __construct()
    {
        $this->db = DB::getInstance();
    }

    public function run(): void
    {
        echo "Running seeders...\n";
        $this->seedUsers();
        $this->seedTeams();
        $this->seedTasks();
        $this->seedComments();
        $this->seedNotifications();
        echo "Seeders completed!\n";
    }

    protected function seedUsers(): void
    {
        $users = [
            [
                'name' => 'John Owner',
                'email' => 'owner@worknest.local',
                'password' => 'password123',
                'role' => 'owner',
            ],
            [
                'name' => 'Jane Admin',
                'email' => 'admin@worknest.local',
                'password' => 'password123',
                'role' => 'admin',
            ],
            [
                'name' => 'Bob Member',
                'email' => 'bob@worknest.local',
                'password' => 'password123',
                'role' => 'member',
            ],
            [
                'name' => 'Alice Member',
                'email' => 'alice@worknest.local',
                'password' => 'password123',
                'role' => 'member',
            ],
            [
                'name' => 'Charlie Member',
                'email' => 'charlie@worknest.local',
                'password' => 'password123',
                'role' => 'member',
            ],
        ];

        foreach ($users as $userData) {
            $passwordHash = password_hash($userData['password'], PASSWORD_BCRYPT);
            
            $this->db->run(
                "INSERT INTO users (email, password_hash, name, role, status, email_verified_at, created_at) 
                 VALUES (?, ?, ?, ?, 'active', NOW(), NOW())",
                [$userData['email'], $passwordHash, $userData['name'], $userData['role']]
            );

            $userId = $this->db->lastInsertId();
            $this->users[] = ['id' => $userId, 'email' => $userData['email'], 'name' => $userData['name']];

            $this->db->run(
                "INSERT INTO user_profiles (user_id, bio, created_at) VALUES (?, ?, NOW())",
                [$userId, "This is {$userData['name']}'s profile"]
            );

            echo "Created user: {$userData['email']}\n";
        }
    }

    protected function seedTeams(): void
    {
        $teams = [
            [
                'name' => 'Engineering Team',
                'slug' => 'engineering',
                'description' => 'The main engineering team',
            ],
            [
                'name' => 'Product Team',
                'slug' => 'product',
                'description' => 'Product development team',
            ],
        ];

        foreach ($teams as $teamData) {
            $this->db->run(
                "INSERT INTO teams (name, slug, description, owner_id, status, created_at) VALUES (?, ?, ?, ?, 'active', NOW())",
                [$teamData['name'], $teamData['slug'], $teamData['description'], $this->users[0]['id']]
            );

            $teamId = $this->db->lastInsertId();
            $this->teams[] = ['id' => $teamId, 'name' => $teamData['name']];

            foreach ($this->users as $index => $user) {
                $role = $index === 0 ? 'team_owner' : ($index === 1 ? 'team_admin' : 'team_member');
                $this->db->run(
                    "INSERT INTO memberships (user_id, team_id, role, status, created_at) VALUES (?, ?, ?, 'active', NOW())",
                    [$user['id'], $teamId, $role]
                );
            }

            $statuses = [
                ['name' => 'To Do', 'slug' => 'todo', 'color' => '#6b7280'],
                ['name' => 'In Progress', 'slug' => 'in_progress', 'color' => '#3b82f6'],
                ['name' => 'Done', 'slug' => 'done', 'color' => '#10b981'],
            ];

            foreach ($statuses as $status) {
                $this->db->run(
                    "INSERT INTO task_statuses (team_id, name, slug, color, position, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
                    [$teamId, $status['name'], $status['slug'], $status['color'], count($statuses)]
                );
            }

            echo "Created team: {$teamData['name']}\n";
        }
    }

    protected function seedTasks(): void
    {
        $tasks = [
            ['title' => 'Setup development environment', 'status' => 'done', 'priority' => 'high', 'assignee_index' => 0],
            ['title' => 'Design database schema', 'status' => 'done', 'priority' => 'high', 'assignee_index' => 1],
            ['title' => 'Implement authentication', 'status' => 'in_progress', 'priority' => 'high', 'assignee_index' => 2],
            ['title' => 'Create API endpoints', 'status' => 'todo', 'priority' => 'medium', 'assignee_index' => 3],
            ['title' => 'Write documentation', 'status' => 'todo', 'priority' => 'low', 'assignee_index' => 4],
        ];

        foreach ($this->teams as $team) {
            foreach ($tasks as $task) {
                $this->db->run(
                    "INSERT INTO tasks (team_id, title, status, priority, created_by, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
                    [$team['id'], $task['title'], $task['status'], $task['priority'], $this->users[$task['assignee_index']]['id']]
                );

                $taskId = $this->db->lastInsertId();

                $this->db->run(
                    "INSERT INTO task_assignees (task_id, user_id, assigned_by, created_at) VALUES (?, ?, ?, NOW())",
                    [$taskId, $this->users[$task['assignee_index']]['id'], $this->users[0]['id']]
                );

                if (rand(0, 1)) {
                    $this->db->run(
                        "INSERT INTO subtasks (task_id, title, is_completed, position, created_by, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
                        [$taskId, 'Subtask 1', rand(0, 1), 1, $this->users[0]['id']]
                    );
                }
            }
        }

        echo "Created tasks\n";
    }

    protected function seedComments(): void
    {
        $this->db->run(
            "INSERT INTO comments (task_id, user_id, content, created_at) VALUES (1, ?, 'Great progress on this task!', NOW())",
            [$this->users[0]['id']]
        );

        $this->db->run(
            "INSERT INTO comments (task_id, user_id, content, created_at) VALUES (2, ?, 'Need to review the schema', NOW())",
            [$this->users[1]['id']]
        );

        echo "Created comments\n";
    }

    protected function seedNotifications(): void
    {
        foreach ($this->users as $user) {
            $this->db->run(
                "INSERT INTO notifications (user_id, type, title, message, is_read, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
                [$user['id'], 'system', 'Welcome to WorkNest', 'Welcome to WorkNest! Start collaborating with your team.', 0]
            );
        }

        echo "Created notifications\n";
    }
}

$seeder = new Seeder();
$seeder->run();