<?php

namespace App\Controllers;

use App\Models\Notification as NotificationModel;
use Core\Controller;
use Core\Auth;

class NotificationController extends Controller
{
    public function index(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $notifications = NotificationModel::findByUserId($this->user()->id);
        $this->success(['notifications' => $notifications]);
    }

    public function unreadCount(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $count = NotificationModel::getUnreadCount($this->user()->id);
        $this->success(['count' => $count]);
    }

    public function markAsRead(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $notification = NotificationModel::find($id);
        if ($notification && $notification->user_id === $this->user()->id) {
            $notification->markAsRead();
        }

        $this->success([], 'Marked as read');
    }

    public function markAllAsRead(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        NotificationModel::markAllAsRead($this->user()->id);
        $this->success([], 'All marked as read');
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