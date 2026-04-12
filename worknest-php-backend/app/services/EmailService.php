<?php

namespace App\Services;

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\SMTP;
use PHPMailer\PHPMailer\Exception;
use Core\DB;

class EmailService
{
    protected ?PHPMailer $mailer = null;
    protected array $config;

    public function __construct()
    {
        $this->config = require __DIR__ . '/../../config/mail.php';
    }

    protected function getMailer(): PHPMailer
    {
        if ($this->mailer === null) {
            $this->mailer = new PHPMailer(true);
            $this->mailer->isSMTP();
            $this->mailer->Host = $this->config['host'];
            $this->mailer->Port = $this->config['port'];
            $this->mailer->SMTPSecure = $this->config['encryption'] ?? '';
            $this->mailer->SMTPAuth = !empty($this->config['username']);
            $this->mailer->Username = $this->config['username'] ?? '';
            $this->mailer->Password = $this->config['password'] ?? '';
            $this->mailer->isHTML(true);
            $this->mailer->setFrom(
                $this->config['from']['address'],
                $this->config['from']['name']
            );
        }
        return $this->mailer;
    }

    public function send(array $to, string $subject, string $body, ?string $altBody = null): bool
    {
        try {
            $mailer = $this->getMailer();
            $mailer->clearAddresses();
            $mailer->Subject = $subject;
            $mailer->Body = $body;

            if ($altBody) {
                $mailer->AltBody = $altBody;
            }

            $mailer->addAddress($to['email'], $to['name'] ?? '');

            $result = $mailer->send();

            $this->logDelivery($to, $subject, $body, 'sent');

            return $result;
        } catch (Exception $e) {
            $this->logDelivery($to, $subject, $body, 'failed', $e->getMessage());
            return false;
        }
    }

    public function sendWelcomeEmail(string $email, string $name): bool
    {
        $subject = 'Welcome to WorkNest';
        $body = $this->getTemplate('welcome', ['name' => $name]);

        return $this->send(
            ['email' => $email, 'name' => $name],
            $subject,
            $body
        );
    }

    public function sendPasswordResetEmail(string $email, string $name, string $token): bool
    {
        $resetUrl = App::config('app.url') . "/api/auth/reset-password?token={$token}";

        $subject = 'Reset Your WorkNest Password';
        $body = $this->getTemplate('password_reset', [
            'name' => $name,
            'reset_url' => $resetUrl,
        ]);

        return $this->send(
            ['email' => $email, 'name' => $name],
            $subject,
            $body
        );
    }

    public function sendInvitationEmail(string $email, string $inviterName, string $teamName, string $token): bool
    {
        $acceptUrl = App::config('app.url') . "/api/invitations/accept?token={$token}";

        $subject = "You're invited to join {$teamName}";
        $body = $this->getTemplate('invitation', [
            'inviter_name' => $inviterName,
            'team_name' => $teamName,
            'accept_url' => $acceptUrl,
        ]);

        return $this->send(
            ['email' => $email],
            $subject,
            $body
        );
    }

    public function sendTaskAssignedEmail(string $email, string $assigneeName, string $taskTitle, string $teamName): bool
    {
        $subject = "You've been assigned a task: {$taskTitle}";
        $body = $this->getTemplate('task_assigned', [
            'assignee_name' => $assigneeName,
            'task_title' => $taskTitle,
            'team_name' => $teamName,
        ]);

        return $this->send(
            ['email' => $email, 'name' => $assigneeName],
            $subject,
            $body
        );
    }

    public function sendTaskCommentEmail(string $email, string $recipientName, string $taskTitle, string $commenterName, string $comment): bool
    {
        $subject = "New comment on task: {$taskTitle}";
        $body = $this->getTemplate('task_comment', [
            'recipient_name' => $recipientName,
            'task_title' => $taskTitle,
            'commenter_name' => $commenterName,
            'comment' => $comment,
        ]);

        return $this->send(
            ['email' => $email, 'name' => $recipientName],
            $subject,
            $body
        );
    }

    protected function getTemplate(string $template, array $data = []): string
    {
        $templates = [
            'welcome' => $this->welcomeTemplate(),
            'password_reset' => $this->passwordResetTemplate(),
            'invitation' => $this->invitationTemplate(),
            'task_assigned' => $this->taskAssignedTemplate(),
            'task_comment' => $this->taskCommentTemplate(),
        ];

        $template = $templates[$template] ?? '';
        foreach ($data as $key => $value) {
            $template = str_replace('{{' . $key . '}}', $value, $template);
        }

        return $template;
    }

    protected function welcomeTemplate(): string
    {
        return '
        <h1>Welcome to WorkNest, {{name}}!</h1>
        <p>Thank you for joining WorkNest. Start collaborating with your team today!</p>
        <p><a href="{{app_url}}">Get Started</a></p>
        ';
    }

    protected function passwordResetTemplate(): string
    {
        return '
        <h1>Reset Your Password</h1>
        <p>Hi {{name}},</p>
        <p>Click the button below to reset your password:</p>
        <p><a href="{{reset_url}}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you did not request this, please ignore this email.</p>
        ';
    }

    protected function invitationTemplate(): string
    {
        return '
        <h1>Team Invitation</h1>
        <p>Hi,</p>
        <p>{{inviter_name}} has invited you to join {{team_name}} on WorkNest.</p>
        <p><a href="{{accept_url}}">Accept Invitation</a></p>
        ';
    }

    protected function taskAssignedTemplate(): string
    {
        return '
        <h1>New Task Assigned</h1>
        <p>Hi {{assignee_name}},</p>
        <p>You have been assigned to the task "{{task_title}}" in {{team_name}}.</p>
        ';
    }

    protected function taskCommentTemplate(): string
    {
        return '
        <h1>New Comment</h1>
        <p>Hi {{recipient_name}},</p>
        <p>{{commenter_name}} commented on "{{task_title}}":</p>
        <blockquote>{{comment}}</blockquote>
        ';
    }

    protected function logDelivery(array $to, string $subject, string $body, string $status, ?string $error = null): void
    {
        $db = DB::getInstance();
        $db->run(
            "INSERT INTO email_deliveries (to_address, subject, body, status, error_message, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
            [$to['email'], $subject, $body, $status, $error]
        );
    }
}

class App
{
    public static function config(string $key, $default = null)
    {
        $config = require __DIR__ . '/../../config/app.php';
        $keys = explode('.', $key);
        $value = $config;

        foreach ($keys as $k) {
            if (!isset($value[$k])) {
                return $default;
            }
            $value = $value[$k];
        }

        return $value;
    }
}