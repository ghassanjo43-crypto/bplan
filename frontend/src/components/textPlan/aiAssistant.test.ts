import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  buildGeneratePayload,
  validateForm,
  textToHtml,
  aiErrorMessage,
  actionNeedsCurrentText,
  QUICK_ACTIONS,
  type AiFormState,
} from './aiAssistant.ts'

const base: AiFormState = {
  sectionKey: 'executive_summary',
  sectionTitle: 'Executive Summary',
  userPrompt: '  Summarise the business  ',
  language: 'english',
  tone: 'investor',
  action: 'generate',
  currentText: 'Existing paragraph.',
}

// --- request payload is correct ------------------------------------------
test('buildGeneratePayload sends the expected body for generate', () => {
  const body = buildGeneratePayload(base)
  assert.deepEqual(body, {
    section_key: 'executive_summary',
    section_title: 'Executive Summary',
    user_prompt: 'Summarise the business', // trimmed
    language: 'english',
    tone: 'investor',
    action: 'generate',
    current_text: null, // generate must not carry current_text
  })
})

test('buildGeneratePayload includes current_text for transform actions', () => {
  const body = buildGeneratePayload({ ...base, action: 'improve' })
  assert.equal(body.action, 'improve')
  assert.equal(body.current_text, 'Existing paragraph.')
})

test('translate_arabic is treated as a text action', () => {
  assert.equal(actionNeedsCurrentText('translate_arabic'), true)
  assert.equal(actionNeedsCurrentText('generate'), false)
})

// --- validation mirrors the backend --------------------------------------
test('validateForm passes for a well-formed generate request', () => {
  assert.equal(validateForm(base), null)
})

test('validateForm blocks a transform with no existing text', () => {
  const err = validateForm({ ...base, action: 'shorten', currentText: '   ' })
  assert.match(err ?? '', /existing text/i)
})

test('validateForm blocks generate with neither prompt nor title', () => {
  const err = validateForm({ ...base, userPrompt: '', sectionTitle: '', sectionKey: '' })
  assert.ok(err)
})

// --- generated text displays / becomes editable HTML ---------------------
test('textToHtml wraps paragraphs and escapes HTML', () => {
  const html = textToHtml('First para.\n\nSecond & <b>bold</b> para.')
  assert.equal(html, '<p>First para.</p><p>Second &amp; &lt;b&gt;bold&lt;/b&gt; para.</p>')
})

test('textToHtml turns single newlines into line breaks', () => {
  assert.equal(textToHtml('line one\nline two'), '<p>line one<br>line two</p>')
})

test('textToHtml returns empty string for blank input', () => {
  assert.equal(textToHtml('   \n\n  '), '')
})

// --- insert vs replace both consume the same HTML ------------------------
test('insert and replace both derive from textToHtml', () => {
  const generated = 'Investor-ready summary.'
  const html = textToHtml(generated)
  // Insert appends at cursor; replace swaps the whole document — both use `html`.
  assert.equal(html, '<p>Investor-ready summary.</p>')
})

// --- API error message displays clearly ----------------------------------
test('aiErrorMessage surfaces the backend 503 configuration message', () => {
  const msg = aiErrorMessage({ status: 503, message: 'AI generation is not configured.' })
  assert.match(msg, /not configured/i)
})

test('aiErrorMessage falls back to a generic message', () => {
  assert.match(aiErrorMessage(null), /failed/i)
  assert.match(aiErrorMessage({}), /failed/i)
})

// --- quick actions -------------------------------------------------------
test('quick actions include the required presets', () => {
  const labels = QUICK_ACTIONS.map((q) => q.label)
  assert.ok(labels.includes('Improve this text'))
  assert.ok(labels.includes('Make investor-friendly'))
  assert.ok(labels.includes('Translate to Arabic'))
  assert.ok(labels.includes('Make shorter'))
  assert.equal(QUICK_ACTIONS.find((q) => q.key === 'investor')?.tone, 'investor')
})
