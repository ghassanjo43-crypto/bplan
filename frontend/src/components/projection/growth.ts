/**
 * Pure, dependency-free growth math for the projection grid.
 *
 * This module is intentionally import-free so it can be unit-tested directly
 * with `node --test` (via native TypeScript type-stripping) without a bundler
 * or DOM. Keep it free of framework/type-alias imports.
 */

export type GrowthScope = 'selected' | 'all'

export interface GrowthRow {
  itemId: string
  /** Base driver value (period-0 units / amount / cost) for this row. */
  baseDriver: number
}

export interface GrowthInput {
  scope: GrowthScope
  /** The currently selected row, or null when nothing is selected. */
  selectedItemId: string | null
  rows: GrowthRow[]
  /** Number of periods in the current mode (12*years monthly, or years annual). */
  periodCount: number
  /** Raw growth % per period, as typed into the input box. */
  growthPct: string
  /** Optional raw base override; blank => each row uses its own baseDriver. */
  base: string
}

export type GrowthResult =
  | { ok: true; edits: Record<string, string> }
  | { ok: false; error: string }

export function growthKey(item: string, period: number): string {
  return `${item}:${period}`
}

/** Plain editable string (no thousands separators while editing). */
export function numStr(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Number(n.toFixed(2)))
}

/**
 * Compute the staged cell edits for compound period-over-period growth:
 *
 *   next_period_value = previous_period_value * (1 + growth_percent / 100)
 *
 * The same per-period formula is applied in both monthly and annual mode —
 * annual mode simply has fewer, year-length periods — so growth compounds
 * consistently across years.
 *
 * Returns `{ ok: false, error }` (rather than throwing) so the caller can show
 * a clear warning, e.g. when "selected row only" is chosen but no row is
 * selected.
 */
export function computeGrowth(input: GrowthInput): GrowthResult {
  const { scope, selectedItemId, rows, periodCount } = input

  if (scope === 'selected' && !selectedItemId) {
    return { ok: false, error: 'Select a revenue row first (click a row), then Apply growth.' }
  }

  const g = Number(input.growthPct)
  if (input.growthPct.trim() === '' || Number.isNaN(g)) {
    return { ok: false, error: 'Enter a growth/inflation % first.' }
  }

  const targetRows =
    scope === 'selected' ? rows.filter((r) => r.itemId === selectedItemId) : rows

  if (targetRows.length === 0) {
    return { ok: false, error: 'No matching row to apply growth to.' }
  }

  const rate = g / 100
  const parsedBase = input.base.trim() !== '' ? Number(input.base) : NaN
  const hasOverride = !Number.isNaN(parsedBase)

  const edits: Record<string, string> = {}
  for (const row of targetRows) {
    let val = hasOverride ? parsedBase : row.baseDriver
    for (let t = 0; t < periodCount; t++) {
      edits[growthKey(row.itemId, t)] = numStr(val)
      val = val * (1 + rate)
    }
  }
  return { ok: true, edits }
}
