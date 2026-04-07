import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import PageHero from '../components/PageHero'
import StatCard from '../components/StatCard'
import LoadingState from '../components/LoadingState'
import { setUser } from '../features/authSlice'
import { usersAPI, unwrapData } from '../services/api'
import { PROFILE_FIELD_KEYS } from '../utils/clientConfig.js'
import { hasCompleteCurrentUser, persistCurrentUser } from '../utils/authSession'
import { clampPercent, formatDate, getInitials } from '../utils/formatters'

export default function Profile() {
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState(null)
  const [avatarFile, setAvatarFile] = useState(null)
  const [avatarPreview, setAvatarPreview] = useState('')
  const currentUser = useSelector((state) => state.auth.user)
  const dispatch = useDispatch()
  const avatarInputRef = useRef(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm()

  const loadProfile = async () => {
    setLoading(true)
    try {
      const response = await usersAPI.getProfile()
      const data = unwrapData(response)
      setProfile(data)
      setAvatarFile(null)
      if (avatarPreview) {
        URL.revokeObjectURL(avatarPreview)
      }
      setAvatarPreview('')
      reset(data)
    } catch (_error) {
      if (hasCompleteCurrentUser(currentUser)) {
        setProfile(currentUser)
        reset(currentUser)
        toast.info('Showing your cached profile while the live profile service recovers.')
      } else {
        toast.error('Unable to load profile right now.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProfile()
  }, [currentUser])

  useEffect(() => {
    return () => {
      if (avatarPreview) {
        URL.revokeObjectURL(avatarPreview)
      }
    }
  }, [avatarPreview])

  const handleAvatarSelection = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      toast.error('Please choose a valid image file.')
      event.target.value = ''
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Avatar image must be 5 MB or smaller.')
      event.target.value = ''
      return
    }

    if (avatarPreview) {
      URL.revokeObjectURL(avatarPreview)
    }

    setAvatarFile(file)
    setAvatarPreview(URL.createObjectURL(file))
  }

  const onSubmit = async (data) => {
    try {
      const payload = new FormData()
      payload.append('name', data.name || '')
      payload.append('first_name', data.first_name || '')
      payload.append('last_name', data.last_name || '')
      payload.append(PROFILE_FIELD_KEYS.locale, data[PROFILE_FIELD_KEYS.locale] || '')
      payload.append('bio', data.bio || '')

      if (avatarFile) {
        payload.append('avatar_file', avatarFile)
      }

      const response = await usersAPI.updateProfile(payload)
      const updatedProfile = unwrapData(response)
      setProfile(updatedProfile)
      setAvatarFile(null)
      if (avatarPreview) {
        URL.revokeObjectURL(avatarPreview)
      }
      setAvatarPreview('')
      if (avatarInputRef.current) {
        avatarInputRef.current.value = ''
      }
      persistCurrentUser(updatedProfile)
      dispatch(setUser(updatedProfile))
      reset(updatedProfile)
      toast.success('Profile updated successfully.')
    } catch (error) {
      toast.error('Unable to update profile right now.')
    }
  }

  if (loading || !profile) {
    return <LoadingState label="Loading your profile" />
  }

  const activeAvatar = avatarPreview || profile.avatar

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="Profile"
        title="Personal identity and workspace settings"
        description="Keep your details up to date so mentions, assignments, and team collaboration feel more human."
        stats={[
          { label: 'Completion', value: `${clampPercent(profile.profile_completion)}%`, caption: 'Profile readiness' },
          { label: 'Verified', value: profile.email_verified ? 'Yes' : 'No', caption: 'Email status' },
          { label: 'Locale', value: profile[PROFILE_FIELD_KEYS.locale] || 'Not set', caption: 'Current locale' },
        ]}
        spotlight={{
          eyebrow: 'Identity',
          title: 'Your profile doubles as a collaboration surface.',
          description: 'A richer identity helps mentions, ownership, and workspace trust feel more intentional during demos and real work.',
          points: [
            { label: 'Joined', value: formatDate(profile.date_joined) },
            { label: 'Provider', value: profile.auth_provider || 'email' },
          ],
        }}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="Profile completion" value={`${clampPercent(profile.profile_completion)}%`} hint="Helpful for team visibility" />
        <StatCard label="Email verified" value={profile.email_verified ? 'Yes' : 'No'} hint={profile.email} />
        <StatCard label="Joined" value={formatDate(profile.date_joined)} hint="Member since" accent="from-teal-500 to-lime-500" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[320px,1fr]">
        <div className="card fade-in">
          <div className="flex flex-col items-center text-center">
            <div className="relative">
              <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-[28px] bg-gradient-to-br from-emerald-500 to-teal-500 text-3xl font-bold text-white shadow-glow">
                {activeAvatar ? (
                  <img src={activeAvatar} alt={profile.name} className="h-full w-full object-cover" />
                ) : (
                  getInitials(profile.name)
                )}
              </div>
              <button
                type="button"
                onClick={() => avatarInputRef.current?.click()}
                className="absolute -bottom-1 -right-1 inline-flex h-9 w-9 items-center justify-center rounded-full border border-white bg-slate-950 text-white shadow-[0_8px_20px_rgba(15,23,42,0.18)] transition-transform duration-200 hover:-translate-y-0.5"
                aria-label="Upload avatar"
              >
                <CameraIcon className="h-4 w-4" />
              </button>
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleAvatarSelection}
              />
            </div>
            <h3 className="mt-4 text-2xl font-bold text-emerald-950">{profile.name}</h3>
            <p className="mt-2 text-sm text-soft">{profile.email}</p>
            <p className="mt-3 text-xs font-medium uppercase tracking-[0.14em] text-emerald-700">
              Click the camera icon to upload from your computer
            </p>
            <div className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-soft">
              {profile.bio || 'Add a short bio so teammates know your focus and working style.'}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="card grid gap-5 fade-in">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Display name</label>
              <input {...register('name')} className="input-field" placeholder="Alex Morgan" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Avatar source</label>
              <div className="input-field flex items-center justify-between gap-3 text-sm text-soft">
                <span className="truncate">{avatarFile ? avatarFile.name : profile.avatar ? 'Current image saved' : 'No avatar uploaded yet'}</span>
                <button
                  type="button"
                  onClick={() => avatarInputRef.current?.click()}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50"
                >
                  <CameraIcon className="h-4 w-4" />
                  Change
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">First name</label>
              <input {...register('first_name')} className="input-field" placeholder="Alex" />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-emerald-950">Last name</label>
              <input {...register('last_name')} className="input-field" placeholder="Morgan" />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Locale</label>
            <input {...register(PROFILE_FIELD_KEYS.locale)} className="input-field" placeholder="Africa/Nairobi" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-emerald-950">Bio</label>
            <textarea {...register('bio')} className="input-field min-h-[140px]" placeholder="Tell your team what you own and how you like to work." />
          </div>

          <div className="flex justify-end">
            <button type="submit" disabled={isSubmitting} className="btn-primary">
              {isSubmitting ? 'Saving profile...' : 'Save profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CameraIcon(props) {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" {...props}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.8}
        d="M4 8.5A2.5 2.5 0 0 1 6.5 6H8l1.2-1.6A2 2 0 0 1 10.8 4h2.4a2 2 0 0 1 1.6.8L16 6h1.5A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-8Z"
      />
      <circle cx="12" cy="12.5" r="3.5" strokeWidth={1.8} />
    </svg>
  )
}
