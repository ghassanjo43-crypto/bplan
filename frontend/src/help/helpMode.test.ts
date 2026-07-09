import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  HELP_MODE_KEY,
  readHelpMode,
  writeHelpMode,
  resolveHelpText,
  type KVStorage,
} from './helpMode.ts'
import { helpContent } from './helpContent.ts'

function mockStorage(): KVStorage & { map: Map<string, string> } {
  const map = new Map<string, string>()
  return {
    map,
    getItem: (k) => (map.has(k) ? map.get(k)! : null),
    setItem: (k, v) => {
      map.set(k, v)
    },
  }
}

// --- Help Mode default OFF ------------------------------------------------
test('help mode defaults to OFF when nothing is stored', () => {
  const store = mockStorage()
  assert.equal(readHelpMode(store), false)
})

test('help mode reads as OFF for any non-"on" stored value', () => {
  const store = mockStorage()
  store.setItem(HELP_MODE_KEY, 'off')
  assert.equal(readHelpMode(store), false)
})

// --- toggle stores value in localStorage ---------------------------------
test('writeHelpMode(true) persists "on" and reads back as ON', () => {
  const store = mockStorage()
  writeHelpMode(true, store)
  assert.equal(store.getItem(HELP_MODE_KEY), 'on')
  assert.equal(readHelpMode(store), true)
})

test('writeHelpMode(false) persists "off" and reads back as OFF', () => {
  const store = mockStorage()
  writeHelpMode(true, store)
  writeHelpMode(false, store)
  assert.equal(store.getItem(HELP_MODE_KEY), 'off')
  assert.equal(readHelpMode(store), false)
})

test('read/write are resilient when no storage is available', () => {
  assert.equal(readHelpMode(null), false)
  assert.doesNotThrow(() => writeHelpMode(true, null))
})

// --- tooltip does NOT show when OFF --------------------------------------
test('resolveHelpText returns null when help mode is OFF', () => {
  assert.equal(resolveHelpText('income.statement', false), null)
})

// --- tooltip shows when ON -----------------------------------------------
test('resolveHelpText returns the help text when help mode is ON', () => {
  const text = resolveHelpText('income.statement', true)
  assert.equal(typeof text, 'string')
  assert.match(text ?? '', /income statement/i)
})

// --- missing helpKey fails gracefully ------------------------------------
test('resolveHelpText returns null for an unknown key (no throw)', () => {
  assert.equal(resolveHelpText('does.not.exist', true), null)
})

test('resolveHelpText tolerates empty/garbage keys', () => {
  assert.equal(resolveHelpText('', true), null)
  assert.equal(resolveHelpText('__proto__', true), null)
})

// --- registry completeness ----------------------------------------------
test('registry contains every documented help key', () => {
  const required = [
    'dashboard.overview',
    'project.setup',
    'revenue.streams',
    'revenue.projection',
    'revenue.growth',
    'direct.costs',
    'operating.expenses',
    'income.statement',
    'scenarios',
    'reports',
    'narrative.editor',
    'ai.generateText',
  ]
  for (const key of required) {
    assert.ok(key in helpContent, `missing help key: ${key}`)
    assert.ok((helpContent as Record<string, { text: string }>)[key].text.length > 0)
  }
})
