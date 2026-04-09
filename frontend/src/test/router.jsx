import React from 'react'
import { MemoryRouter } from 'react-router-dom'

import { routerFuture } from '../router/future'

export function TestMemoryRouter(props) {
  return <MemoryRouter future={routerFuture} {...props} />
}
