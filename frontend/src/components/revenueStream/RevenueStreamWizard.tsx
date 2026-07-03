import { useMemo, useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { SectionCard } from '@/components/SectionCard'
import { Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { useProjectContext } from '@/layouts/ProjectContext'
import {
  useCollectionSection,
  useDeleteCollectionItem,
  useSaveCollectionItem,
  useSingletonSection,
} from '@/api/hooks'
import { useRefreshRevenueDependents, useRevenueStreamsForecast } from '@/api/revenueStreamsApi'
import { formatCurrency } from '@/utils/format'
import type {
  BillingFrequency, ForecastInputMethod, ProjectSetup, RevenueStream, RevenueStreamType,
} from '@/types'

const TYPES: { value: RevenueStreamType; label: string; blurb: string; formula: string }[] = [
  { value: 'unit_sales', label: 'Unit Sales', blurb: 'Sell a number of units at a price.', formula: 'revenue = units × unit price' },
  { value: 'billable_hours', label: 'Billable Hours', blurb: 'Bill hours at an hourly rate.', formula: 'revenue = hours × hourly rate' },
  { value: 'recurring_charges', label: 'Recurring Charges', blurb: 'Subscriptions with signups & churn.', formula: 'active customers × charge (+ upfront)' },
  { value: 'revenue_only', label: 'Revenue Only', blurb: 'Enter total revenue directly.', formula: 'revenue entered per period' },
]
const TYPE_LABEL: Record<RevenueStreamType, string> = {
  unit_sales: 'Unit Sales', billable_hours: 'Billable Hours', recurring_charges: 'Recurring Charges', revenue_only: 'Revenue Only',
}

const yearsFromPeriod = (p?: string | null) => (p === '3_years' ? 3 : p === '10_years' ? 10 : 5)

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const round2 = (n: number) => Math.round(n * 100) / 100

// -- blank stream ----------------------------------------------------------
function blank(): Partial<RevenueStream> {
  return {
    name: '', stream_type: 'unit_sales', active: true,
    quantity_method: 'constant', quantity_constant: 0, quantity_monthly: [],
    price_method: 'constant', price_constant: 0, price_monthly: [],
    initial_customers: 0, signups_method: 'constant', signups_constant: 0, signups_monthly: [],
    recurring_charge: 0, billing_frequency: 'monthly', upfront_fee: 0, churn_rate_percent: 0,
    revenue_method: 'constant', revenue_constant: 0, revenue_monthly: [],
  }
}

// -- spreadsheet grid for a "varying over time" driver ---------------------
// Years as rows, months as columns, with a per-year Total and Y/Y% growth.
// Values are stored at monthly resolution (length = years × 12) so the backend
// forecast keeps working unchanged. In yearly granularity the same data is
// entered as annual totals that spread evenly across the twelve months.
function VaryingGrid({ values, setValues, years, startYear, granularity, unit }: {
  values: number[]
  setValues: (v: number[]) => void
  years: number
  startYear: number
  granularity: 'monthly' | 'yearly'
  unit?: string
}) {
  const n = years * 12
  const cells = useMemo(() => {
    const arr = (values ?? []).slice(0, n)
    while (arr.length < n) arr.push(0)
    return arr
  }, [values, n])

  const yearTotal = (y: number) => {
    let s = 0
    for (let mo = 0; mo < 12; mo++) s += cells[y * 12 + mo] ?? 0
    return s
  }
  // Year-over-year growth of the annual total, with a sign + colour direction.
  const yoy = (y: number): { label: string; cls: string } => {
    if (y === 0) return { label: '—', cls: '' }
    const prev = yearTotal(y - 1)
    if (!prev) return { label: '—', cls: '' }
    const pct = ((yearTotal(y) - prev) / prev) * 100
    const label = `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`
    return { label, cls: pct > 0 ? 'vgrid__yoy--up' : pct < 0 ? 'vgrid__yoy--down' : '' }
  }
  const writeMonth = (y: number, mo: number, val: number) => {
    const next = cells.slice(); next[y * 12 + mo] = val; setValues(next)
  }
  const writeYear = (y: number, total: number) => {
    const per = total / 12
    const next = cells.slice()
    for (let mo = 0; mo < 12; mo++) next[y * 12 + mo] = per
    setValues(next)
  }

  if (granularity === 'yearly') {
    return (
      <>
        <div className="vgrid-wrap">
          <table className="vgrid">
            <thead><tr>
              <th className="vgrid__yhead">Year</th>
              <th className="vgrid__thead">Annual total{unit ? ` · ${unit}` : ''}</th>
              <th>Y/Y%</th>
            </tr></thead>
            <tbody>
              {Array.from({ length: years }, (_, y) => {
                const g = yoy(y)
                return (
                  <tr key={y}>
                    <td className="vgrid__year">{startYear + y}</td>
                    <td>
                      <input className="vgrid__cell" type="number" value={round2(yearTotal(y))}
                        onChange={(e) => writeYear(y, Number(e.target.value) || 0)} />
                    </td>
                    <td className={`vgrid__yoy ${g.cls}`}>{g.label}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <p className="vgrid__hint">Annual totals spread evenly across the year. Switch to <strong>Monthly</strong> to enter each month.</p>
      </>
    )
  }

  return (
    <div className="vgrid-wrap">
      <table className="vgrid">
        <thead><tr>
          <th className="vgrid__yhead">Year</th>
          {MONTHS.map((m) => <th key={m}>{m}</th>)}
          <th className="vgrid__thead">Total{unit ? ` · ${unit}` : ''}</th>
          <th>Y/Y%</th>
        </tr></thead>
        <tbody>
          {Array.from({ length: years }, (_, y) => {
            const g = yoy(y)
            return (
              <tr key={y}>
                <td className="vgrid__year">{startYear + y}</td>
                {MONTHS.map((_, mo) => (
                  <td key={mo}>
                    <input className="vgrid__cell" type="number" value={cells[y * 12 + mo] ?? 0}
                      onChange={(e) => writeMonth(y, mo, Number(e.target.value) || 0)} />
                  </td>
                ))}
                <td className="vgrid__total">{round2(yearTotal(y))}</td>
                <td className={`vgrid__yoy ${g.cls}`}>{g.label}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// -- a constant | varying driver: single field, or the spreadsheet grid ----
function DriverInput({ label, method, setMethod, constant, setConstant, values, setValues, years, startYear, granularity, unit }: {
  label: string
  method: ForecastInputMethod
  setMethod: (m: ForecastInputMethod) => void
  constant: number
  setConstant: (n: number) => void
  values: number[]
  setValues: (v: number[]) => void
  years: number
  startYear: number
  granularity: 'monthly' | 'yearly'
  unit?: string
}) {
  return (
    <div className="field" style={{ marginBottom: 4 }}>
      <div className="row row--between" style={{ alignItems: 'center' }}>
        <span className="field__label">{label}{unit ? ` (${unit})` : ''}</span>
        <div className="segmented">
          <button type="button" className={`segmented__btn${method === 'constant' ? ' segmented__btn--active' : ''}`} onClick={() => setMethod('constant')}>Constant</button>
          <button type="button" className={`segmented__btn${method === 'varying' ? ' segmented__btn--active' : ''}`} onClick={() => setMethod('varying')}>Varying over time</button>
        </div>
      </div>
      {method === 'constant' ? (
        <input className="input" type="number" value={constant} onChange={(e) => setConstant(Number(e.target.value) || 0)} />
      ) : (
        <VaryingGrid values={values} setValues={setValues} years={years} startYear={startYear} granularity={granularity} unit={unit} />
      )}
    </div>
  )
}

// -- the wizard modal (create + edit) --------------------------------------
function Wizard({ years, startYear, currency, onClose, onSubmit, saving, initial }: {
  years: number
  startYear: number
  currency: string
  onClose: () => void
  onSubmit: (body: Partial<RevenueStream>) => void
  saving: boolean
  initial?: RevenueStream | null
}) {
  const isEdit = !!initial?.id
  // Varying drivers are entered in the month-by-month spreadsheet grid, so
  // default to the monthly view; the toggle can still summarise annual totals.
  const [view, setView] = useState<'yearly' | 'monthly'>('monthly')
  const [step, setStep] = useState(0)
  // Merge onto blank() so streams created before a field existed still populate.
  const [f, setF] = useState<Partial<RevenueStream>>(() => (initial ? { ...blank(), ...initial } : blank()))
  const [warn, setWarn] = useState<string | null>(null)
  const set = (p: Partial<RevenueStream>) => setF((cur) => ({ ...cur, ...p }))

  // Varying values are always stored at monthly resolution (years × 12) so the
  // backend forecast reads them directly, regardless of the view toggle.
  const ensureMonthly = (v?: number[]) => {
    const n = years * 12
    const arr = (v ?? []).slice(0, n)
    while (arr.length < n) arr.push(0)
    return arr
  }

  // Steps per type.
  const t = f.stream_type as RevenueStreamType
  const steps: { key: string; title: string; render: () => JSX.Element; valid: () => string | null }[] = []
  steps.push({
    key: 'type', title: 'Type & name',
    render: () => (
      <div className="stack--sm">
        <div className="field"><span className="field__label">Stream name *</span>
          <input className="input" value={f.name ?? ''} onChange={(e) => set({ name: e.target.value })} placeholder="e.g. Pro Subscriptions" /></div>
        <div className="field"><span className="field__label">Forecast type</span>
          <div className="stack--sm">
            {TYPES.map((ty) => (
              <label key={ty.value} className={`card${t === ty.value ? ' card--selected' : ''}`} style={{ padding: 12, cursor: 'pointer', border: t === ty.value ? '2px solid var(--blue-500,#3b6ef5)' : '1px solid var(--border,#e3e6ea)' }}>
                <div className="row" style={{ gap: 10, alignItems: 'flex-start' }}>
                  <input type="radio" checked={t === ty.value} onChange={() => set({ stream_type: ty.value })} style={{ marginTop: 3 }} />
                  <div>
                    <strong>{ty.label}</strong>
                    <div className="muted" style={{ fontSize: 12.5 }}>{ty.blurb} — <em>{ty.formula}</em></div>
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      </div>
    ),
    valid: () => (f.name?.trim() ? null : 'Enter a stream name.'),
  })

  if (t === 'unit_sales' || t === 'billable_hours') {
    const qtyUnit = t === 'billable_hours' ? 'hours' : 'units'
    const priceLabel = t === 'billable_hours' ? 'Hourly Rate' : 'Unit Price'
    steps.push({
      key: 'qty', title: t === 'billable_hours' ? 'Billable Hours' : 'Unit Sales',
      render: () => <DriverInput label={t === 'billable_hours' ? 'Billable hours' : 'Units sold'} unit={qtyUnit}
        method={f.quantity_method!} setMethod={(m) => set({ quantity_method: m })}
        constant={f.quantity_constant ?? 0} setConstant={(n) => set({ quantity_constant: n })}
        values={f.quantity_monthly ?? []} setValues={(v) => set({ quantity_monthly: v })}
        years={years} startYear={startYear} granularity={view} />,
      valid: () => (f.quantity_method === 'constant' && !(f.quantity_constant! > 0) ? `Enter the ${qtyUnit}.` : null),
    })
    steps.push({
      key: 'price', title: priceLabel,
      render: () => <DriverInput label={priceLabel} unit={currency}
        method={f.price_method!} setMethod={(m) => set({ price_method: m })}
        constant={f.price_constant ?? 0} setConstant={(n) => set({ price_constant: n })}
        values={f.price_monthly ?? []} setValues={(v) => set({ price_monthly: v })}
        years={years} startYear={startYear} granularity={view} />,
      valid: () => (f.price_method === 'constant' && !(f.price_constant! > 0) ? `Enter the ${priceLabel.toLowerCase()}.` : null),
    })
  }

  if (t === 'recurring_charges') {
    steps.push({
      key: 'signups', title: 'Signups',
      render: () => (
        <div className="stack--sm">
          <div className="field"><span className="field__label">Starting customers</span>
            <input className="input" type="number" value={f.initial_customers ?? 0} onChange={(e) => set({ initial_customers: Number(e.target.value) || 0 })} /></div>
          <DriverInput label="New signups per period" unit="customers"
            method={f.signups_method!} setMethod={(m) => set({ signups_method: m })}
            constant={f.signups_constant ?? 0} setConstant={(n) => set({ signups_constant: n })}
            values={f.signups_monthly ?? []} setValues={(v) => set({ signups_monthly: v })}
            years={years} startYear={startYear} granularity={view} />
        </div>
      ),
      valid: () => null,
    })
    steps.push({
      key: 'charges', title: 'Charges',
      render: () => (
        <div className="stack--sm">
          <div className="field"><span className="field__label">Recurring charge ({currency}) *</span>
            <input className="input" type="number" value={f.recurring_charge ?? 0} onChange={(e) => set({ recurring_charge: Number(e.target.value) || 0 })} /></div>
          <div className="field"><span className="field__label">Billing frequency</span>
            <select className="input" value={f.billing_frequency} onChange={(e) => set({ billing_frequency: e.target.value as BillingFrequency })}>
              <option value="monthly">Monthly</option><option value="yearly">Yearly</option></select></div>
          <div className="field"><span className="field__label">Upfront fee per signup ({currency}, optional)</span>
            <input className="input" type="number" value={f.upfront_fee ?? 0} onChange={(e) => set({ upfront_fee: Number(e.target.value) || 0 })} /></div>
        </div>
      ),
      valid: () => (f.recurring_charge! > 0 ? null : 'Enter the recurring charge.'),
    })
    steps.push({
      key: 'churn', title: 'Churn',
      render: () => (
        <div className="field"><span className="field__label">Monthly churn rate (%)</span>
          <input className="input" type="number" value={f.churn_rate_percent ?? 0} onChange={(e) => set({ churn_rate_percent: Number(e.target.value) || 0 })} />
          <span className="field__hint">Share of customers lost each month.</span></div>
      ),
      valid: () => null,
    })
  }

  if (t === 'revenue_only') {
    steps.push({
      key: 'revenue', title: 'Revenue',
      render: () => <DriverInput label="Total revenue" unit={currency}
        method={f.revenue_method!} setMethod={(m) => set({ revenue_method: m })}
        constant={f.revenue_constant ?? 0} setConstant={(n) => set({ revenue_constant: n })}
        values={f.revenue_monthly ?? []} setValues={(v) => set({ revenue_monthly: v })}
        years={years} startYear={startYear} granularity={view} />,
      valid: () => (f.revenue_method === 'constant' && !(f.revenue_constant! > 0) ? 'Enter the revenue amount.' : null),
    })
  }

  const isLast = step === steps.length - 1
  const next = () => {
    const msg = steps[step].valid()
    if (msg) { setWarn(msg); return }
    setWarn(null); setStep((s) => Math.min(s + 1, steps.length - 1))
  }
  const back = () => { setWarn(null); setStep((s) => Math.max(s - 1, 0)) }

  const submit = () => {
    // validate every step
    for (let i = 0; i < steps.length; i++) {
      const m = steps[i].valid()
      if (m) { setStep(i); setWarn(m); return }
    }
    const body: Partial<RevenueStream> = { ...f }
    // Varying drivers are already monthly from the grid; just pad/trim to the
    // exact projection length (years × 12) before saving.
    if (f.quantity_method === 'varying') body.quantity_monthly = ensureMonthly(f.quantity_monthly)
    if (f.price_method === 'varying') body.price_monthly = ensureMonthly(f.price_monthly)
    if (f.signups_method === 'varying') body.signups_monthly = ensureMonthly(f.signups_monthly)
    if (f.revenue_method === 'varying') body.revenue_monthly = ensureMonthly(f.revenue_monthly)
    // body carries `id` when editing (merged from `initial`), so the save hook
    // PUTs to update the existing stream instead of POSTing a duplicate.
    onSubmit(body)
  }

  return (
    <Modal open wide title={isEdit ? 'Edit Revenue Stream' : 'Add Revenue Stream'} onClose={onClose} footer={
      <div className="row row--between" style={{ width: '100%' }}>
        <button className="btn btn--ghost" onClick={onClose}>Discard &amp; Exit</button>
        <div className="row" style={{ gap: 8 }}>
          {step > 0 && <button className="btn btn--secondary" onClick={back}>← Back</button>}
          {!isLast
            ? <button className="btn btn--primary" onClick={next}>Next →</button>
            : <button className="btn btn--primary" disabled={saving} onClick={submit}>
                {saving ? (isEdit ? 'Saving…' : 'Creating…') : (isEdit ? 'Save Changes' : 'Create & Exit')}
              </button>}
        </div>
      </div>
    }>
      <div className="row row--between" style={{ marginBottom: 12, alignItems: 'center' }}>
        <div className="row" style={{ gap: 6 }}>
          {steps.map((s, i) => (
            <span key={s.key} className={`badge ${i === step ? 'badge--blue' : 'badge--neutral'}`}>{i + 1}. {s.title}</span>
          ))}
        </div>
        <div className="segmented">
          <button type="button" className={`segmented__btn${view === 'yearly' ? ' segmented__btn--active' : ''}`} onClick={() => setView('yearly')}>Yearly</button>
          <button type="button" className={`segmented__btn${view === 'monthly' ? ' segmented__btn--active' : ''}`} onClick={() => setView('monthly')}>Monthly</button>
        </div>
      </div>
      {warn && <div className="banner banner--warning" style={{ marginBottom: 10 }}><span className="banner__icon">⚠</span><div>{warn}</div></div>}
      {steps[step].render()}
    </Modal>
  )
}

// -- details / forecast viewer --------------------------------------------
function methodSummary(method: ForecastInputMethod, constant: number, monthly: number[]) {
  return method === 'constant' ? `Constant · ${constant}` : `Varying · ${monthly.length} periods`
}

function DetailsModal({ stream, row, periods, currency, onClose, onEdit }: {
  stream: RevenueStream
  row?: { values: number[]; total: number } | null
  periods: string[]
  currency: string
  onClose: () => void
  onEdit: () => void
}) {
  const t = stream.stream_type
  return (
    <Modal open title={`Details — ${stream.name}`} onClose={onClose} footer={
      <div className="row row--between" style={{ width: '100%' }}>
        <button className="btn btn--ghost" onClick={onClose}>Close</button>
        <button className="btn btn--primary" onClick={onEdit}>Edit</button>
      </div>
    }>
      <div className="stack--sm">
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <Badge tone="blue">{TYPE_LABEL[t]}</Badge>
          {!stream.active && <Badge tone="neutral">Inactive</Badge>}
        </div>
        <ul className="muted" style={{ fontSize: 13, lineHeight: 1.8, margin: 0, paddingLeft: 18 }}>
          {(t === 'unit_sales' || t === 'billable_hours') && <>
            <li>{t === 'billable_hours' ? 'Billable hours' : 'Units sold'}: {methodSummary(stream.quantity_method, stream.quantity_constant, stream.quantity_monthly)}</li>
            <li>{t === 'billable_hours' ? 'Hourly rate' : 'Unit price'}: {methodSummary(stream.price_method, stream.price_constant, stream.price_monthly)}</li>
          </>}
          {t === 'recurring_charges' && <>
            <li>Starting customers: {stream.initial_customers}</li>
            <li>New signups: {methodSummary(stream.signups_method, stream.signups_constant, stream.signups_monthly)}</li>
            <li>Recurring charge: {formatCurrency(stream.recurring_charge, currency)} · billed {stream.billing_frequency}</li>
            <li>Upfront fee per signup: {formatCurrency(stream.upfront_fee, currency)}</li>
            <li>Monthly churn: {stream.churn_rate_percent}%</li>
          </>}
          {t === 'revenue_only' && <li>Total revenue: {methodSummary(stream.revenue_method, stream.revenue_constant, stream.revenue_monthly)}</li>}
        </ul>
        {row ? (
          <div className="table-wrap" style={{ maxHeight: 240, overflow: 'auto' }}>
            <table className="table">
              <thead><tr>{periods.map((p) => <th key={p} style={{ textAlign: 'right' }}>{p}</th>)}<th style={{ textAlign: 'right' }}>Total</th></tr></thead>
              <tbody><tr>
                {row.values.map((v, i) => <td key={i} className="table__num">{formatCurrency(v, currency)}</td>)}
                <td className="table__num"><strong>{formatCurrency(row.total, currency)}</strong></td>
              </tr></tbody>
            </table>
          </div>
        ) : <p className="muted" style={{ fontSize: 12.5 }}>Forecast not available yet.</p>}
      </div>
    </Modal>
  )
}

// -- panel: list + totals + row actions (view / edit / delete) -------------
export function RevenueStreamsSection() {
  const { projectId, currency } = useProjectContext()
  const { notify } = useToast()
  const streamsQ = useCollectionSection<RevenueStream>(projectId, 'revenue-streams')
  const setupQ = useSingletonSection<ProjectSetup>(projectId, 'setup')
  const [view, setView] = useState<'yearly' | 'monthly'>('yearly')
  const forecastQ = useRevenueStreamsForecast(projectId, view)
  const save = useSaveCollectionItem<RevenueStream>(projectId, 'revenue-streams')
  const del = useDeleteCollectionItem(projectId, 'revenue-streams')
  const refreshDependents = useRefreshRevenueDependents(projectId)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<RevenueStream | null>(null)
  const [viewing, setViewing] = useState<RevenueStream | null>(null)

  const years = yearsFromPeriod(setupQ.data?.projection_period)
  const startYear = setupQ.data?.projection_start_date ? new Date(setupQ.data.projection_start_date).getFullYear() : 2025
  const streams = streamsQ.data ?? []
  const fc = forecastQ.data
  const streamById = (id: string) => streams.find((s) => s.id === id) ?? null

  const closeWizard = () => { setCreating(false); setEditing(null) }
  const removeStream = (id: string, name: string) => {
    if (!window.confirm(`Delete “${name}”? This permanently removes the revenue stream and cannot be undone.`)) return
    del.mutate(id, {
      onSuccess: () => { refreshDependents(); notify('Revenue stream deleted') },
      onError: (e) => notify((e as Error).message || 'Delete failed', 'error'),
    })
  }

  return (
    <SectionCard title="Revenue Streams" subtitle="Guided forecast builder — add unit sales, billable hours, recurring charges, or direct revenue." icon="◴"
      actions={<>
        <div className="segmented">
          <button type="button" className={`segmented__btn${view === 'yearly' ? ' segmented__btn--active' : ''}`} onClick={() => setView('yearly')}>Yearly</button>
          <button type="button" className={`segmented__btn${view === 'monthly' ? ' segmented__btn--active' : ''}`} onClick={() => setView('monthly')}>Monthly</button>
        </div>
        <button className="btn btn--primary btn--sm" onClick={() => setCreating(true)}>+ Add Revenue Stream</button>
      </>}>
      {streams.length === 0 ? (
        <p className="muted" style={{ fontSize: 13 }}>No revenue streams yet. Click <strong>+ Add Revenue Stream</strong> to build one with the wizard.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Stream</th><th>Type</th>{(fc?.periods ?? []).map((p) => <th key={p} style={{ textAlign: 'right' }}>{p}</th>)}<th style={{ textAlign: 'right' }}>Total</th><th style={{ textAlign: 'right' }}>Actions</th></tr></thead>
            <tbody>
              {(fc?.rows ?? []).map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.name}</strong></td>
                  <td><Badge tone="blue">{TYPE_LABEL[r.stream_type]}</Badge></td>
                  {r.values.map((v, i) => <td key={i} className="table__num">{formatCurrency(v, currency)}</td>)}
                  <td className="table__num"><strong>{formatCurrency(r.total, currency)}</strong></td>
                  <td>
                    <div className="row" style={{ gap: 4, justifyContent: 'flex-end' }}>
                      <button className="btn btn--ghost btn--sm" title="View details / forecast" aria-label={`View ${r.name}`}
                        onClick={() => setViewing(streamById(r.id))} disabled={!streamById(r.id)}>👁 View</button>
                      <button className="btn btn--ghost btn--sm" title="Edit this revenue stream" aria-label={`Edit ${r.name}`}
                        onClick={() => { const s = streamById(r.id); s ? setEditing(s) : notify('Stream is still loading — try again.', 'error') }} disabled={!streamById(r.id)}>✏️ Edit</button>
                      <button className="btn btn--ghost btn--sm" title="Delete this revenue stream" aria-label={`Delete ${r.name}`}
                        onClick={() => removeStream(r.id, r.name)}>🗑 Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {fc && fc.rows.length > 0 && (
                <tr>
                  <td colSpan={2}><strong>Total revenue</strong></td>
                  {fc.totals_by_period.map((v, i) => <td key={i} className="table__num"><strong>{formatCurrency(v, currency)}</strong></td>)}
                  <td className="table__num"><strong>{formatCurrency(fc.grand_total, currency)}</strong></td>
                  <td></td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {(creating || editing) && (
        <Wizard key={editing?.id ?? 'new'} years={years} startYear={startYear} currency={currency} saving={save.isPending}
          initial={editing}
          onClose={closeWizard}
          onSubmit={(body) => save.mutate(body as RevenueStream, {
            onSuccess: () => {
              refreshDependents()
              notify(editing ? 'Revenue stream updated' : 'Revenue stream created')
              closeWizard()
            },
            onError: (e) => notify((e as Error).message || 'Save failed', 'error'),
          })} />
      )}

      {viewing && (
        <DetailsModal stream={viewing} row={fc?.rows.find((r) => r.id === viewing.id) ?? null}
          periods={fc?.periods ?? []} currency={currency}
          onClose={() => setViewing(null)}
          onEdit={() => { setEditing(viewing); setViewing(null) }} />
      )}
    </SectionCard>
  )
}
