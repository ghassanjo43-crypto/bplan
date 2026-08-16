import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { SectionCard } from '@/components/SectionCard'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { LoadingScreen } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/Toast'
import { useCompanies } from '@/api/companyApi'
import {
  useAssignCompany,
  useCreateUser,
  useDeleteUser,
  useEndTrial,
  useExtendTrial,
  useResetUserPassword,
  useSetTrial,
  useSetUserActive,
  useUpdateUser,
  useUsers,
} from '@/api/adminUsersApi'
import type { AccountStatus, CreateUserInput, ManagedUser, Role } from '@/types/auth'

const DURATIONS = [7, 14, 30, 60, 90]

const STATUS_TONE: Record<AccountStatus, 'green' | 'blue' | 'amber' | 'red'> = {
  active: 'green', trial: 'blue', expired: 'amber', suspended: 'red',
}
const STATUS_LABEL: Record<AccountStatus, string> = {
  active: 'Active', trial: 'Active trial', expired: 'Trial expired', suspended: 'Suspended',
}

function statusOf(u: ManagedUser): AccountStatus {
  return (u.account_status as AccountStatus) ?? (u.is_active ? 'active' : 'suspended')
}

function fmtDate(s?: string | null): string {
  if (!s) return '—'
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function calcEnd(start: string, days: number): string {
  if (!start || !days || days < 1) return '—'
  const d = new Date(start)
  if (Number.isNaN(d.getTime())) return '—'
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

const today = () => new Date().toISOString().slice(0, 10)

export function UserManagementPage() {
  const navigate = useNavigate()
  const { notify } = useToast()
  const usersQ = useUsers()
  const companiesQ = useCompanies()
  const create = useCreateUser()
  const setActive = useSetUserActive()
  const updateUser = useUpdateUser()
  const assign = useAssignCompany()
  const resetPw = useResetUserPassword()
  const del = useDeleteUser()
  const [open, setOpen] = useState(false)
  const [trialUser, setTrialUser] = useState<ManagedUser | null>(null)
  const [resetUser, setResetUser] = useState<ManagedUser | null>(null)
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [highlightEmail, setHighlightEmail] = useState<string | null>(null)

  // Briefly highlight a row (e.g. the email a create just resolved to).
  const highlight = (email: string) => {
    const e = email.trim().toLowerCase()
    setHighlightEmail(e)
    setTimeout(() => setHighlightEmail((cur) => (cur === e ? null : cur)), 5000)
  }

  const companyName = useMemo(() => {
    const map = new Map((companiesQ.data ?? []).map((c) => [c.id, c.company_name]))
    return (id: string | null) => (id ? map.get(id) ?? id : '—')
  }, [companiesQ.data])

  if (usersQ.isLoading) return <LoadingScreen label="Loading users…" />

  const users = (usersQ.data ?? []).filter(
    (u) => !search || u.email.toLowerCase().includes(search.toLowerCase()) || u.full_name.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <>
      <PageHeader
        breadcrumb="Admin"
        title="User Management"
        subtitle="Create users, grant trial periods, assign companies, and control access."
        actions={
          <>
            <button className="btn btn--ghost" onClick={() => navigate('/projects')}>← Projects</button>
            <button className="btn btn--primary" onClick={() => setOpen(true)}>+ Add User</button>
          </>
        }
      />
      <div className="stack">
        <SectionCard>
          {usersQ.isError ? (
            <div className="banner banner--warning" style={{ alignItems: 'center' }}>
              <span className="banner__icon">⚠</span>
              <div style={{ flex: 1 }}>Could not load users. Please check the API connection and try again.</div>
              <button className="btn btn--secondary btn--sm" disabled={usersQ.isFetching}
                onClick={() => { void usersQ.refetch() }}>
                {usersQ.isFetching ? 'Retrying…' : 'Retry'}
              </button>
            </div>
          ) : (
          <>
          <input className="input" placeholder="Search by name or email" value={search}
            onChange={(e) => setSearch(e.target.value)} style={{ maxWidth: 320, marginBottom: 12 }} />
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th><th>Email</th><th>Role</th><th>Company</th><th>Demo Access</th><th>Status</th>
                  <th>Trial end</th><th style={{ textAlign: 'right' }}>Days left</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const st = statusOf(u)
                  const isHit = highlightEmail === u.email.toLowerCase()
                  return (
                    <tr key={u.id} style={isHit ? { background: 'var(--blue-50, #eef4ff)' } : undefined}>
                      <td>{u.full_name || '—'}</td>
                      <td>{u.email}</td>
                      <td><Badge tone={u.role === 'admin' ? 'blue' : 'neutral'}>{u.role}</Badge></td>
                      <td>{u.role === 'admin' ? 'All companies' : companyName(u.company_id)}</td>
                      <td>{u.role === 'admin'
                        ? <Badge tone="blue">Yes</Badge>
                        : <Badge tone={u.demo_company_access ? 'green' : 'neutral'}>{u.demo_company_access ? 'Yes' : 'No'}</Badge>}</td>
                      <td><Badge tone={STATUS_TONE[st]} dot>{STATUS_LABEL[st]}</Badge></td>
                      <td>{u.trial_enabled ? fmtDate(u.trial_end_date) : '—'}</td>
                      <td style={{ textAlign: 'right' }}>
                        {u.trial_enabled && typeof u.days_remaining === 'number'
                          ? (u.days_remaining >= 0 ? u.days_remaining : <span style={{ color: 'var(--amber-600)' }}>expired</span>)
                          : '—'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="row" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          {u.role !== 'admin' && (
                            <button className="btn btn--ghost btn--sm" title="Toggle access to the AquaPure demo company"
                              onClick={() => updateUser.mutate(
                                { id: u.id, body: { demo_company_access: !u.demo_company_access } },
                                { onSuccess: () => notify(u.demo_company_access ? 'Demo access removed' : 'Demo access granted'),
                                  onError: (e) => notify((e as Error).message, 'error') })}>
                              {u.demo_company_access ? 'Revoke demo' : 'Grant demo'}
                            </button>
                          )}
                          {u.role !== 'admin' && (
                            <button className="btn btn--ghost btn--sm" onClick={() => setTrialUser(u)}>Trial</button>
                          )}
                          <button className="btn btn--ghost btn--sm" onClick={() => setActive.mutate({ id: u.id, active: !u.is_active })}>
                            {u.is_active ? 'Disable' : 'Enable'}
                          </button>
                          {u.role === 'user' && (
                            <select className="input input--sm" value={u.company_id ?? ''} style={{ width: 130 }}
                              onChange={(e) => assign.mutate({ id: u.id, company_id: e.target.value }, { onSuccess: () => notify('Company updated') })}>
                              {(companiesQ.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
                            </select>
                          )}
                          {u.role === 'user' && <button className="btn btn--ghost btn--sm" onClick={() => setResetUser(u)}>Reset password</button>}
                          <button className="btn btn--ghost btn--sm" onClick={() => {
                            if (window.confirm(`Delete ${u.email}?`)) del.mutate(u.id, { onSuccess: () => notify('User deleted') })
                          }}>🗑</button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          </>
          )}
        </SectionCard>
      </div>

      {open && <AddUserModal onClose={() => setOpen(false)} onCreate={(body) => create.mutate(body, {
        onSuccess: () => { notify('User created'); setOpen(false); void usersQ.refetch(); highlight(body.email) },
        onError: (e) => {
          const msg = (e as Error).message
          if (/already exists/i.test(msg)) {
            // The user really exists — the list was likely stale/failed. Refresh
            // and point the admin at the existing row instead of a confusing error.
            void usersQ.refetch()
            highlight(body.email)
            setOpen(false)
            notify('This email already exists. The user list has been refreshed.')
          } else {
            notify(msg, 'error')
          }
        },
      })} companies={companiesQ.data ?? []} pending={create.isPending} />}

      {trialUser && <TrialModal user={trialUser} onClose={() => setTrialUser(null)} />}
      {resetUser && <Modal title={`Reset password — ${resetUser.email}`} open onClose={() => { setResetUser(null); setTemporaryPassword(null) }} footer={
        <div className="row" style={{ gap: 8, justifyContent: 'flex-end', width: '100%' }}>
          <button className="btn btn--secondary" onClick={() => { setResetUser(null); setTemporaryPassword(null) }}>{temporaryPassword ? 'Done' : 'Cancel'}</button>
          {!temporaryPassword && <button className="btn btn--primary" disabled={resetPw.isPending} onClick={() => resetPw.mutate(resetUser.id, {
            onSuccess: (result) => { setTemporaryPassword(result.temporary_password); notify('Password reset successfully') },
            onError: (e) => notify((e as Error).message, 'error'),
          })}>{resetPw.isPending ? 'Resetting…' : 'Confirm reset'}</button>}
        </div>
      }>
        {temporaryPassword ? <div className="stack--sm">
          <div className="banner banner--info">Copy this temporary password now. It is shown only once and the user must replace it at login.</div>
          <label className="field"><span className="field__label">One-time temporary password</span>
            <input className="input" readOnly value={temporaryPassword} onFocus={e => e.currentTarget.select()} /></label>
        </div> : <p>This immediately invalidates the user's old password and all existing sessions. Their role, company, and project access will not change.</p>}
      </Modal>}
    </>
  )
}

function AddUserModal({ onClose, onCreate, companies, pending }: {
  onClose: () => void
  onCreate: (body: CreateUserInput) => void
  companies: { id: string; company_name: string }[]
  pending: boolean
}) {
  const [form, setForm] = useState<CreateUserInput>({
    email: '', full_name: '', role: 'user', company_id: companies[0]?.id ?? null,
    temporary_password: '', must_change_password: true,
    trial_enabled: false, trial_days: 14, trial_start_date: today(),
    demo_company_access: false,
  })
  const set = (p: Partial<CreateUserInput>) => setForm((f) => ({ ...f, ...p }))
  return (
    <Modal title="Add User" open onClose={onClose} footer={
      <div className="row" style={{ gap: 8, justifyContent: 'flex-end', width: '100%' }}>
        <button className="btn btn--secondary" onClick={onClose}>Cancel</button>
        <button className="btn btn--primary" disabled={pending} onClick={() => onCreate({
          ...form, company_id: form.role === 'admin' ? null : form.company_id,
          // Only send trial fields when enabled.
          trial_enabled: form.role === 'admin' ? false : form.trial_enabled,
          trial_days: form.trial_enabled ? form.trial_days : undefined,
          trial_start_date: form.trial_enabled ? form.trial_start_date : undefined,
          demo_company_access: form.role === 'admin' ? false : form.demo_company_access,
        })}>{pending ? 'Creating…' : 'Create User'}</button>
      </div>
    }>
      <div className="stack--sm">
        <div className="field"><span className="field__label">Full name</span>
          <input className="input" value={form.full_name} onChange={(e) => set({ full_name: e.target.value })} /></div>
        <div className="field"><span className="field__label">Email *</span>
          <input className="input" type="email" value={form.email} onChange={(e) => set({ email: e.target.value })} /></div>
        <div className="field"><span className="field__label">Role</span>
          <select className="input" value={form.role} onChange={(e) => set({ role: e.target.value as Role })}>
            <option value="user">User</option><option value="admin">Admin</option>
          </select></div>
        {form.role === 'user' && (
          <div className="field"><span className="field__label">Assigned company *</span>
            <select className="input" value={form.company_id ?? ''} onChange={(e) => set({ company_id: e.target.value })}>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.company_name}</option>)}
            </select></div>
        )}
        <div className="field"><span className="field__label">Temporary password *</span>
          <input className="input" value={form.temporary_password} onChange={(e) => set({ temporary_password: e.target.value })}
            placeholder="Min 10 chars, upper/lower/number/special" /></div>
        <label className="row" style={{ gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={form.must_change_password} onChange={(e) => set({ must_change_password: e.target.checked })} />
          <span style={{ fontSize: 13.5 }}>Must change password on first login</span>
        </label>

        {form.role === 'user' && (
          <div className="banner banner--info" style={{ marginTop: 4, display: 'block' }}>
            <label className="row" style={{ gap: 8, alignItems: 'center' }}>
              <input type="checkbox" checked={!!form.demo_company_access} onChange={(e) => set({ demo_company_access: e.target.checked })} />
              <strong style={{ fontSize: 13.5 }}>Allow this user to access the AquaPure Smart Filters FZE demo company.</strong>
            </label>
            <div className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
              Demo access lets the user open the pre-filled AquaPure Smart Filters FZE example company and explore a completed business plan.
            </div>
          </div>
        )}

        {form.role === 'user' && (
          <div className="banner banner--info" style={{ marginTop: 4, display: 'block' }}>
            <label className="row" style={{ gap: 8, alignItems: 'center' }}>
              <input type="checkbox" checked={!!form.trial_enabled} onChange={(e) => set({ trial_enabled: e.target.checked })} />
              <strong style={{ fontSize: 13.5 }}>Enable trial access</strong>
            </label>
            {form.trial_enabled && (
              <div className="stack--sm" style={{ marginTop: 10 }}>
                <div className="row" style={{ gap: 10 }}>
                  <div className="field" style={{ flex: 1 }}><span className="field__label">Trial duration (days)</span>
                    <select className="input" value={form.trial_days ?? 14} onChange={(e) => set({ trial_days: Number(e.target.value) })}>
                      {DURATIONS.map((d) => <option key={d} value={d}>{d} days</option>)}
                    </select></div>
                  <div className="field" style={{ flex: 1 }}><span className="field__label">Trial start date</span>
                    <input className="input" type="date" value={form.trial_start_date ?? today()} onChange={(e) => set({ trial_start_date: e.target.value })} /></div>
                </div>
                <div className="muted" style={{ fontSize: 12.5 }}>
                  Trial end date (calculated): <strong>{calcEnd(form.trial_start_date ?? today(), form.trial_days ?? 0)}</strong>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  )
}

function TrialModal({ user, onClose }: { user: ManagedUser; onClose: () => void }) {
  const { notify } = useToast()
  const setTrial = useSetTrial()
  const extend = useExtendTrial()
  const end = useEndTrial()
  const [enabled, setEnabled] = useState<boolean>(!!user.trial_enabled)
  const [days, setDays] = useState<number>(user.trial_days ?? 14)
  const [start, setStart] = useState<string>(user.trial_start_date?.slice(0, 10) ?? today())
  const [extendDays, setExtendDays] = useState<number>(14)
  const st = statusOf(user)
  const busy = setTrial.isPending || extend.isPending || end.isPending

  const done = (msg: string) => { notify(msg); onClose() }
  const err = (e: unknown) => notify((e as Error).message, 'error')

  return (
    <Modal title={`Trial — ${user.email}`} open onClose={onClose} footer={
      <div className="row" style={{ gap: 8, justifyContent: 'space-between', width: '100%' }}>
        <button className="btn btn--ghost" disabled={busy || !user.trial_enabled}
          onClick={() => end.mutate(user.id, { onSuccess: () => done('Trial ended — full active user'), onError: err })}>
          End trial (make full user)
        </button>
        <div className="row" style={{ gap: 8 }}>
          <button className="btn btn--secondary" onClick={onClose}>Close</button>
          <button className="btn btn--primary" disabled={busy} onClick={() => setTrial.mutate(
            { id: user.id, body: { enabled, trial_days: enabled ? days : undefined, trial_start_date: enabled ? start : undefined } },
            { onSuccess: () => done('Trial settings saved'), onError: err })}>
            {setTrial.isPending ? 'Saving…' : 'Save trial settings'}
          </button>
        </div>
      </div>
    }>
      <div className="stack--sm">
        <div className="row" style={{ gap: 10, alignItems: 'center' }}>
          <span className="muted" style={{ fontSize: 13 }}>Current status:</span>
          <Badge tone={STATUS_TONE[st]} dot>{STATUS_LABEL[st]}</Badge>
          {user.trial_enabled && <span className="muted" style={{ fontSize: 13 }}>ends {fmtDate(user.trial_end_date)}</span>}
        </div>

        <label className="row" style={{ gap: 8, alignItems: 'center', marginTop: 6 }}>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          <strong style={{ fontSize: 13.5 }}>Enable trial access</strong>
        </label>
        {enabled && (
          <>
            <div className="row" style={{ gap: 10 }}>
              <div className="field" style={{ flex: 1 }}><span className="field__label">Trial duration (days)</span>
                <select className="input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                  {DURATIONS.map((d) => <option key={d} value={d}>{d} days</option>)}
                </select></div>
              <div className="field" style={{ flex: 1 }}><span className="field__label">Trial start date</span>
                <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} /></div>
            </div>
            <div className="muted" style={{ fontSize: 12.5 }}>
              Trial end date (calculated): <strong>{calcEnd(start, days)}</strong>
            </div>
          </>
        )}

        <div className="banner banner--info" style={{ marginTop: 8, display: 'block' }}>
          <div style={{ fontSize: 13, marginBottom: 8 }}><strong>Extend trial</strong> — adds days from the current end date (or revives an expired trial).</div>
          <div className="row" style={{ gap: 8, alignItems: 'flex-end' }}>
            <div className="field" style={{ width: 140, marginBottom: 0 }}><span className="field__label">Add days</span>
              <select className="input" value={extendDays} onChange={(e) => setExtendDays(Number(e.target.value))}>
                {DURATIONS.map((d) => <option key={d} value={d}>{d} days</option>)}
              </select></div>
            <button className="btn btn--secondary" disabled={busy} onClick={() => extend.mutate(
              { id: user.id, additional_days: extendDays },
              { onSuccess: () => done(`Trial extended by ${extendDays} days`), onError: err })}>
              {extend.isPending ? 'Extending…' : `Extend +${extendDays}d`}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}
