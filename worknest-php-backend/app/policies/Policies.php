<?php

namespace App\Policies;

use App\Models\User;
use Core\Auth;

class UserPolicy
{
    public static function view(User $user): bool
    {
        return true;
    }

    public static function update(User $user, User $target): bool
    {
        return Auth::owns($target->id) || Auth::can('manage_settings');
    }

    public static function delete(User $user, User $target): bool
    {
        return Auth::can('manage_settings') && !Auth::owns($target->id);
    }
}

class TeamPolicy
{
    public static function view(int $teamId): bool
    {
        return Auth::isTeamMember($teamId);
    }

    public static function create(): bool
    {
        return Auth::can('create_team');
    }

    public static function update(int $teamId): bool
    {
        return Auth::canTeam('edit_team', $teamId);
    }

    public static function delete(int $teamId): bool
    {
        return Auth::canTeam('delete_team', $teamId);
    }

    public static function invite(int $teamId): bool
    {
        return Auth::canTeam('invite_member', $teamId);
    }
}

class MembershipPolicy
{
    public static function view(int $teamId): bool
    {
        return Auth::isTeamMember($teamId);
    }

    public static function update(int $teamId): bool
    {
        return Auth::canTeam('manage_members', $teamId);
    }

    public static function remove(int $teamId, int $userId): bool
    {
        if (!Auth::canTeam('remove_member', $teamId)) {
            return false;
        }
        $db = \Core\DB::getInstance();
        $membership = $db->fetch("SELECT role FROM memberships WHERE team_id = ? AND user_id = ?", [$teamId, $userId]);
        return !$membership || $membership['role'] !== 'team_owner';
    }
}

class InvitationPolicy
{
    public static function create(int $teamId): bool
    {
        return Auth::canTeam('invite_member', $teamId);
    }

    public static function revoke(int $invitationId): bool
    {
        $db = \Core\DB::getInstance();
        $invitation = $db->fetch("SELECT team_id FROM invitations WHERE id = ?", [$invitationId]);
        return $invitation && Auth::canTeam('invite_member', $invitation['team_id']);
    }

    public static function accept(string $token): bool
    {
        return !empty($token);
    }
}

class TaskPolicy
{
    public static function view(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::isTeamMember($task['team_id']);
    }

    public static function create(int $teamId): bool
    {
        return Auth::isTeamMember($teamId);
    }

    public static function update(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::canTeam('edit_task', $task['team_id']);
    }

    public static function delete(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::canTeam('delete_task', $task['team_id']);
    }

    public static function assign(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::canTeam('assign_task', $task['team_id']);
    }
}

class CommentPolicy
{
    public static function create(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::canTeam('comment_task', $task['team_id']);
    }

    public static function update(int $commentId): bool
    {
        $db = \Core\DB::getInstance();
        $comment = $db->fetch("SELECT user_id FROM comments WHERE id = ?", [$commentId]);
        return $comment && (Auth::owns($comment['user_id']) || Auth::can('manage_settings'));
    }

    public static function delete(int $commentId): bool
    {
        $db = \Core\DB::getInstance();
        $comment = $db->fetch("SELECT user_id FROM comments WHERE id = ?", [$commentId]);
        return $comment && (Auth::owns($comment['user_id']) || Auth::can('manage_settings'));
    }
}

class AttachmentPolicy
{
    public static function create(int $taskId): bool
    {
        $db = \Core\DB::getInstance();
        $task = $db->fetch("SELECT team_id FROM tasks WHERE id = ?", [$taskId]);
        return $task && Auth::canTeam('upload_attachment', $task['team_id']);
    }

    public static function delete(int $attachmentId): bool
    {
        $db = \Core\DB::getInstance();
        $attachment = $db->fetch("SELECT user_id FROM attachments WHERE id = ?", [$attachmentId]);
        return $attachment && (Auth::owns($attachment['user_id']) || Auth::can('manage_settings'));
    }
}

class NotificationPolicy
{
    public static function view(int $userId): bool
    {
        return Auth::owns($userId);
    }

    public static function markAsRead(int $notificationId): bool
    {
        $db = \Core\DB::getInstance();
        $notification = $db->fetch("SELECT user_id FROM notifications WHERE id = ?", [$notificationId]);
        return $notification && Auth::owns($notification['user_id']);
    }

    public static function updatePreferences(): bool
    {
        return Auth::check();
    }
}

class AuditLogPolicy
{
    public static function view(): bool
    {
        return Auth::can('view_audit_logs');
    }

    public static function viewForTeam(int $teamId): bool
    {
        return Auth::canTeam('view_audit_logs', $teamId);
    }
}

class ReportPolicy
{
    public static function view(int $teamId): bool
    {
        return Auth::isTeamMember($teamId) && Auth::canTeam('view_reports', $teamId);
    }

    public static function export(int $teamId): bool
    {
        return Auth::isTeamMember($teamId) && Auth::canTeam('export_reports', $teamId);
    }
}

class SettingsPolicy
{
    public static function view(): bool
    {
        return Auth::can('manage_settings');
    }

    public static function update(): bool
    {
        return Auth::can('manage_settings');
    }
}
