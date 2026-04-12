<?php

namespace App\Controllers;

use App\Models\Task;
use App\Models\Subtask as SubtaskModel;
use Core\Controller;
use Core\DB;
use Core\Auth;
use Core\Logger;
use Core\Upload;
use App\Services\EmailService;

class TaskController extends Controller
{
    protected EmailService $emailService;

    public function __construct()
    {
        parent::__construct();
        $this->emailService = new EmailService();
    }

    public function index(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teamId = $this->input('team_id');
        if (!$teamId) {
            $this->error('Team ID is required');
            return;
        }

        $db = DB::getInstance();
        $tasks = $db->fetchAll(
            "SELECT * FROM tasks WHERE team_id = ? AND deleted_at IS NULL ORDER BY position",
            [$teamId]
        );

        $this->success(['tasks' => $tasks]);
    }

    public function create(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $validator = $this->validate($data, [
            'title' => 'required|min:1|max:500',
            'team_id' => 'required',
        ]);

        if ($validator->fails()) {
            $this->validationError('Task creation failed', $validator->errors());
            return;
        }

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO tasks (team_id, title, description, priority, status, created_by, created_at) VALUES (?, ?, ?, ?, 'todo', ?, NOW())",
            [$data['team_id'], $data['title'], $data['description'] ?? null, $data['priority'] ?? 'medium', $this->user()->id]
        );

        $taskId = $db->lastInsertId();
        Logger::logActivity($this->user()->id, $data['team_id'], 'task.created', 'task', $taskId);

        $this->success(['task_id' => $taskId], 'Task created');
    }

    public function show(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $this->success([
            'task' => $task->toArray(),
            'assignees' => $task->getAssignees(),
            'subtasks' => $task->getSubtasks(),
            'comments' => $task->getComments(),
            'attachments' => $task->getAttachments(),
        ]);
    }

    public function update(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $data = $this->all();
        
        if (isset($data['title'])) {
            $task->title = $data['title'];
        }

        if (isset($data['description'])) {
            $task->description = $data['description'];
        }

        if (isset($data['priority'])) {
            $task->priority = $data['priority'];
        }

        $task->save();

        $this->success(['task' => $task->toArray()], 'Task updated');
    }

    public function delete(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $task->softDelete();

        $this->success([], 'Task deleted');
    }

    public function updateStatus(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $validator = $this->validate($data, ['status' => 'required|in:todo,in_progress,in_review,done,archived']);

        if ($validator->fails()) {
            $this->error('Invalid status');
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $task->updateStatus($data['status']);

        $this->success([], 'Status updated');
    }

    public function assign(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $validator = $this->validate($data, ['user_id' => 'required']);

        if ($validator->fails()) {
            $this->error('User ID is required');
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $task->assignTo($data['user_id'], $this->user()->id);

        $this->success([], 'Task assigned');
    }

    public function addSubtask(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $validator = $this->validate($data, ['title' => 'required']);

        if ($validator->fails()) {
            $this->error('Title is required');
            return;
        }

        $task = Task::find($id);
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO subtasks (task_id, title, created_by, created_at) VALUES (?, ?, ?, NOW())",
            [$id, $data['title'], $this->user()->id]
        );

        $this->success([], 'Subtask added');
    }

    public function addTimeLog(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $task = Task::find($id);
        
        if (!$task) {
            $this->notFound('Task not found');
            return;
        }

        $task->addTimeLog($this->user()->id, $data['hours'] ?? 0, $data['description'] ?? null);

        $this->success([], 'Time logged');
    }

    protected function validate(array $data, array $rules)
    {
        $validator = new \Core\Validator($data, $rules);
        $validator->validate();
        return $validator;
    }

    protected function user()
    {
        return Auth::user();
    }

    protected function authenticate(): bool
    {
        return Auth::check();
    }
}