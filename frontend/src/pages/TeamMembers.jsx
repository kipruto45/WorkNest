import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import LoadingState from '../components/LoadingState'
import EmptyState from '../components/EmptyState'
import { teamsAPI, unwrapData, unwrapResults } from '../services/api'
import { formatDate, getInitials, toSentenceCase } from '../utils/formatters'
import { canManageMembers, resolveMembershipRole } from '../utils/permissions'

const roleOptions = ['admin', 'manager', 'member']

export default function TeamMembers() {
  const { teamId } = useParams()
  const [loading, setLoading] = useState(true)
  const [team, setTeam] = useState(null)
  const [members, setMembers] = useState([])

  const loadMembers = async () => {
    setLoading(true)
    try {
      const [teamResponse, membersResponse] = await Promise.all([
        teamsAPI.getTeam(teamId),
        teamsAPI.getTeamMembers(teamId),
      ])
      setTeam(unwrapData(teamResponse))
      setMembers(unwrapResults(membersResponse))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMembers()
  }, [teamId])

  const handleRoleChange = async (memberId, role) => {
    try {
      await teamsAPI.updateMemberRole(teamId, memberId, { role })
      toast.success('Member role updated.')
      await loadMembers()
    } catch (error) {
      toast.error('Unable to update role right now.')
    }
  }

  const handleRemove = async (memberId) => {
    try {
      await teamsAPI.removeMember(teamId, memberId)
      toast.success('Member removed from team.')
      await loadMembers()
    } catch (error) {
      toast.error('Unable to remove member right now.')
    }
  }

  if (loading || !team) {
    return <LoadingState label="Loading team members" />
  }

  const currentRole = resolveMembershipRole(team)
  const canManage = canManageMembers(currentRole)

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Team Members"
        title={`${team.name} members`}
        description="Review who is in the workspace, what role they hold, and when they joined."
        aside={canManage ? 'Admin controls enabled' : `Your role: ${toSentenceCase(currentRole || 'member')}`}
      />

      {members.length === 0 ? (
        <EmptyState
          title="No active members found"
          description="Invite collaborators to this workspace to start assigning work and collaborating in one place."
        />
      ) : (
        <div className="grid gap-4">
          {members.map((membership) => (
            <div key={membership.id} className="card fade-in">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-500 text-lg font-bold text-white">
                    {getInitials(membership.user?.name)}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-emerald-950">{membership.user?.name || 'Unnamed user'}</h3>
                    <p className="mt-1 text-sm text-soft">
                      {membership.user?.bio || 'No bio added yet'} • Joined {formatDate(membership.joined_at)}
                    </p>
                  </div>
                </div>

                {canManage ? (
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <select
                      value={membership.role}
                      onChange={(event) => handleRoleChange(membership.id, event.target.value)}
                      className="input-field min-w-[180px]"
                    >
                      {roleOptions.map((role) => (
                        <option key={role} value={role}>
                          {toSentenceCase(role)}
                        </option>
                      ))}
                    </select>
                    <button type="button" onClick={() => handleRemove(membership.id)} className="btn-secondary">
                      Remove member
                    </button>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    Team admins can update roles and remove members.
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
