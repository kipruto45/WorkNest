import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import Layout from './components/Layout'
import { hydrateCurrentUser } from './features/authSlice'
import { hasCompleteCurrentUser } from './utils/authSession'

const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const OAuthCallback = lazy(() => import('./pages/OAuthCallback'))
const Landing = lazy(() => import('./pages/Landing'))
const About = lazy(() => import('./pages/About'))
const HelpCenter = lazy(() => import('./pages/HelpCenter'))
const ApiDocsPage = lazy(() => import('./pages/ApiDocsPage'))
const StatusPage = lazy(() => import('./pages/StatusPage'))
const SecurityPage = lazy(() => import('./pages/SecurityPage'))
const ContactPage = lazy(() => import('./pages/ContactPage'))
const SupportPage = lazy(() => import('./pages/SupportPage'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Teams = lazy(() => import('./pages/Teams'))
const TeamBoard = lazy(() => import('./pages/TeamBoard'))
const TeamOverview = lazy(() => import('./pages/TeamOverview'))
const TeamMembers = lazy(() => import('./pages/TeamMembers'))
const TeamInvitations = lazy(() => import('./pages/TeamInvitations'))
const TeamAnalytics = lazy(() => import('./pages/TeamAnalytics'))
const TeamActivity = lazy(() => import('./pages/TeamActivity'))
const TeamSettings = lazy(() => import('./pages/TeamSettings'))
const TaskDetail = lazy(() => import('./pages/TaskDetail'))
const MyTasks = lazy(() => import('./pages/MyTasks'))
const Calendar = lazy(() => import('./pages/Calendar'))
const Notifications = lazy(() => import('./pages/Notifications'))
const Profile = lazy(() => import('./pages/Profile'))
const Settings = lazy(() => import('./pages/Settings'))
const Search = lazy(() => import('./pages/Search'))
const Archive = lazy(() => import('./pages/Archive'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const InvitationResponse = lazy(() => import('./pages/InvitationResponse'))
const Forbidden = lazy(() => import('./pages/Forbidden'))
const ServerError = lazy(() => import('./pages/ServerError'))
const NotFound = lazy(() => import('./pages/NotFound'))

function PrivateRoute({ children }) {
  const { token, hydrating } = useSelector((state) => state.auth)
  if (token && hydrating) {
    return <RouteFallback />
  }
  return token ? children : <Navigate to="/login" replace />
}

function AdminRoute({ children }) {
  const { user, hydrating } = useSelector((state) => state.auth)
  if (hydrating) {
    return <RouteFallback />
  }
  return user?.is_staff ? children : <Navigate to="/403" replace />
}

function App() {
  const dispatch = useDispatch()
  const { token, user } = useSelector((state) => state.auth)

  useEffect(() => {
    if (token && !hasCompleteCurrentUser(user)) {
      dispatch(hydrateCurrentUser())
    }
  }, [dispatch, token, user])

  return (
    <>
      <ToastContainer
        position="top-right"
        toastClassName="!rounded-2xl !bg-white/90 !text-emerald-950 !shadow-lg !backdrop-blur-xl"
      />

      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/welcome" element={<Navigate to="/" replace />} />
          <Route path="/about" element={<About />} />
          <Route path="/help-center" element={<HelpCenter />} />
          <Route path="/api-docs" element={<ApiDocsPage />} />
          <Route path="/status" element={<StatusPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/support" element={<SupportPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/auth/google/callback" element={<OAuthCallback />} />
          <Route path="/invitations/:token" element={<InvitationResponse />} />
          <Route path="/accept-invitation" element={<InvitationResponse />} />
          <Route path="/403" element={<Forbidden />} />
          <Route path="/500" element={<ServerError />} />

          <Route
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="tasks" element={<MyTasks />} />
            <Route path="tasks/:taskId" element={<TaskDetail />} />
            <Route path="calendar" element={<Calendar />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings" element={<Settings />} />
            <Route path="search" element={<Search />} />
            <Route path="archive" element={<Archive />} />
            <Route
              path="admin"
              element={
                <AdminRoute>
                  <AdminDashboard />
                </AdminRoute>
              }
            />
            <Route
              path="admin/:section"
              element={
                <AdminRoute>
                  <AdminDashboard />
                </AdminRoute>
              }
            />
            <Route path="teams" element={<Teams />} />
            <Route path="teams/:teamId" element={<TeamBoard />} />
            <Route path="teams/:teamId/overview" element={<TeamOverview />} />
            <Route path="teams/:teamId/members" element={<TeamMembers />} />
            <Route path="teams/:teamId/invitations" element={<TeamInvitations />} />
            <Route path="teams/:teamId/analytics" element={<TeamAnalytics />} />
            <Route path="teams/:teamId/activity" element={<TeamActivity />} />
            <Route path="teams/:teamId/settings" element={<TeamSettings />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </>
  )
}

export default App

function RouteFallback() {
  return (
    <div className="app-shell flex min-h-screen items-center justify-center bg-[#f7f8f6] px-4 py-10">
      <div className="rounded-[24px] border border-slate-200 bg-white px-6 py-5 text-center shadow-[0_12px_32px_rgba(15,23,42,0.06)]">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">Loading</p>
        <p className="mt-3 text-sm text-slate-600">Preparing your workspace…</p>
      </div>
    </div>
  )
}
