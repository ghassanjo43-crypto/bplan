import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { ApiError } from '@/api/client'

export function LoginPage() {
  const navigate = useNavigate()
  const { login, isAuthenticated } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) {
    navigate('/guide', { replace: true })
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(undefined)
    setBusy(true)
    try {
      await login(email.trim(), password)
      navigate('/guide', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign in failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <div className="login__card">
        <div className="login__brand">
          <div className="sidebar__logo">B</div>
          <div className="login__brand-name">Business Plan Studio</div>
        </div>
        <h1 className="login__title">Welcome back</h1>
        <p className="login__subtitle">
          Sign in to manage your companies, projects, financial models, and business-plan reports.
        </p>

        {error && <div className="login__error">{error}</div>}

        <form onSubmit={submit} className="stack--sm">
          <div className="field">
            <span className="field__label">Email</span>
            <input className="input" type="email" autoComplete="username" value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoFocus required />
          </div>
          <div className="field">
            <span className="field__label">Password</span>
            <div className="login__password">
              <input className="input" type={show ? 'text' : 'password'} autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
              <button type="button" className="login__toggle" onClick={() => setShow((s) => !s)}>
                {show ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
          <button className="btn btn--primary btn--lg" type="submit" disabled={busy} style={{ width: '100%' }}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="login__hint">
          Demo: <code>admin@example.com</code> / <code>ChangeMe123!</code>
        </div>
      </div>
    </div>
  )
}
