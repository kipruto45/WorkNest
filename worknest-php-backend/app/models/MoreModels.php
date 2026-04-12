<?php

namespace App\Models;

use Core\Model;
use Core\DB;

class CommentMention extends Model
{
    protected string $table = 'comment_mentions';
    protected string $primaryKey = 'id';
    protected array $fillable = ['comment_id', 'user_id'];
}

class CommentReaction extends Model
{
    protected string $table = 'comment_reactions';
    protected string $primaryKey = 'id';
    protected array $fillable = ['comment_id', 'user_id', 'emoji'];
}

class AttachmentVersion extends Model
{
    protected string $table = 'attachment_versions';
    protected string $primaryKey = 'id';
    protected array $fillable = ['attachment_id', 'version', 'filename', 'size', 'created_by'];
}

class AttachmentLink extends Model
{
    protected string $table = 'attachment_links';
    protected string $primaryKey = 'id';
    protected array $fillable = ['attachment_id', 'entity_type', 'entity_id'];
}

class NotificationRead extends Model
{
    protected string $table = 'notification_reads';
    protected string $primaryKey = 'id';
    protected array $fillable = ['notification_id', 'user_id', 'read_at'];
}

class NotificationPreference extends Model
{
    protected string $table = 'notification_preferences';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'type', 'is_enabled', 'channel'];
}

class DashboardSnapshot extends Model
{
    protected string $table = 'dashboard_snapshots';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'user_id', 'data'];
    protected array $casts = ['data' => 'json'];
}

class WidgetPreference extends Model
{
    protected string $table = 'widget_preferences';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'team_id', 'widget', 'settings', 'position', 'is_visible'];
    protected array $casts = ['settings' => 'json'];
}

class ReportExport extends Model
{
    protected string $table = 'report_exports';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'user_id', 'type', 'format', 'filename', 'path', 'rows_count', 'status'];
}

class IntegrationProvider extends Model
{
    protected string $table = 'integration_providers';
    protected string $primaryKey = 'id';
    protected array $fillable = ['name', 'slug', 'description', 'is_enabled', 'settings'];
    protected array $casts = ['settings' => 'json'];
}

class IntegrationSetting extends Model
{
    protected string $table = 'integration_settings';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'provider_id', 'key', 'value', 'is_encrypted'];
}

class OAuthConnection extends Model
{
    protected string $table = 'oauth_connections';
    protected string $primaryKey = 'id';
    protected array $fillable = ['user_id', 'provider_id', 'provider_user_id', 'access_token', 'refresh_token', 'expires_at', 'scope'];
}

class WebhookLog extends Model
{
    protected string $table = 'webhook_logs';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'webhook_id', 'url', 'event', 'payload', 'response_status', 'response_body', 'status'];
    protected array $casts = ['payload' => 'json'];
}

class EmailDelivery extends Model
{
    protected string $table = 'email_deliveries';
    protected string $primaryKey = 'id';
    protected array $fillable = ['team_id', 'user_id', 'to_address', 'subject', 'body', 'status', 'error_message', 'sent_at'];
}

class StorageProvider extends Model
{
    protected string $table = 'storage_providers';
    protected string $primaryKey = 'id';
    protected array $fillable = ['name', 'slug', 'driver', 'is_default', 'settings'];
    protected array $casts = ['settings' => 'json'];
}

class Setting extends Model
{
    protected string $table = 'settings';
    protected string $primaryKey = 'id';
    protected array $fillable = ['key', 'value', 'value_type', 'is_encrypted', 'description'];
}

class JobLog extends Model
{
    protected string $table = 'jobs_log';
    protected string $primaryKey = 'id';
    protected array $fillable = ['job', 'payload', 'status', 'attempts', 'max_attempts', 'error_message', 'started_at', 'completed_at'];
    protected array $casts = ['payload' => 'json'];
}

class HealthCheck extends Model
{
    protected string $table = 'health_checks';
    protected string $primaryKey = 'id';
    protected array $fillable = ['check_name', 'status', 'message', 'response_time', 'run_at'];
}