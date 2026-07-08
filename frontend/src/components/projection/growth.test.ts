import { test } from 'node:test'
import assert from 'node:assert/strict'
import { computeGrowth, growthKey, type GrowthRow } from './growth.ts'

const rows: GrowthRow[] = [
  { itemId: 'a', baseDriver: 100 },
  { itemId: 'b', baseDriver: 50 },
]

test('applies growth to the selected row only', () => {
  const res = computeGrowth({
    scope: 'selected',
    selectedItemId: 'a',
    rows,
    periodCount: 3,
    growthPct: '10',
    base: '',
  })
  assert.equal(res.ok, true)
  if (!res.ok) return
  // Row "a" is written; row "b" is untouched.
  assert.equal(res.edits[growthKey('a', 0)], '100')
  assert.equal(res.edits[growthKey('a', 1)], '110')
  assert.equal(res.edits[growthKey('a', 2)], '121')
  assert.equal(res.edits[growthKey('b', 0)], undefined)
})

test('applies growth to all rows', () => {
  const res = computeGrowth({
    scope: 'all',
    selectedItemId: null,
    rows,
    periodCount: 2,
    growthPct: '10',
    base: '',
  })
  assert.equal(res.ok, true)
  if (!res.ok) return
  assert.equal(res.edits[growthKey('a', 0)], '100')
  assert.equal(res.edits[growthKey('a', 1)], '110')
  assert.equal(res.edits[growthKey('b', 0)], '50')
  assert.equal(res.edits[growthKey('b', 1)], '55')
})

test('warns when selected-row scope is chosen but no row is selected', () => {
  const res = computeGrowth({
    scope: 'selected',
    selectedItemId: null,
    rows,
    periodCount: 3,
    growthPct: '10',
    base: '',
  })
  assert.equal(res.ok, false)
  if (res.ok) return
  assert.match(res.error, /select a revenue row/i)
})

test('4% monthly growth compounds period over period', () => {
  const res = computeGrowth({
    scope: 'all',
    selectedItemId: null,
    rows: [{ itemId: 'x', baseDriver: 100 }],
    periodCount: 4,
    growthPct: '4',
    base: '',
  })
  assert.equal(res.ok, true)
  if (!res.ok) return
  // next = prev * (1 + 4/100)
  assert.equal(res.edits[growthKey('x', 0)], '100')
  assert.equal(res.edits[growthKey('x', 1)], '104')
  assert.equal(res.edits[growthKey('x', 2)], '108.16')
  assert.equal(res.edits[growthKey('x', 3)], '112.49')
})

test('base override starts the compounding series at the given value', () => {
  const res = computeGrowth({
    scope: 'selected',
    selectedItemId: 'b',
    rows,
    periodCount: 2,
    growthPct: '4',
    base: '200',
  })
  assert.equal(res.ok, true)
  if (!res.ok) return
  assert.equal(res.edits[growthKey('b', 0)], '200')
  assert.equal(res.edits[growthKey('b', 1)], '208')
})

test('empty growth percent is rejected', () => {
  const res = computeGrowth({
    scope: 'all',
    selectedItemId: null,
    rows,
    periodCount: 2,
    growthPct: '   ',
    base: '',
  })
  assert.equal(res.ok, false)
  if (res.ok) return
  assert.match(res.error, /growth/i)
})
