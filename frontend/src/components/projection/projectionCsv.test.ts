import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  csvEscape,
  buildProjectionCsvMatrix,
  buildProjectionCsv,
  type ProjectionCsvInput,
} from './projectionCsv.ts'

function monthlyInput(edits: Record<string, string> = {}): ProjectionCsvInput {
  return {
    periodLabels: ['Jan 2026', 'Feb 2026'],
    rows: [
      {
        itemId: 'a',
        label: 'Filters',
        description: 'units',
        cells: [
          { periodIndex: 0, driver: 100 },
          { periodIndex: 1, driver: 110 },
        ],
        total: 21000,
      },
    ],
    edits,
    totalsByPeriod: [10000, 11000],
    grandTotal: 21000,
    totalNoun: 'net revenue',
    currency: 'USD',
  }
}

function annualInput(): ProjectionCsvInput {
  return {
    periodLabels: ['Year 1', 'Year 2'],
    rows: [
      {
        itemId: 'a',
        label: 'Filters',
        description: 'units',
        cells: [
          { periodIndex: 0, driver: 1200 },
          { periodIndex: 1, driver: 1320 },
        ],
        total: 252000,
      },
    ],
    edits: {},
    totalsByPeriod: [120000, 132000],
    grandTotal: 252000,
    totalNoun: 'net revenue',
    currency: 'USD',
  }
}

test('monthly CSV export data: header, row and totals', () => {
  const m = buildProjectionCsvMatrix(monthlyInput())
  assert.deepEqual(m[0], ['Item', 'Description', 'Jan 2026', 'Feb 2026', 'Total net revenue (USD)'])
  assert.deepEqual(m[1], ['Filters', 'units', '100', '110', '21000'])
})

test('annual CSV export data uses the annual period labels', () => {
  const m = buildProjectionCsvMatrix(annualInput())
  assert.deepEqual(m[0], ['Item', 'Description', 'Year 1', 'Year 2', 'Total net revenue (USD)'])
  assert.deepEqual(m[1], ['Filters', 'units', '1200', '1320', '252000'])
})

test('edited/staged values override saved driver values', () => {
  // Stage Feb 2026 for row "a" to 999 without touching the backend driver.
  const m = buildProjectionCsvMatrix(monthlyInput({ 'a:1': '999' }))
  assert.deepEqual(m[1], ['Filters', 'units', '100', '999', '21000'])
})

test('totals row is included as the last row', () => {
  const m = buildProjectionCsvMatrix(monthlyInput())
  assert.deepEqual(m[m.length - 1], ['Total net revenue', '', '10000', '11000', '21000'])
})

test('csvEscape wraps commas, quotes and newlines', () => {
  assert.equal(csvEscape('plain'), 'plain')
  assert.equal(csvEscape('a,b'), '"a,b"')
  assert.equal(csvEscape('say "hi"'), '"say ""hi"""')
  assert.equal(csvEscape('line1\nline2'), '"line1\nline2"')
})

test('buildProjectionCsv escapes a label containing a comma', () => {
  const input = monthlyInput()
  input.rows[0].label = 'Filters, Deluxe'
  const csv = buildProjectionCsv(input)
  const firstBodyLine = csv.split('\r\n')[1]
  assert.ok(firstBodyLine.startsWith('"Filters, Deluxe",units,'))
})
