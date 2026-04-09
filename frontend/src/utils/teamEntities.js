export const normalizeTeamEntity = (team) => {
  if (!team || typeof team !== 'object') {
    return team
  }

  return {
    ...team,
    my_role: team.my_role ?? team.my_membership?.role ?? null,
  }
}
