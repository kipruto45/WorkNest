<?php

namespace App\Controllers;

use App\Models\Attachment as AttachmentModel;
use Core\Controller;
use Core\DB;
use Core\Auth;
use Core\Upload;
use Core\Response;

class AttachmentController extends Controller
{
    public function index(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $attachments = AttachmentModel::findByTaskId($id);
        $this->success(['attachments' => $attachments]);
    }

    public function upload(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $file = $_FILES['file'] ?? null;

        if (!$file) {
            $this->error('No file uploaded');
            return;
        }

        $upload = new Upload([
            'path' => 'storage/uploads',
            'allowed_types' => ['application/pdf', 'image/jpeg', 'image/png', 'text/plain', 'application/msword'],
            'max_size' => 10485760,
        ]);

        $result = $upload->uploadAttachment($file);

        if (!$result) {
            $this->error($upload->getError());
            return;
        }

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO attachments (team_id, task_id, user_id, filename, original_name, mime_type, size, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())",
            [1, $id, $this->user()->id, $result['filename'], $result['original_name'], $result['mime_type'], $result['size'], $result['path'], $result['url']]
        );

        $attachmentId = $db->lastInsertId();

        $this->success(['attachment_id' => $attachmentId, 'url' => $result['url']], 'File uploaded');
    }

    public function delete(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $attachment = AttachmentModel::find($id);

        if (!$attachment) {
            $this->notFound('Attachment not found');
            return;
        }

        $attachment->softDelete();

        $this->success([], 'File deleted');
    }

    public function download(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $attachment = AttachmentModel::find($id);

        if (!$attachment) {
            $this->notFound('Attachment not found');
            return;
        }

        Response::download($attachment->path, $attachment->original_name);
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