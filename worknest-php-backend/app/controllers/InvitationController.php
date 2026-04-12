<?php

namespace App\Controllers;

use App\Models\Invitation as InvitationModel;
use App\Models\User;
use Core\Controller;
use Core\DB;
use Core\Token;

class InvitationController extends Controller
{
    public function accept(): void
    {
        $data = $this->all();
        
        if (empty($data['token'])) {
            $this->error('Token is required');
            return;
        }

        $token = Token::hash($data['token']);
        $db = DB::getInstance();

        $invitationToken = $db->fetch(
            "SELECT it.*, i.email, i.team_id, i.role, i.status as invitation_status FROM invitation_tokens it INNER JOIN invitations i ON it.invitation_id = i.id WHERE it.token = ? AND it.expires_at > NOW()",
            [$token]
        );

        if (!$invitationToken) {
            $this->error('Invalid or expired invitation');
            return;
        }

        if ($invitationToken['invitation_status'] !== 'pending') {
            $this->error('Invitation is no longer valid');
            return;
        }

        $user = User::findByEmail($invitationToken['email']);
        if (!$user) {
            $this->error('User not found. Please register first.');
            return;
        }

        $invitation = InvitationModel::find($invitationToken['invitation_id']);
        $invitation->accept($user->id);

        $this->success([], 'Invitation accepted');
    }

    public function revoke(): void
    {
        $data = $this->all();
        
        if (empty($data['invitation_id'])) {
            $this->error('Invitation ID is required');
            return;
        }

        $invitation = InvitationModel::find($data['invitation_id']);
        if ($invitation) {
            $invitation->revoke();
        }

        $this->success([], 'Invitation revoked');
    }
}