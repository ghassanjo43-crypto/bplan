import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { LoadingScreen } from '@/components/ui/Spinner'
import { useAuth } from './useAuth'

export function ProtectedRoute() {
  const { currentUser, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  if (isLoading) return <LoadingScreen label="Loading…" />
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (currentUser?.must_change_password && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }
  if (currentUser && !currentUser.must_change_password && location.pathname === '/change-password' && currentUser.role !== 'admin') {
    return <Navigate to="/projects" replace />
  }
  return <Outlet />
}

export function AdminRoute() {
  const { isAdmin, isLoading } = useAuth()
  if (isLoading) return <LoadingScreen label="Loading…" />
  if (!isAdmin) return <Navigate to="/projects" replace />
  return <Outlet />
}
