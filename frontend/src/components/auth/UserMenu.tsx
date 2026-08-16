import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'

export function UserMenu() {
  const { currentUser, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  if (!currentUser) return null
  return (
    <div className="row" style={{ gap: 8, alignItems: 'center' }}>
      {isAdmin && (
        <button className="btn btn--ghost btn--sm" onClick={() => navigate('/admin/users')} title="User management">
          👤 Users
        </button>
      )}
      {isAdmin && (
        <button className="btn btn--ghost btn--sm" onClick={() => navigate('/admin/security')} title="Account security">
          Security
        </button>
      )}
      <span className="usermenu__id" title={currentUser.email}>
        {currentUser.full_name || currentUser.email}
        <span className="usermenu__role">{currentUser.role}</span>
      </span>
      <button className="btn btn--secondary btn--sm" onClick={async () => { await logout(); navigate('/login') }}>
        Sign out
      </button>
    </div>
  )
}
