<?php

namespace App\Transformers;

class UserTransformer
{
    public static function transform($user): array
    {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'avatar_url' => $user->avatar_url ?? null,
            'role' => $user->role,
            'status' => $user->status,
            'email_verified_at' => $user->email_verified_at,
            'created_at' => $user->created_at,
        ];
    }

    public static function transformWithProfile($user, $profile = null): array
    {
        $data = self::transform($user);
        if ($profile) {
            $data['profile'] = [
                'bio' => $profile->bio ?? null,
                'phone' => $profile->phone ?? null,
                'company' => $profile->company ?? null,
                'job_title' => $profile->job_title ?? null,
                'location' => $profile->location ?? null,
                'website' => $profile->website ?? null,
                'timezone' => $profile->timezone ?? null,
            ];
        }
        return $data;
    }
}

class TeamTransformer
{
    public static function transform($team): array
    {
        return [
            'id' => $team->id,
            'name' => $team->name,
            'slug' => $team->slug,
            'description' => $team->description ?? null,
            'logo_url' => $team->logo_url ?? null,
            'owner_id' => $team->owner_id,
            'status' => $team->status,
            'created_at' => $team->created_at,
        ];
    }

    public static function transformWithStats($team, $stats = []): array
    {
        $data = self::transform($team);
        $data['stats'] = $stats;
        return $data;
    }
}

class MembershipTransformer
{
    public static function transform($membership, $user = null): array
    {
        $data = [
            'id' => $membership->id,
            'user_id' => $membership->user_id,
            'team_id' => $membership->team_id,
            'role' => $membership->role,
            'status' => $membership->status,
            'created_at' => $membership->created_at,
        ];
        
        if ($user) {
            $data['user'] = UserTransformer::transform($user);
        }
        
        return $data;
    }
}

class InvitationTransformer
{
    public static function transform($invitation): array
    {
        return [
            'id' => $invitation->id,
            'email' => $invitation->email,
            'team_id' => $invitation->team_id,
            'role' => $invitation->role,
            'invited_by' => $invitation->invited_by,
            'status' => $invitation->status,
            'expires_at' => $invitation->expires_at,
            'accepted_at' => $invitation->accepted_at,
            'created_at' => $invitation->created_at,
        ];
    }
}

class TaskTransformer
{
    public static function transform($task): array
    {
        return [
            'id' => $task->id,
            'team_id' => $task->team_id,
            'task_list_id' => $task->task_list_id ?? null,
            'status_id' => $task->status_id ?? null,
            'title' => $task->title,
            'description' => $task->description ?? null,
            'priority' => $task->priority,
            'status' => $task->status,
            'due_date' => $task->due_date ?? null,
            'due_time' => $task->due_time ?? null,
            'position' => $task->position,
            'created_by' => $task->created_by,
            'completed_at' => $task->completed_at ?? null,
            'created_at' => $task->created_at,
            'updated_at' => $task->updated_at,
        ];
    }

    public static function transformWithDetails($task, $assignees = [], $subtasks = [], $labels = []): array
    {
        $data = self::transform($task);
        $data['assignees'] = array_map(fn($a) => UserTransformer::transform((object)$a), $assignees);
        $data['subtasks'] = $subtasks;
        $data['labels'] = $labels;
        return $data;
    }
}

class CommentTransformer
{
    public static function transform($comment): array
    {
        return [
            'id' => $comment->id,
            'task_id' => $comment->task_id,
            'user_id' => $comment->user_id,
            'user_name' => $comment->user_name ?? null,
            'avatar_url' => $comment->avatar_url ?? null,
            'parent_id' => $comment->parent_id ?? null,
            'content' => $comment->content,
            'is_edited' => (bool) $comment->is_edited,
            'created_at' => $comment->created_at,
            'updated_at' => $comment->updated_at ?? null,
        ];
    }
}

class AttachmentTransformer
{
    public static function transform($attachment): array
    {
        return [
            'id' => $attachment->id,
            'task_id' => $attachment->task_id ?? null,
            'user_id' => $attachment->user_id,
            'filename' => $attachment->filename,
            'original_name' => $attachment->original_name,
            'mime_type' => $attachment->mime_type,
            'size' => $attachment->size,
            'url' => $attachment->url,
            'version' => $attachment->version,
            'created_at' => $attachment->created_at,
        ];
    }
}

class NotificationTransformer
{
    public static function transform($notification): array
    {
        return [
            'id' => $notification->id,
            'type' => $notification->type,
            'title' => $notification->title,
            'message' => $notification->message ?? null,
            'data' => is_string($notification->data) ? json_decode($notification->data, true) : $notification->data,
            'link' => $notification->link ?? null,
            'is_read' => (bool) $notification->is_read,
            'read_at' => $notification->read_at ?? null,
            'created_at' => $notification->created_at,
        ];
    }
}

class DashboardTransformer
{
    public static function transform($stats): array
    {
        return [
            'total_tasks' => $stats['total_tasks'] ?? 0,
            'completed_tasks' => $stats['completed_tasks'] ?? 0,
            'in_progress_tasks' => $stats['in_progress_tasks'] ?? 0,
            'overdue_tasks' => $stats['overdue_tasks'] ?? 0,
            'due_soon_tasks' => $stats['due_soon_tasks'] ?? 0,
            'total_teams' => $stats['total_teams'] ?? 0,
            'total_members' => $stats['total_members'] ?? 0,
            'unread_notifications' => $stats['unread_notifications'] ?? 0,
        ];
    }
}

class AuditLogTransformer
{
    public static function transform($log): array
    {
        return [
            'id' => $log->id,
            'user_id' => $log->user_id,
            'user_name' => $log->user_name ?? null,
            'action' => $log->action,
            'entity_type' => $log->entity_type ?? null,
            'entity_id' => $log->entity_id ?? null,
            'details' => is_string($log->details) ? json_decode($log->details, true) : $log->details,
            'ip_address' => $log->ip_address ?? null,
            'created_at' => $log->created_at,
        ];
    }
}

class ReportTransformer
{
    public static function transformTaskReport($tasks): array
    {
        return [
            'data' => array_map(fn($t) => TaskTransformer::transform((object)$t), $tasks),
            'total' => count($tasks),
            'by_status' => array_count_values(array_column($tasks, 'status')),
            'by_priority' => array_count_values(array_column($tasks, 'priority')),
        ];
    }

    public static function transformActivityReport($activities): array
    {
        return [
            'data' => $activities,
            'total' => count($activities),
        ];
    }
}
