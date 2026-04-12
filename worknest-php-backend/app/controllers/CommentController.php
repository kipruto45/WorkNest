<?php

namespace App\Controllers;

use App\Models\Comment as CommentModel;
use Core\Controller;
use Core\DB;
use Core\Auth;

class CommentController extends Controller
{
    public function index(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $comments = CommentModel::findByTaskId($id);
        $this->success(['comments' => $comments]);
    }

    public function create(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $validator = $this->validate($data, ['content' => 'required']);

        if ($validator->fails()) {
            $this->error('Content is required');
            return;
        }

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO comments (task_id, user_id, content, created_at) VALUES (?, ?, ?, NOW())",
            [$id, $this->user()->id, $data['content']]
        );

        $commentId = $db->lastInsertId();
        $this->success(['comment_id' => $commentId], 'Comment added');
    }

    public function update(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $db = DB::getInstance();

        $comment = $db->fetch("SELECT * FROM comments WHERE id = ?", [$id]);
        if (!$comment || $comment['user_id'] !== $this->user()->id) {
            $this->forbidden();
            return;
        }

        $db->run("UPDATE comments SET content = ?, is_edited = 1, updated_at = NOW() WHERE id = ?", [$data['content'], $id]);

        $this->success([], 'Comment updated');
    }

    public function delete(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $db = DB::getInstance();
        $comment = $db->fetch("SELECT * FROM comments WHERE id = ?", [$id]);
        if (!$comment || $comment['user_id'] !== $this->user()->id) {
            $this->forbidden();
            return;
        }

        $db->run("UPDATE comments SET deleted_at = NOW() WHERE id = ?", [$id]);
        $this->success([], 'Comment deleted');
    }

    public function addReaction(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $comment = CommentModel::find($id);
        
        if ($comment) {
            $comment->addReaction($this->user()->id, $data['emoji'] ?? '👍');
        }

        $this->success([], 'Reaction added');
    }

    public function removeReaction(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();
        $comment = CommentModel::find($id);
        
        if ($comment) {
            $comment->removeReaction($this->user()->id, $data['emoji'] ?? '👍');
        }

        $this->success([], 'Reaction removed');
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