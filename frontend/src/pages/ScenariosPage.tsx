import { useEffect, useMemo, useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SaveBar } from '@/components/SaveBar'
import { SectionCard } from '@/components/SectionCard'
import { Modal } from '@/components/ui/Modal'
import { LoadingScreen } from '@/components/ui/Spinner'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import {
  useCollectionSection,
  useDeleteCollectionItem,
  useSaveCollectionItem,
} from '@/api/hooks'
import { useEnsureDefaultScenario, useSetDefaultScenario } from '@/api/scenariosApi'
import { useProjectContext } from '@/layouts/ProjectContext'
import { useToast } from '@/components/ui/Toast'
import { scenarioTypeOptions } from '@/utils/options'
import { formatDate } from '@/utils/format'
import type { ScenarioAssumption, ScenarioType } from '@/types'

const ADJUSTMENTS: { key: keyof ScenarioAssumption; label: string }[] = [
  { key: 'sales_volume_adjustment', label: 'Sales Volume' },
  { key: 'selling_price_adjustment', label: 'Selling Price' },
  { key: 'direct_cost_adjustment', label: 'Direct Costs' },
  { key: 'salary_adjustment', label: 'Salaries' },
  { key: 'rent_adjustment', label: 'Rent' },
  { key: 'marketing_adjustment', label: 'Marketing' },
  { key: 'customer_growth_adjustment', label: 'Customer Growth' },
  { key: 'collection_days_adjustment', label: 'Collection Days' },
  { key: 'inventory_days_adjustment', label: 'Inventory Days' },
  { key: 'interest_rate_adjustment', label: 'Interest Rate' },
  { key: 'exchange_rate_adjustment', label: 'Exchange Rate' },
  { key: 'tax_rate_adjustment', label: 'Tax Rate' },
  { key: 'inflation_adjustment', label: 'Inflation' },
]
const EXTREME = 50

type Draft = {
  name: string
  description: string
  scenario_type: ScenarioType
  adj: Record<string, number>
}

function toDraft(s?: ScenarioAssumption | null): Draft {
  return {
    name: s?.name || '',
    description: s?.description || '',
    scenario_type: (s?.scenario_type as ScenarioType) || 'custom',
    adj: Object.fromEntries(ADJUSTMENTS.map((a) => [a.key, Number(s?.[a.key]) || 0])),
  }
}

const typeLabel = (t: ScenarioType) => scenarioTypeOptions.find((o) => o.value === t)?.label ?? t

// -- Create / Edit modal ---------------------------------------------------
function ScenarioModal({ scenario, saving, onClose, onSubmit }: {
  scenario: ScenarioAssumption | null
  saving: boolean
  onClose: () => void
  onSubmit: (d: Draft) => void
}) {
  const [d, setD] = useState<Draft>(() => toDraft(scenario))
  const set = (p: Partial<Draft>) => setD((cur) => ({ ...cur, ...p }))
  const [warn, setWarn] = useState<string | null>(null)

  const submit = () => {
    if (!String(d.name).trim()) { setWarn('Enter a scenario name.'); return }
    onSubmit({ ...d, name: String(d.name).trim() })
  }

  return (
    <Modal open wide title={scenario ? 'Edit Scenario' : 'New Scenario'} onClose={onClose} footer={
      <div className="row row--between" style={{ width: '100%' }}>
        <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn--primary" disabled={saving} onClick={submit}>
          {saving ? 'Saving…' : scenario ? 'Save Changes' : 'Create Scenario'}
        </button>
      </div>
    }>
      {warn && <div className="banner banner--warning" style={{ marginBottom: 10 }}><span className="banner__icon">⚠</span><div>{warn}</div></div>}
      <div className="stack--sm">
        <div className="form-grid">
          <div className="field"><span className="field__label">Scenario name *</span>
            <input className="input" value={String(d.name)} onChange={(e) => set({ name: e.target.value })} placeholder="e.g. Investor Case" /></div>
          <div className="field"><span className="field__label">Type</span>
            <select className="input" value={d.scenario_type} onChange={(e) => set({ scenario_type: e.target.value as ScenarioType })}>
              {scenarioTypeOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select></div>
          <div className="field" style={{ gridColumn: '1 / -1' }}><span className="field__label">Description (optional)</span>
            <input className="input" value={String(d.description)} onChange={(e) => set({ description: e.target.value })} placeholder="What this scenario represents" /></div>
        </div>

        <SectionCard title="Assumption adjustments" subtitle="Percentage change vs. the base plan. 0% = same as base." icon="⊟">
          <div className="form-grid">
            {ADJUSTMENTS.map((a) => {
              const k = a.key as string
              const value = d.adj[k] ?? 0
              const extreme = Math.abs(value) >= EXTREME
              const setAdj = (v: number) => set({ adj: { ...d.adj, [k]: v } })
              return (
                <div className="field" key={k}>
                  <label className="field__label">{a.label}
                    <span style={{ marginLeft: 'auto', fontWeight: 700, color: extreme ? 'var(--amber-600)' : 'var(--text-primary)' }}>
                      {value > 0 ? '+' : ''}{value}%
                    </span>
                  </label>
                  <div className="slider-row">
                    <input className="slider" type="range" min={-100} max={100} step={1}
                      value={value} onChange={(e) => setAdj(Number(e.target.value))} />
                    <input className="input" type="number" value={value}
                      onChange={(e) => setAdj(Number(e.target.value) || 0)} />
                  </div>
                </div>
              )
            })}
          </div>
        </SectionCard>
      </div>
    </Modal>
  )
}

// -- Page ------------------------------------------------------------------
export function ScenariosPage() {
  const { projectId } = useProjectContext()
  const { data, isLoading } = useCollectionSection<ScenarioAssumption>(projectId, 'scenarios')
  const save = useSaveCollectionItem<ScenarioAssumption>(projectId, 'scenarios')
  const del = useDeleteCollectionItem(projectId, 'scenarios')
  const ensureDefault = useEnsureDefaultScenario(projectId)
  const setDefault = useSetDefaultScenario(projectId)
  const { notify } = useToast()

  const [modal, setModal] = useState<{ open: boolean; scenario: ScenarioAssumption | null }>({ open: false, scenario: null })

  const scenarios = useMemo(() => data ?? [], [data])

  // Backfill a default Base Case for older projects on first open.
  useEffect(() => {
    if (!isLoading && data && data.length === 0) ensureDefault.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, data])

  if (isLoading) return <LoadingScreen />

  const handleSubmit = (draft: Draft) => {
    const base = modal.scenario ?? {}
    const { adj, ...top } = draft
    const payload = { ...base, ...top, ...adj } as unknown as ScenarioAssumption
    save.mutate(payload, {
      onSuccess: () => { notify(modal.scenario ? 'Scenario updated' : 'Scenario created'); setModal({ open: false, scenario: null }) },
      onError: (e) => notify((e as Error).message || 'Save failed', 'error'),
    })
  }

  const duplicate = (s: ScenarioAssumption) => {
    const { id: _id, created_at: _c, updated_at: _u, ...rest } = s
    void _id; void _c; void _u
    save.mutate({ ...rest, name: `${s.name || typeLabel(s.scenario_type)} (copy)`, is_default: false } as ScenarioAssumption, {
      onSuccess: () => notify('Scenario duplicated'),
      onError: (e) => notify((e as Error).message || 'Duplicate failed', 'error'),
    })
  }

  const remove = (s: ScenarioAssumption) => {
    if (s.is_default) { notify('Set another scenario as default before deleting this one.', 'error'); return }
    if (!window.confirm(`Delete scenario “${s.name || typeLabel(s.scenario_type)}”? This cannot be undone.`)) return
    del.mutate(s.id, { onSuccess: () => notify('Scenario deleted'), onError: (e) => notify((e as Error).message || 'Delete failed', 'error') })
  }

  const makeDefault = (s: ScenarioAssumption) => {
    setDefault.mutate(s.id, { onSuccess: () => notify(`“${s.name}” is now the default`), onError: (e) => notify((e as Error).message || 'Failed', 'error') })
  }

  return (
    <>
      <PageHeader
        breadcrumb="Business Plan · Planning"
        title="Scenarios"
        subtitle="Save multiple named scenarios per plan. Each keeps its own assumptions; the base plan is never overwritten."
        actions={<button className="btn btn--primary" onClick={() => setModal({ open: true, scenario: null })}>+ New Scenario</button>}
      />

      <div className="stack">
        <SectionCard title="Saved Scenarios" subtitle={`${scenarios.length} scenario${scenarios.length === 1 ? '' : 's'}`} icon="⊡"
          actions={<button className="btn btn--secondary btn--sm" onClick={() => setModal({ open: true, scenario: null })}>+ New</button>}>
          {scenarios.length === 0 ? (
            <EmptyState icon="⊡" title="No scenarios yet" description="Create a scenario to model optimistic, conservative, or custom cases." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr>
                  <th>Scenario Name</th><th>Type</th><th>Description</th><th>Last Updated</th>
                  <th style={{ textAlign: 'center' }}>Default?</th><th style={{ textAlign: 'right' }}>Actions</th>
                </tr></thead>
                <tbody>
                  {scenarios.map((s) => (
                    <tr key={s.id}>
                      <td><strong>{s.name || typeLabel(s.scenario_type)}</strong></td>
                      <td><Badge tone="blue">{typeLabel(s.scenario_type)}</Badge></td>
                      <td className="muted" style={{ maxWidth: 260 }}>{s.description || '—'}</td>
                      <td>{formatDate(s.updated_at)}</td>
                      <td style={{ textAlign: 'center' }}>
                        {s.is_default
                          ? <Badge tone="green" dot>Default</Badge>
                          : <button className="btn btn--ghost btn--sm" onClick={() => makeDefault(s)}>Set default</button>}
                      </td>
                      <td>
                        <div className="row" style={{ gap: 4, justifyContent: 'flex-end' }}>
                          <button className="btn btn--ghost btn--sm" onClick={() => setModal({ open: true, scenario: s })}>✏️ Open</button>
                          <button className="btn btn--ghost btn--sm" onClick={() => duplicate(s)}>⧉ Duplicate</button>
                          <button className="btn btn--ghost btn--sm" title="Side-by-side comparison — coming next" disabled>⊟ Compare</button>
                          <button className="btn btn--ghost btn--sm" onClick={() => remove(s)}>🗑 Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {scenarios.length > 0 && (
          <SectionCard title="Adjustments Overview" subtitle="All saved scenarios side by side." icon="⊟">
            <div className="table-wrap">
              <table className="table">
                <thead><tr>
                  <th>Adjustment</th>
                  {scenarios.map((s) => <th key={s.id} style={{ textAlign: 'right' }}>{s.name || typeLabel(s.scenario_type)}</th>)}
                </tr></thead>
                <tbody>
                  {ADJUSTMENTS.map((a) => (
                    <tr key={a.key as string}>
                      <td>{a.label}</td>
                      {scenarios.map((s) => {
                        const v = Number(s[a.key]) || 0
                        return (
                          <td key={s.id} className="table__num">
                            {v === 0 ? <span className="muted">—</span> : <Badge tone={v > 0 ? 'green' : 'amber'}>{v > 0 ? '+' : ''}{v}%</Badge>}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
      </div>

      {modal.open && (
        <ScenarioModal
          key={modal.scenario?.id ?? 'new'}
          scenario={modal.scenario}
          saving={save.isPending}
          onClose={() => setModal({ open: false, scenario: null })}
          onSubmit={handleSubmit}
        />
      )}

      <SaveBar slug="scenarios" />
    </>
  )
}
