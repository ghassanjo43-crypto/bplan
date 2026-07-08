import { useState } from 'react'
import { SectionCard } from '@/components/SectionCard'
import { LoadingScreen, Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { useProjectionGrid, useSaveCells } from '@/api/projectionApi'
import type { GridCell, ProjectionMode, ProjectionSection } from '@/types/projection'
import { PRIMARY_FIELD } from '@/types/projection'
import { formatStatementNumber } from '@/utils/statementFormat'
import { computeGrowth, growthKey, numStr, type GrowthScope } from './growth'
import { buildProjectionCsv, downloadCsv } from './projectionCsv'

const SECTION_LABEL: Record<ProjectionSection, { driver: string; totalNoun: string; growthVerb: string }> = {
  revenue: { driver: 'units', totalNoun: 'net revenue', growthVerb: 'growth' },
  direct_costs: { driver: 'cost', totalNoun: 'cost of sales', growthVerb: 'inflation' },
  operating_expenses: { driver: 'amount', totalNoun: 'operating expense', growthVerb: 'inflation' },
}

/** Filename prefix used for CSV export, e.g. "revenue-projection-monthly.csv". */
const CSV_FILE_PREFIX: Record<ProjectionSection, string> = {
  revenue: 'revenue-projection',
  direct_costs: 'direct-cost-projection',
  operating_expenses: 'operating-expense-projection',
}

function cellDriver(section: ProjectionSection, c: GridCell): number {
  if (section === 'revenue') return c.quantity ?? 0
  if (section === 'operating_expenses') return c.amount ?? 0
  return c.value // direct costs: edit the final cost (creates a manual override)
}

export function ProjectionGrid({
  projectId,
  section,
}: {
  projectId: string
  section: ProjectionSection
}) {
  const [mode, setMode] = useState<ProjectionMode>('monthly')
  const { data: grid, isLoading, isError, error, refetch } = useProjectionGrid(projectId, section, mode)
  const saveCells = useSaveCells(projectId, section)
  const { notify } = useToast()

  // edited values keyed by `${item_id}:${period_index}` -> raw string
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<{ item: string; period: number } | null>(null)
  // The row targeted by row-level actions (Apply growth to "selected row").
  const [selectedRow, setSelectedRow] = useState<string | null>(null)
  const [scope, setScope] = useState<GrowthScope>('all')
  const [growthPct, setGrowthPct] = useState('')
  const [baseVal, setBaseVal] = useState('')

  const labels = SECTION_LABEL[section]
  const dirty = Object.keys(edits).length > 0
  const resetEdits = () => setEdits({})

  const periodCount = grid?.periods.length ?? 0
  const keyOf = growthKey

  const selectRow = (item: string) => setSelectedRow((cur) => (cur === item ? null : item))

  const valueFor = (item: string, c: GridCell): string => {
    const k = keyOf(item, c.period_index)
    return k in edits ? edits[k] : numStr(cellDriver(section, c))
  }

  const save = () => {
    const field = PRIMARY_FIELD[section]
    const cells = Object.entries(edits).map(([key, raw]) => {
      const idx = key.lastIndexOf(':')
      const item_id = key.slice(0, idx)
      const period_index = Number(key.slice(idx + 1))
      const num = Number(String(raw).replace(/,/g, ''))
      return { item_id, period_index, [field]: Number.isNaN(num) ? 0 : num }
    })
    if (cells.length === 0) return
    saveCells.mutate(
      { mode, cells },
      {
        onSuccess: () => {
          notify(`Saved ${cells.length} cell${cells.length === 1 ? '' : 's'}`)
          resetEdits()
        },
        onError: (e) => notify((e as Error).message || 'Save failed', 'error'),
      },
    )
  }

  // -- client-side helpers (operate on what you see; then Save) -------------
  const fillRight = () => {
    if (!grid || !selected) {
      notify('Click a cell first, then Fill right', 'error')
      return
    }
    const row = grid.rows.find((r) => r.item_id === selected.item)
    if (!row) return
    const src = valueFor(selected.item, row.cells[selected.period])
    setEdits((e) => {
      const next = { ...e }
      for (let t = selected.period + 1; t < periodCount; t++) next[keyOf(selected.item, t)] = src
      return next
    })
    notify('Filled right — review then Save changes')
  }

  const applyGrowth = () => {
    if (!grid) return
    const result = computeGrowth({
      scope,
      selectedItemId: selectedRow,
      rows: grid.rows.map((r) => ({ itemId: r.item_id, baseDriver: cellDriver(section, r.cells[0]) })),
      periodCount,
      growthPct,
      base: baseVal,
    })
    if (!result.ok) {
      notify(result.error, 'error')
      return
    }
    setEdits((e) => ({ ...e, ...result.edits }))
    const target = scope === 'selected' ? 'selected row' : 'all rows'
    notify(`Applied ${labels.growthVerb} to ${target} — review then Save changes`)
  }

  const exportCsv = () => {
    if (!grid || grid.rows.length === 0) {
      notify('Nothing to export yet', 'error')
      return
    }
    const csv = buildProjectionCsv({
      periodLabels: grid.periods.map((p) => p.period_label),
      rows: grid.rows.map((r) => ({
        itemId: r.item_id,
        label: r.label,
        description: r.group ?? r.note ?? '',
        cells: r.cells.map((c) => ({ periodIndex: c.period_index, driver: cellDriver(section, c) })),
        total: r.total,
      })),
      edits,
      totalsByPeriod: grid.totals_by_period,
      grandTotal: grid.grand_total,
      totalNoun: labels.totalNoun,
      currency: grid.currency,
    })
    downloadCsv(`${CSV_FILE_PREFIX[section]}-${mode}.csv`, csv)
    notify('CSV exported')
  }

  if (isLoading) return <LoadingScreen label="Loading projection grid…" />
  if (isError || !grid) {
    return (
      <SectionCard title="Could not load the projection grid" icon="⚠">
        <div className="banner banner--warning" style={{ marginBottom: 14 }}>
          <span className="banner__icon">⚠</span>
          <div>{(error as Error)?.message ?? 'The request to the server failed.'}</div>
        </div>
        <button className="btn btn--primary" onClick={() => refetch()}>↻ Retry</button>
      </SectionCard>
    )
  }

  return (
    <div className="stack">
      {/* Toolbar */}
      <SectionCard>
        <div className="row row--wrap" style={{ gap: 20, alignItems: 'flex-end' }}>
          <div className="field" style={{ minWidth: 0 }}>
            <span className="field__label">Projection mode</span>
            <div className="segmented">
              <button className={`segmented__btn${mode === 'monthly' ? ' segmented__btn--active' : ''}`} onClick={() => { setMode('monthly'); resetEdits() }}>Monthly</button>
              <button className={`segmented__btn${mode === 'annual' ? ' segmented__btn--active' : ''}`} onClick={() => { setMode('annual'); resetEdits() }}>Annual</button>
            </div>
          </div>

          <div className="field" style={{ minWidth: 0 }}>
            <span className="field__label">Apply {labels.growthVerb} to</span>
            <div className="row" style={{ gap: 6, alignItems: 'center' }}>
              <div className="segmented">
                <button
                  className={`segmented__btn${scope === 'selected' ? ' segmented__btn--active' : ''}`}
                  onClick={() => setScope('selected')}
                >
                  Selected row
                </button>
                <button
                  className={`segmented__btn${scope === 'all' ? ' segmented__btn--active' : ''}`}
                  onClick={() => setScope('all')}
                >
                  All rows
                </button>
              </div>
              <input className="input" style={{ width: 92 }} placeholder="base" value={baseVal} onChange={(e) => setBaseVal(e.target.value)} />
              <input className="input" style={{ width: 78 }} placeholder="% / period" value={growthPct} onChange={(e) => setGrowthPct(e.target.value)} />
              <button className="btn btn--secondary btn--sm" onClick={applyGrowth}>Apply</button>
            </div>
            {scope === 'selected' && !selectedRow && (
              <span className="field__label" style={{ color: 'var(--amber-500)', marginTop: 4 }}>
                ⚠ No row selected — click a row in the grid first.
              </span>
            )}
          </div>

          <button className="btn btn--secondary btn--sm" onClick={fillRight}>⟶ Fill right</button>
          <div className="spacer" />
          <button className="btn btn--secondary btn--sm" onClick={exportCsv} disabled={grid.rows.length === 0} title="Download the visible grid as CSV">⤓ CSV</button>
          {dirty && <span className="badge badge--amber badge--dot">{Object.keys(edits).length} unsaved</span>}
          <button className="btn btn--primary" onClick={save} disabled={!dirty || saveCells.isPending}>
            {saveCells.isPending ? <><Spinner /> Saving…</> : 'Save changes'}
          </button>
        </div>
      </SectionCard>

      {/* Warnings */}
      {grid.warnings.length > 0 && (
        <SectionCard title="Validation" icon="⚠" subtitle={`${grid.warnings.length} note(s)`}>
          <div className="stack--sm">
            {grid.warnings.map((w, i) => (
              <div className="banner banner--warning" key={i}><span className="banner__icon">⚠</span><div>{w}</div></div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Grid */}
      <div className="card">
        <div className="card__body">
          {grid.rows.length === 0 ? (
            <EmptyState icon="▦" title="Nothing to project yet" description="Add items in the Setup tab first." />
          ) : (
            <>
              <p className="muted" style={{ fontSize: 12.5, marginBottom: 10 }}>
                Editable cells show <strong>{labels.driver}</strong>; the Total column and totals row show{' '}
                <strong>{labels.totalNoun}</strong> in {grid.currency} (updates when you Save).
                {mode === 'annual' && ' Annual edits are spread across the year.'}
              </p>
              <div className="pgrid-wrap">
                <table className="pgrid">
                  <thead>
                    <tr>
                      <th className="pgrid__label-head">Item</th>
                      {grid.periods.map((p) => (
                        <th key={p.period_index} className="pgrid__num">{p.period_label}</th>
                      ))}
                      <th className="pgrid__num pgrid__total">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grid.rows.map((row) => {
                      const rowSelected = selectedRow === row.item_id
                      return (
                      <tr key={row.item_id} className={rowSelected ? 'pgrid__row--selected' : undefined}>
                        <td
                          className="pgrid__label pgrid__label--selectable"
                          onClick={() => selectRow(row.item_id)}
                          role="button"
                          aria-pressed={rowSelected}
                          title="Click to select this row"
                        >
                          <strong>{row.label}</strong>
                          {row.group && <span className="pgrid__group">{row.group}</span>}
                        </td>
                        {row.cells.map((c) => {
                          const k = keyOf(row.item_id, c.period_index)
                          const edited = k in edits
                          const isSel = selected?.item === row.item_id && selected?.period === c.period_index
                          return (
                            <td key={c.period_index} className="pgrid__cell">
                              <input
                                className={`pgrid__input${edited ? ' pgrid__input--edited' : ''}${isSel ? ' pgrid__input--selected' : ''}`}
                                value={valueFor(row.item_id, c)}
                                onFocus={() => { setSelected({ item: row.item_id, period: c.period_index }); setSelectedRow(row.item_id) }}
                                onChange={(e) =>
                                  setEdits((prev) => ({ ...prev, [k]: e.target.value }))
                                }
                                inputMode="decimal"
                              />
                            </td>
                          )
                        })}
                        <td className="pgrid__num pgrid__total">{formatStatementNumber(row.total)}</td>
                      </tr>
                      )
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="pgrid__totals">
                      <td className="pgrid__label">Total {labels.totalNoun}</td>
                      {grid.totals_by_period.map((v, i) => (
                        <td key={i} className="pgrid__num">{formatStatementNumber(v)}</td>
                      ))}
                      <td className="pgrid__num pgrid__total">{formatStatementNumber(grid.grand_total)}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
