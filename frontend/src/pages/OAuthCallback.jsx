import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { toast } from 'react-toastify'
import LoadingState from '../components/LoadingState'
import { setSession } from '../features/authSlice'
import { authAPI, unwrapData } from '../services/api'
import { persistAuthSession, persistCurrentUser } from '../utils/authSession'

export default function OAuthCallback() {
  const navigate = useNavigate()
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
        navigate('/login')
        return
      }

      try {
        let currentUser = session.user
        if (!currentUser) {
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
        navigate(nextPath)
      } catch (error) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        toast.error('Google sign-in did not complete successfully.')
        navigate('/login')
      }
    }

    const error = searchParams.get('error')

    if (error) {
      toast.error('Google sign-in did not complete successfully.')
      navigate('/login')
      return
    }

    finishGoogleCallback()
  }, [dispatch, navigate, searchParams])

  return (
    <div className="app-shell px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <LoadingState label="Finishing secure sign-in" />
      </div>
    </div>
  )
}
