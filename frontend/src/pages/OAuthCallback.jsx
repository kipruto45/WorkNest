import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import { setSession } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'
import { hasCompleteCurrentUser, persistAuthSession, persistCurrentUser } from '../utils/authSession'
import { resolvePostAuthPath } from '../utils/authRouting'
import { clearGoogleAuthState, readGoogleAuthState } from '../utils/googleAuthState'

export default function OAuthCallback() {
  const dispatch = useDispatch()
  const [searchParams] = useSearchParams()
  const authState = useMemo(() => readGoogleAuthState(), [])
  const authFlow = authState?.flow === 'register' ? 'register' : 'login'
  const [statusLabel, setStatusLabel] = useState(authFlow === 'register' ? 'Finishing Google sign-up' : 'Finishing secure sign-in')
  const [isSlow, setIsSlow] = useState(false)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setIsSlow(true)
    }, 6000)

    return () => window.clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    const finishGoogleCallback = async () => {
      const nextPath = searchParams.get('next') || '/dashboard'
      const accessToken = searchParams.get('access')
      const refreshToken = searchParams.get('refresh')
      const userValue = searchParams.get('user')

      const session = {
        accessToken,
        refreshToken,
        user: null,
      }

      if (userValue) {
        try {
          session.user = JSON.parse(userValue)
        } catch (storageError) {
          session.user = null
        }
      }

      if (!persistAuthSession(session)) {
        clearGoogleAuthState()
        toast.error('Google sign-in did not complete successfully.')
        window.location.replace('/login')
        return
      }

      try {
        setStatusLabel(authFlow === 'register' ? 'Creating your workspace' : 'Loading your workspace')
        let currentUser = session.user
        if (!hasCompleteCurrentUser(currentUser)) {
          const userResponse = await authAPI.getCurrentUser()
          currentUser = unwrapData(userResponse)
        }

        if (currentUser) {
          persistCurrentUser(currentUser)
          dispatch(
            setSession({
              token: session.accessToken,
              user: currentUser,
            })
          )
        }

        clearGoogleAuthState()
        toast.success('Authentication complete.')
        window.location.replace(resolvePostAuthPath({ nextPath, user: currentUser }))
      } catch (error) {
        clearGoogleAuthState()
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionAccess)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionRefresh)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
        toast.error('Google sign-in did not complete successfully.')
        window.location.replace('/login')
      }
    }

    const error = searchParams.get('error')

    if (error) {
      clearGoogleAuthState()
      toast.error('Google sign-in did not complete successfully.')
      window.location.replace('/login')
      return
    }

    finishGoogleCallback()
  }, [authFlow, dispatch, searchParams])

  const description = isSlow
    ? 'This is taking longer than expected. Google or background delivery services may be slow, but we are still completing your session.'
    : authFlow === 'register'
      ? 'We are creating your account, preparing your workspace, and securing your session.'
      : 'We are securing your session and loading the right workspace for this account.'

  return (
    <div className="app-shell px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <LoadingState label={statusLabel} description={description} />
      </div>
    </div>
  )
}
