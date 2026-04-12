<?php

namespace App\ViewModels;

class DashboardViewModel
{
    public int $totalTasks = 0;
    public int $completedTasks = 0;
    public int $inProgressTasks = 0;
    public int $overdueTasks = 0;
    public int $dueSoonTasks = 0;
    public int $totalTeams = 0;
    public int $totalMembers = 0;
    public int $unreadNotifications = 0;
    public array $tasksByStatus = [];
    public array $tasksByPriority = [];
    public array $recentActivity = [];
    public array $topMembers = [];

    public static function fromData(array $stats): self
    {
        $vm = new self();
        $vm->totalTasks = $stats['total_tasks'] ?? 0;
        $vm->completedTasks = $stats['completed_tasks'] ?? 0;
        $vm->inProgressTasks = $stats['in_progress_tasks'] ?? 0;
        $vm->overdueTasks = $stats['overdue_tasks'] ?? 0;
        $vm->dueSoonTasks = $stats['due_soon_tasks'] ?? 0;
        $vm->totalTeams = $stats['total_teams'] ?? 0;
        $vm->totalMembers = $stats['total_members'] ?? 0;
        $vm->unreadNotifications = $stats['unread_notifications'] ?? 0;
        return $vm;
    }

    public function toArray(): array
    {
        return [
            'total_tasks' => $this->totalTasks,
            'completed_tasks' => $this->completedTasks,
            'in_progress_tasks' => $this->inProgressTasks,
            'overdue_tasks' => $this->overdueTasks,
            'due_soon_tasks' => $this->dueSoonTasks,
            'total_teams' => $this->totalTeams,
            'total_members' => $this->totalMembers,
            'unread_notifications' => $this->unreadNotifications,
            'tasks_by_status' => $this->tasksByStatus,
            'tasks_by_priority' => $this->tasksByPriority,
            'recent_activity' => $this->recentActivity,
            'top_members' => $this->topMembers,
        ];
    }
}

class TeamViewModel
{
    public int $id;
    public string $name;
    public string $slug;
    public ?string $description;
    public int $ownerId;
    public string $status;
    public array $members = [];
    public array $invitations = [];
    public array $stats = [];

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'slug' => $this->slug,
            'description' => $this->description,
            'owner_id' => $this->ownerId,
            'status' => $this->status,
            'members' => $this->members,
            'invitations' => $this->invitations,
            'stats' => $this->stats,
        ];
    }
}

class TaskViewModel
{
    public int $id;
    public int $teamId;
    public string $title;
    public ?string $description;
    public string $status;
    public string $priority;
    public ?string $dueDate;
    public ?string $dueTime;
    public array $assignees = [];
    public array $watchers = [];
    public array $subtasks = [];
    public array $labels = [];
    public array $checklists = [];
    public array $comments = [];
    public array $attachments = [];
    public float $timeLogged = 0;

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'team_id' => $this->teamId,
            'title' => $this->title,
            'description' => $this->description,
            'status' => $this->status,
            'priority' => $this->priority,
            'due_date' => $this->dueDate,
            'due_time' => $this->dueTime,
            'assignees' => $this->assignees,
            'watchers' => $this->watchers,
            'subtasks' => $this->subtasks,
            'labels' => $this->labels,
            'checklists' => $this->checklists,
            'comments_count' => count($this->comments),
            'attachments_count' => count($this->attachments),
            'time_logged' => $this->timeLogged,
        ];
    }
}

class NotificationViewModel
{
    public int $id;
    public string $type;
    public string $title;
    public ?string $message;
    public ?string $link;
    public bool $isRead;
    public ?string $createdAt;
    public array $data = [];

    public static function fromNotification($notification): self
    {
        $vm = new self();
        $vm->id = $notification->id;
        $vm->type = $notification->type;
        $vm->title = $notification->title;
        $vm->message = $notification->message ?? null;
        $vm->link = $notification->link ?? null;
        $vm->isRead = (bool) $notification->is_read;
        $vm->createdAt = $notification->created_at;
        $vm->data = is_string($notification->data) ? json_decode($notification->data, true) : ($notification->data ?? []);
        return $vm;
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'type' => $this->type,
            'title' => $this->title,
            'message' => $this->message,
            'link' => $this->link,
            'is_read' => $this->isRead,
            'created_at' => $this->createdAt,
            'data' => $this->data,
        ];
    }
}

class AuditLogViewModel
{
    public int $id;
    public ?int $userId;
    public ?string $userName;
    public string $action;
    public ?string $entityType;
    public ?int $entityId;
    public array $details = [];
    public ?string $ipAddress;
    public string $createdAt;

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'user_id' => $this->userId,
            'user_name' => $this->userName,
            'action' => $this->action,
            'entity_type' => $this->entityType,
            'entity_id' => $this->entityId,
            'details' => $this->details,
            'ip_address' => $this->ipAddress,
            'created_at' => $this->createdAt,
        ];
    }
}

class ReportViewModel
{
    public string $type;
    public string $format;
    public int $teamId;
    public array $data = [];
    public int $totalRows = 0;
    public ?string $filePath;
    public string $generatedAt;

    public function toArray(): array
    {
        return [
            'type' => $this->type,
            'format' => $this->format,
            'team_id' => $this->teamId,
            'total_rows' => $this->totalRows,
            'file_path' => $this->filePath,
            'generated_at' => $this->generatedAt,
        ];
    }
}
