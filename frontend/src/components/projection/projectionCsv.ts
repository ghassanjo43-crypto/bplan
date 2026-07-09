/**
 * CSV export for the projection grid.
 *
 * The matrix/escaping helpers are pure and import only the dependency-free
 * `growth` module, so they can be unit-tested with `node --test` (via native
 * TypeScript type-stripping) without a bundler or DOM. `downloadCsv` is the
 * only browser-only part and is kept separate.
 */
import { growthKey, numStr } from './growth.ts'

/**
 * RFC-4180 field escaping: wrap the value in double quotes and double any
 * internal quote when it contains a comma, quote, CR or LF.
 */
export function csvEscape(value: string): string {
  if (/[",\r\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

/** Join a matrix of already-stringified cells into RFC-4180 CSV text (CRLF rows). */
export function matrixToCsv(rows: string[][]): string {
  return rows.map((r) => r.map(csvEscape).join(',')).join('\r\n')
}

export interface CsvCell {
  periodIndex: number
  /** The per-period driver value (units / amount / cost) as last saved. */
  driver: number
}

export interface CsvRow {
  itemId: string
  label: string
  /** Unit label / description shown next to the row, if any. */
  description?: string | null
  cells: CsvCell[]
  total: number
}

export interface ProjectionCsvInput {
  periodLabels: string[]
  rows: CsvRow[]
  /** Staged edits keyed like the grid: `${itemId}:${periodIndex}` -> raw string. */
  edits: Record<string, string>
  totalsByPeriod: number[]
  grandTotal: number
  /** Noun for the totals row + Total column, e.g. "net revenue". */
  totalNoun: string
  currency: string
}

/** Plain machine-readable number (no thousands separators); '' for missing. */
function money(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return ''
  return numStr(Number(n.toFixed(2)))
}

/**
 * Build the 2-D CSV matrix for the currently-visible projection grid.
 *
 * Per-period cells reflect staged edits (falling back to the saved driver
 * value), so the export matches exactly what the user sees on screen — even
 * before Save. The Total column and totals row carry the net figures the grid
 * displays.
 */
export function buildProjectionCsvMatrix(input: ProjectionCsvInput): string[][] {
  const totalHeader = `Total ${input.totalNoun} (${input.currency})`
  const header = ['Item', 'Description', ...input.periodLabels, totalHeader]

  const body = input.rows.map((row) => {
    const cells = row.cells.map((c) => {
      const k = growthKey(row.itemId, c.periodIndex)
      return k in input.edits ? input.edits[k] : numStr(c.driver)
    })
    return [row.label, row.description ?? '', ...cells, money(row.total)]
  })

  const totals = [
    `Total ${input.totalNoun}`,
    '',
    ...input.totalsByPeriod.map(money),
    money(input.grandTotal),
  ]

  return [header, ...body, totals]
}

export function buildProjectionCsv(input: ProjectionCsvInput): string {
  return matrixToCsv(buildProjectionCsvMatrix(input))
}

/** Trigger a browser download of the given CSV text. */
export function downloadCsv(filename: string, csv: string): void {
  // Prepend a UTF-8 BOM () so Excel opens accented characters correctly.
  const bom = String.fromCharCode(0xfeff)
  const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
