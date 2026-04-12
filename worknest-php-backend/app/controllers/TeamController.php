<?php

namespace App\Controllers;

use App\Models\Team;
use App\Models\User;
use App\Models\Invitation;
use App\Services\EmailService;
use Core\Controller;
use Core\DB;
use Core\Auth;
use Core\Logger;
use Core\Token;

class TeamController extends Controller
{
    protected EmailService $emailService;

    public function __construct()
    {
        parent::__construct();
        $this->emailService = new EmailService();
    }

    public function index(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $teams = Team::getByUserId($this->user()->id);

        $this->success(['teams' => $teams]);
    }

    public function create(): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'name' => 'required|min:2|max:255',
        ]);

        if ($validator->fails()) {
            $this->validationError('Creation failed', $validator->errors());
            return;
        }

        $slug = $this->generateSlug($data['name']);

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO teams (name, slug, description, owner_id, status, created_at) VALUES (?, ?, ?, ?, 'active', NOW())",
            [$data['name'], $slug, $data['description'] ?? null, $this->user()->id]
        );

        $teamId = $db->lastInsertId();
        $team = Team::find($teamId);
        $team->addMember($this->user()->id, 'team_owner');

        $this->createDefaultTaskStatuses($teamId);
        Logger::logActivity($this->user()->id, $teamId, 'team.created', 'team', $teamId);

        $this->success(['team' => $team->toArray()], 'Team created');
    }

    public function show(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team || !$team->hasMember($this->user()->id)) {
            $this->notFound('Team not found');
            return;
        }

        $this->success([
            'team' => $team->toArray(),
            'members' => $team->getMembers(),
            'stats' => $team->getStats(),
        ]);
    }

    public function update(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team) {
            $this->notFound('Team not found');
            return;
        }

        if (!$this->authorize('edit_team', $team->id)) {
            $this->forbidden();
            return;
        }

        $data = $this->all();

        if (isset($data['name'])) {
            $team->name = $data['name'];
        }

        if (isset($data['description'])) {
            $team->description = $data['description'];
        }

        $team->save();
        Logger::logActivity($this->user()->id, $team->id, 'team.updated', 'team', $team->id);

        $this->success(['team' => $team->toArray()], 'Team updated');
    }

    public function members(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team || !$team->hasMember($this->user()->id)) {
            $this->notFound('Team not found');
            return;
        }

        $this->success(['members' => $team->getMembers()]);
    }

    public function updateMemberRole(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team) {
            $this->notFound('Team not found');
            return;
        }

        if (!$this->authorize('invite_member', $team->id)) {
            $this->forbidden();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'user_id' => 'required|exists:users,id',
            'role' => 'required|in:team_owner,team_admin,team_member,guest',
        ]);

        if ($validator->fails()) {
            $this->validationError('Update failed', $validator->errors());
            return;
        }

        $db = DB::getInstance();
        $db->run(
            "UPDATE memberships SET role = ?, updated_at = NOW() WHERE team_id = ? AND user_id = ?",
            [$data['role'], $id, $data['user_id']]
        );

        Logger::logActivity($this->user()->id, $team->id, 'team.member_role_updated', 'membership', $data['user_id']);

        $this->success([], 'Member role updated');
    }

    public function removeMember(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team) {
            $this->notFound('Team not found');
            return;
        }

        if (!$this->authorize('remove_member', $team->id)) {
            $this->forbidden();
            return;
        }

        $data = $this->all();
        $userId = $data['user_id'] ?? null;

        if (!$userId) {
            $this->error('User ID is required');
            return;
        }

        if ($team->owner_id == $userId) {
            $this->error('Cannot remove team owner');
            return;
        }

        $team->removeMember($userId);
        Logger::logActivity($this->user()->id, $team->id, 'team.member_removed', 'membership', $userId);

        $this->success([], 'Member removed');
    }

    public function invitations(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team || !$team->hasMember($this->user()->id)) {
            $this->notFound('Team not found');
            return;
        }

        $this->success(['invitations' => $team->getInvitations()]);
    }

    public function createInvitation(int $id): void
    {
        if (!$this->authenticate()) {
            $this->unauthorized();
            return;
        }

        $team = Team::find($id);

        if (!$team) {
            $this->notFound('Team not found');
            return;
        }

        if (!$this->authorize('invite_member', $team->id)) {
            $this->forbidden();
            return;
        }

        $data = $this->all();

        $validator = $this->validate($data, [
            'email' => 'required|email',
            'role' => 'in:team_owner,team_admin,team_member,guest',
        ]);

        if ($validator->fails()) {
            $this->validationError('Invitation failed', $validator->errors());
            return;
        }

        $existingUser = User::findByEmail($data['email']);
        if ($existingUser && $team->hasMember($existingUser->id)) {
            $this->error('User is already a member of this team');
            return;
        }

        $token = Token::generateEmailToken();
        $hashed = Token::hash($token);
        $expiresAt = date('Y-m-d H:i:s', time() + 604800);

        $db = DB::getInstance();
        $db->run(
            "INSERT INTO invitations (email, team_id, role, invited_by, expires_at, created_at) VALUES (?, ?, ?, ?, ?, NOW())",
            [$data['email'], $id, $data['role'] ?? 'team_member', $this->user()->id, $expiresAt]
        );

        $invitationId = $db->lastInsertId();
        $db->run(
            "INSERT INTO invitation_tokens (invitation_id, token, expires_at, created_at) VALUES (?, ?, ?, NOW())",
            [$invitationId, $hashed, $expiresAt]
        );

        $this->emailService->sendInvitationEmail(
            $data['email'],
            $this->user()->name,
            $team->name,
            $token
        );

        Logger::logActivity($this->user()->id, $team->id, 'team.invitation_created', 'invitation', $invitationId);

        $this->success(['invitation_id' => $invitationId], 'Invitation sent');
    }

    protected function generateSlug(string $name): string
    {
        $slug = strtolower(preg_replace('/[^a-z0-9-]/', '-', $name));
        $slug = preg_replace('/-+/', '-', $slug);
        $slug = trim($slug, '-');

        $db = DB::getInstance();
        $originalSlug = $slug;
        $counter = 1;

        while ($db->fetch("SELECT id FROM teams WHERE slug = ?", [$slug])) {
            $slug = $originalSlug . '-' . $counter++;
        }

        return $slug;
    }

    protected function createDefaultTaskStatuses(int $teamId): void
    {
        $db = DB::getInstance();

        $statuses = [
            ['name' => 'To Do', 'slug' => 'todo', 'color' => '#6b7280', 'position' => 1, 'is_default' => 1],
            ['name' => 'In Progress', 'slug' => 'in_progress', 'color' => '#3b82f6', 'position' => 2, 'is_default' => 0],
            ['name' => 'In Review', 'slug' => 'in_review', 'color' => '#f59e0b', 'position' => 3, 'is_default' => 0],
            ['name' => 'Done', 'slug' => 'done', 'color' => '#10b981', 'position' => 4, 'is_default' => 0],
        ];

        foreach ($statuses as $status) {
            $db->run(
                "INSERT INTO task_statuses (team_id, name, slug, color, position, is_default, created_at) VALUES (?, ?, ?, ?, ?, ?, NOW())",
                [$teamId, $status['name'], $status['slug'], $status['color'], $status['position'], $status['is_default']]
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

    protected function authorize(string $permission, int $teamId): bool
    {
        return Auth::canTeam($permission, $teamId);
    }
}