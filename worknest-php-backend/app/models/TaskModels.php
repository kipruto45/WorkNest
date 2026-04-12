<?php

namespace App\Models;

use Core\Model;

class TeamSetting extends Model
{
    protected string $table = 'team_settings';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'key', 'value'];
}

class MembershipRole extends Model
{
    protected string $table = 'membership_roles';
    protected string $primaryKey = 'id';
    protected array $fillable = ['membership_id', 'role', 'changed_by'];
}

class InvitationToken extends Model
{
    protected string $table = 'invitation_tokens';
    protected string $primaryKey = 'id';
    protected array $fillable = ['invitation_id', 'token', 'expires_at', 'used_at'];
}

class TaskList extends Model
{
    protected string $table = 'task_lists';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'name', 'description', 'position', 'created_by'];
}

class TaskStatus extends Model
{
    protected string $table = 'task_statuses';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'name', 'slug', 'color', 'position', 'is_default'];
}

class TaskPriority extends Model
{
    protected string $table = 'task_priorities';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'name', 'slug', 'color', 'position', 'is_default'];
}

class TaskAssignee extends Model
{
    protected string $table = 'task_assignees';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'user_id', 'assigned_by'];
}

class TaskWatcher extends Model
{
    protected string $table = 'task_watchers';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'user_id'];
}

class TaskLabel extends Model
{
    protected string $table = 'task_labels';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'name', 'color', 'created_by'];
}

class TaskLabelLink extends Model
{
    protected string $table = 'task_label_links';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'label_id'];
}

class TaskChecklist extends Model
{
    protected string $table = 'task_checklists';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'title', 'position', 'created_by'];
}

class TaskChecklistItem extends Model
{
    protected string $table = 'task_checklist_items';
    protected string $primaryKey = 'id';
    protected array $fillable = ['checklist_id', 'title', 'is_completed', 'position', 'created_by'];
}

class TaskDueDate extends Model
{
    protected string $table = 'task_due_dates';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'due_date', 'due_time', 'reminder_at'];
}

class TaskTimeLog extends Model
{
    protected string $table = 'task_time_logs';
    protected string $primaryKey = 'id';
    protected array $fillable = ['task_id', 'user_id', 'hours', 'description', 'logged_at'];
}