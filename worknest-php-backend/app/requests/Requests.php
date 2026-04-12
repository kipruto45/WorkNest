<?php

namespace App\Requests;

use Core\Validator;

class LoginRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'email' => 'required|email',
            'password' => 'required'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class RegisterRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'name' => 'required|min:2|max:255',
            'email' => 'required|email|unique:users',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class ForgotPasswordRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'email' => 'required|email'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class ResetPasswordRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'token' => 'required',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class ChangePasswordRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'current_password' => 'required',
            'password' => 'required|min:8',
            'password_confirm' => 'required|same:password'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class VerifyEmailRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'token' => 'required'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateProfileRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'name' => 'min:2|max:255',
            'bio' => 'max:1000',
            'phone' => 'max:50',
            'company' => 'max:255',
            'job_title' => 'max:255',
            'location' => 'max:255',
            'website' => 'url'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class CreateTeamRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'name' => 'required|min:2|max:255',
            'description' => 'max:1000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateTeamRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'name' => 'min:2|max:255',
            'description' => 'max:1000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class InviteMemberRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'email' => 'required|email',
            'role' => 'in:team_owner,team_admin,team_member,guest'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateMembershipRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'role' => 'required|in:team_owner,team_admin,team_member,guest'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class CreateTaskRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'required|min:1|max:500',
            'description' => 'max:5000',
            'priority' => 'in:low,medium,high,urgent',
            'due_date' => 'date'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateTaskRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'min:1|max:500',
            'description' => 'max:5000',
            'priority' => 'in:low,medium,high,urgent',
            'status' => 'in:todo,in_progress,in_review,done,archived',
            'due_date' => 'date'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class AssignTaskRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'user_id' => 'required|exists:users,id'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class ChangeTaskStatusRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'status' => 'required|in:todo,in_progress,in_review,done,archived'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class CreateSubtaskRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'required|min:1|max:500'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateSubtaskRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'min:1|max:500',
            'is_completed' => 'in:0,1'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class CreateChecklistRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'required|min:1|max:500'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateChecklistItemRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'title' => 'min:1|max:500',
            'is_completed' => 'in:0,1'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class CreateCommentRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'content' => 'required|min:1|max:5000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UpdateCommentRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'content' => 'required|min:1|max:5000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UploadAttachmentRequest
{
    public static function validate(array $data, array $file): array
    {
        $errors = [];
        
        if (empty($file) || $file['error'] !== UPLOAD_ERR_OK) {
            $errors['file'] = ['No file uploaded'];
            return $errors;
        }
        
        $maxSize = 10 * 1024 * 1024;
        if ($file['size'] > $maxSize) {
            $errors['file'] = ['File size exceeds 10MB'];
        }
        
        $allowed = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'xlsx', 'csv', 'zip'];
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $allowed)) {
            $errors['file'] = ['File type not allowed'];
        }
        
        return $errors;
    }
}

class NotificationPreferenceRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'type' => 'required',
            'is_enabled' => 'in:0,1',
            'channel' => 'in:email,in_app,both'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class ReportExportRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'team_id' => 'required',
            'format' => 'in:csv,pdf',
            'type' => 'in:tasks,activity,productivity'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class TeamSettingRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'key' => 'required',
            'value' => 'max:5000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}

class UserSettingRequest
{
    public static function validate(array $data): array
    {
        $validator = new Validator($data, [
            'key' => 'required',
            'value' => 'max:5000'
        ]);
        
        $validator->validate();
        return $validator->fails() ? $validator->errors() : [];
    }
}
