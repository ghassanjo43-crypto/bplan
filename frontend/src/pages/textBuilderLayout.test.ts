import { test } from 'node:test'
import assert from 'node:assert/strict'
import { tbGridClass } from './textBuilderLayout.ts'

test('no panels collapsed → base grid class only', () => {
  assert.equal(tbGridClass(false, false), 'tb')
})

test('left collapsed → adds left modifier (editor expands left)', () => {
  assert.equal(tbGridClass(true, false), 'tb tb--left-collapsed')
})

test('right collapsed → adds right modifier (editor expands right)', () => {
  assert.equal(tbGridClass(false, true), 'tb tb--right-collapsed')
})

test('both collapsed → both modifiers (editor uses almost full width)', () => {
  assert.equal(tbGridClass(true, true), 'tb tb--left-collapsed tb--right-collapsed')
})
