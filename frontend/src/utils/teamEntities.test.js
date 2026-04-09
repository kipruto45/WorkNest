import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeTeamEntity } from './teamEntities.js'

test('normalizeTeamEntity maps my_membership.role into my_role for newly created teams', () => {
  const normalized = normalizeTeamEntity({
    id: 'team-1',
    name: 'Platform',
    my_membership: { role: 'admin' },
  })

  assert.equal(normalized.my_role, 'admin')
})
