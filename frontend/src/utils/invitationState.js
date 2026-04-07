export function deriveInvitationViewState({ requestState, invitation, currentEmail }) {
  if (requestState === 'missing') return 'missing'
  if (requestState === 'invalid') return 'invalid'
  if (requestState === 'error') return 'error'
  if (!invitation) return 'loading'
  if (invitation?.team?.is_archived) return 'archived'
  if (invitation?.is_expired || invitation?.status === 'expired') return 'expired'
  if (invitation?.status === 'revoked') return 'revoked'
  if (invitation?.status === 'accepted') return 'accepted'
  if (invitation?.status === 'declined') return 'declined'
  if (!currentEmail) return 'auth_required'
  if (currentEmail.toLowerCase() !== invitation.email.toLowerCase()) return 'mismatch'
  return 'actionable'
}

export function resolveInvitationTitle(state) {
  if (state === 'auth_required') return 'Sign in to continue'
  if (state === 'mismatch') return 'Wrong account for this invite'
  if (state === 'accepted') return 'Invitation accepted'
  if (state === 'declined') return 'Invitation declined'
  if (state === 'expired') return 'This invite has expired'
  if (state === 'revoked') return 'This invite was revoked'
  if (state === 'archived') return 'This team is archived'
  if (state === 'invalid') return 'Invitation not found'
  if (state === 'missing') return 'Invitation link is incomplete'
  if (state === 'error') return 'We could not load this invitation'
  return 'Review team invitation'
}

export function resolveInvitationSubtitle(state, invitation) {
  if (state === 'auth_required') return 'Use the invited email address so the workspace can verify you correctly.'
  if (state === 'mismatch') return 'Only the invited email address can accept this workspace invitation.'
  if (state === 'accepted') return 'The invitation is complete and your access is ready.'
  if (state === 'declined') return 'The invitation has been closed without joining the team.'
  if (state === 'expired') return 'Ask the inviter for a fresh invitation link if you still need access.'
  if (state === 'revoked') return 'The inviter revoked this request before it was accepted.'
  if (state === 'archived') return 'The workspace is no longer accepting new members through this invitation.'
  if (state === 'invalid') return 'This invite token is missing, invalid, or no longer available.'
  if (state === 'missing') return 'Open the full invitation link from your email and try again.'
  if (state === 'error') return 'Please refresh the page or try the invitation link again later.'
  return invitation?.team?.description || 'Review the team, role, and inviter details before you continue.'
}
