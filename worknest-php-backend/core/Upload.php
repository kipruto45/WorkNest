<?php

namespace Core;

class Upload
{
    protected string $path = 'storage/uploads';
    protected array $allowedTypes = [];
    protected int $maxSize = 10485760;
    protected string $error = '';

    public function __construct(array $config = [])
    {
        if (isset($config['path'])) {
            $this->path = $config['path'];
        }

        if (isset($config['allowed_types'])) {
            $this->allowedTypes = $config['allowed_types'];
        }

        if (isset($config['max_size'])) {
            $this->maxSize = $config['max_size'];
        }
    }

    public function upload(array $file, string $subdirectory = ''): ?array
    {
        if (!isset($file['tmp_name']) || !is_uploaded_file($file['tmp_name'])) {
            $this->error = 'No file uploaded';
            return null;
        }

        if ($file['error'] !== UPLOAD_ERR_OK) {
            $this->error = $this->getErrorMessage($file['error']);
            return null;
        }

        if ($file['size'] > $this->maxSize) {
            $this->error = 'File size exceeds maximum allowed';
            return null;
        }

        if (!empty($this->allowedTypes)) {
            $mimeType = $this->getMimeType($file['tmp_name']);
            if (!in_array($mimeType, $this->allowedTypes)) {
                $this->error = 'File type not allowed';
                return null;
            }
        }

        $directory = $this->path . ($subdirectory ? '/' . $subdirectory : '');
        if (!is_dir($directory)) {
            mkdir($directory, 0755, true);
        }

        $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
        $filename = $this->generateFilename($extension);
        $destination = $directory . '/' . $filename;

        if (!move_uploaded_file($file['tmp_name'], $destination)) {
            $this->error = 'Failed to move uploaded file';
            return null;
        }

        return [
            'filename' => $filename,
            'original_name' => $file['name'],
            'path' => $destination,
            'url' => '/storage/' . $subdirectory . '/' . $filename,
            'size' => $file['size'],
            'mime_type' => $this->getMimeType($destination),
            'extension' => $extension,
        ];
    }

    public function uploadAvatar(array $file): ?array
    {
        return $this->upload($file, 'avatars');
    }

    public function uploadAttachment(array $file): ?array
    {
        return $this->upload($file, 'attachments');
    }

    public function delete(string $path): bool
    {
        if (file_exists($path)) {
            return unlink($path);
        }
        return false;
    }

    public function exists(string $path): bool
    {
        return file_exists($path);
    }

    public function getError(): string
    {
        return $this->error;
    }

    public function getMimeType(string $filePath): string
    {
        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mimeType = finfo_file($finfo, $filePath);
        finfo_close($finfo);
        return $mimeType;
    }

    protected function generateFilename(string $extension): string
    {
        return date('YmdHis') . '_' . bin2hex(random_bytes(8)) . '.' . $extension;
    }

    protected function getErrorMessage(int $errorCode): string
    {
        $messages = [
            UPLOAD_ERR_INI_SIZE => 'File exceeds upload_max_filesize',
            UPLOAD_ERR_FORM_SIZE => 'File exceeds form MAX_FILE_SIZE',
            UPLOAD_ERR_PARTIAL => 'File was only partially uploaded',
            UPLOAD_ERR_NO_FILE => 'No file was uploaded',
            UPLOAD_ERR_NO_TMP_DIR => 'Missing temp folder',
            UPLOAD_ERR_CANT_WRITE => 'Failed to write to disk',
            UPLOAD_ERR_EXTENSION => 'Upload stopped by extension',
        ];
        return $messages[$errorCode] ?? 'Unknown upload error';
    }

    public static function isImage(string $mimeType): bool
    {
        return in_array($mimeType, [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
        ]);
    }

    public static function isPdf(string $mimeType): bool
    {
        return $mimeType === 'application/pdf';
    }
}