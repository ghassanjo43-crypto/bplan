import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePasswordRequest } from '@/api/authApi'
import { useAuth } from '@/auth/useAuth'
import { PageHeader } from '@/components/PageHeader'
import { SectionCard } from '@/components/SectionCard'
import { useToast } from '@/components/ui/Toast'

export function ChangePasswordPage() {
  const { currentUser, refreshUser } = useAuth()
  const { notify } = useToast()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const forced = !!currentUser?.must_change_password

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (next !== confirm) { setError('New password and confirmation do not match.'); return }
    setBusy(true)
    try {
      await changePasswordRequest(current, next)
      await refreshUser()
      notify('Password changed successfully')
      navigate('/projects', { replace: true })
    } catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  return <>
    <PageHeader breadcrumb={currentUser?.role === 'admin' ? 'Admin / Account / Security' : 'Account'}
      title={forced ? 'Create a permanent password' : 'Change password'}
      subtitle={forced ? 'You must replace your temporary password before using Planora.' : 'Verify your current password and choose a new one.'} />
    <div className="stack" style={{ maxWidth: 620 }}><SectionCard>
      <form className="stack--sm" onSubmit={submit}>
        {error && <div className="banner banner--warning">{error}</div>}
        <label className="field"><span className="field__label">Current password</span>
          <input className="input" type="password" autoComplete="current-password" value={current} onChange={e => setCurrent(e.target.value)} required /></label>
        <label className="field"><span className="field__label">New password</span>
          <input className="input" type="password" autoComplete="new-password" value={next} onChange={e => setNext(e.target.value)} required /></label>
        <label className="field"><span className="field__label">Confirm new password</span>
          <input className="input" type="password" autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} required /></label>
        <div className="muted">At least 10 characters with uppercase, lowercase, number, and special character.</div>
        <button className="btn btn--primary" type="submit" disabled={busy}>{busy ? 'Changing…' : 'Change password'}</button>
      </form>
    </SectionCard></div>
  </>
}
