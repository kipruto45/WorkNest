<?php

namespace App\Controllers;

use App\Models\User;
use Core\Controller;
use Core\DB;
use Core\Logger;
use Core\Upload;
use App\Services\EmailService;

class UserController extends Controller
{
    protected EmailService $emailService;

    public function __construct()
    {
        parent::__construct();
        $this->emailService = new EmailService();
    }

    public function me(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $user = $this->user();
        $profile = $user->getProfile();
        $notificationCount = $user->getNotificationCount();

        $this->success([
            'user' => $user->toArray(),
            'profile' => $profile ? $profile->toArray() : null,
            'notification_count' => $notificationCount,
        ]);
    }

    public function updateProfile(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'name' => 'min:2|max:255',
        ]);

        if ($validator->fails()) {
            $this->validationError('Update failed', $validator->errors());
            return;
        }

        $user = $this->user();

        if (isset($data['name'])) {
            $user->name = $data['name'];
        }

        $user->save();

        if (isset($data['bio']) || isset($data['phone']) || isset($data['company'])) {
            $this->updateUserProfile($user->id, $data);
        }

        Logger::logActivity($user->id, 'user.profile_updated', 'user', $user->id);

        $this->success(['user' => $user->toArray()], 'Profile updated');
    }

    public function uploadAvatar(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $file = $_FILES['avatar'] ?? null;

        if (!$file) {
            $this->error('No file uploaded');
            return;
        }

        $upload = new Upload([
            'path' => 'storage/uploads',
            'allowed_types' => ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            'max_size' => 2097152,
        ]);

        $result = $upload->uploadAvatar($file);

        if (!$result) {
            $this->error($upload->getError());
            return;
        }

        $user = $this->user();
        $user->avatar_url = $result['url'];
        $user->save();

        $this->success(['avatar_url' => $result['url']], 'Avatar uploaded');
    }

    public function getSettings(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $user = $this->user();
        $db = DB::getInstance();

        $settings = $db->fetchAll(
            "SELECT `key`, value FROM user_settings WHERE user_id = ?",
            [$user->id]
        );

        $settingsArray = [];
        foreach ($settings as $setting) {
            $settingsArray[$setting['key']] = $setting['value'];
        }

        $this->success(['settings' => $settingsArray]);
    }

    public function updateSettings(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $user = $this->user();

        foreach ($data as $key => $value) {
            $user->setSetting($key, $value);
        }

        $this->success([], 'Settings updated');
    }

    public function search(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $query = $this->input('q', '');

        if (strlen($query) < 2) {
            $this->success(['users' => []]);
            return;
        }

        $db = DB::getInstance();
        $users = $db->fetchAll(
            "SELECT id, name, email, avatar_url FROM users 
             WHERE (name LIKE ? OR email LIKE ?) AND status = 'active'
             LIMIT 10",
            ["%{$query}%", "%{$query}%"]
        );

        $this->success(['users' => $users]);
    }

    protected function updateUserProfile(int $userId, array $data): void
    {
        $db = DB::getInstance();

        $profileData = array_intersect_key($data, array_flip(['bio', 'phone', 'company', 'job_title', 'location', 'website', 'timezone', 'locale']));

        if (empty($profileData)) {
            return;
        }

        $profileData['updated_at'] = date('Y-m-d H:i:s');

        $existing = $db->fetch("SELECT id FROM user_profiles WHERE user_id = ?", [$userId]);

        if ($existing) {
            $sets = implode(' = ?, ', array_keys($profileData)) . ' = ?';
            $db->run(
                "UPDATE user_profiles SET {$sets} WHERE user_id = ?",
                array_merge(array_values($profileData), [$userId])
            );
        } else {
            $profileData['user_id'] = $userId;
            $profileData['created_at'] = date('Y-m-d H:i:s');

            $columns = implode(', ', array_keys($profileData));
            $placeholders = implode(', ', array_fill(0, count($profileData), '?'));

            $db->run(
                "INSERT INTO user_profiles ({$columns}) VALUES ({$placeholders})",
                array_values($profileData)
            );
        }
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