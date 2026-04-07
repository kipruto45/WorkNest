import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import { setSession } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { CLIENT_STORAGE_KEYS } from '../utils/clientConfig.js'
import { hasCompleteCurrentUser, persistAuthSession, persistCurrentUser } from '../utils/authSession'

const resolvePostLoginPath = ({ nextPath, user }) => {
  const trimmedNextPath = typeof nextPath === 'string' ? nextPath.trim() : ''
  if (trimmedNextPath && !['/', '/dashboard'].includes(trimmedNextPath)) {
    return trimmedNextPath
  }
  return user?.is_staff ? '/admin' : '/dashboard'
}

export default function OAuthCallback() {
  const dispatch = useDispatch()
  const [searchParams] = useSearchParams()

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
        toast.error('Google sign-in did not complete successfully.')
        window.location.replace('/login')
        return
      }

      try {
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

        toast.success('Authentication complete.')
        window.location.replace(resolvePostLoginPath({ nextPath, user: currentUser }))
      } catch (error) {
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionAccess)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionRefresh)
        localStorage.removeItem(CLIENT_STORAGE_KEYS.sessionUser)
        toast.error('Google sign-in did not complete successfully.')
        window.location.replace('/login')
      }
    }

    const error = searchParams.get('error')

    if (error) {
      toast.error('Google sign-in did not complete successfully.')
      window.location.replace('/login')
      return
    }

    finishGoogleCallback()
  }, [dispatch, searchParams])

  return (
    <div className="app-shell px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <LoadingState label="Finishing secure sign-in" />
      </div>
    </div>
  )
}
