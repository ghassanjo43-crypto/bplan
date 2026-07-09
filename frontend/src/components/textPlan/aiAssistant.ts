/* Pure, framework-free logic backing the AI assistant modal.
 *
 * Kept separate from the React component so it is unit-testable under
 * `node --test` (no DOM). The modal is a thin shell over these helpers. */
import type { AiAction, AiGenerateRequest, AiLanguage, AiTone } from '@/types/ai'

export const DISCLAIMER = 'AI-generated content should be reviewed before final use.'

export const LANGUAGES: { value: AiLanguage; label: string }[] = [
  { value: 'english', label: 'English' },
  { value: 'arabic', label: 'Arabic' },
]

export const TONES: { value: AiTone; label: string }[] = [
  { value: 'investor', label: 'Investor' },
  { value: 'bank', label: 'Bank' },
  { value: 'formal', label: 'Formal' },
  { value: 'government', label: 'Government' },
  { value: 'simple', label: 'Simple' },
  { value: 'big_four', label: 'Big Four style' },
]

export const ACTIONS: { value: AiAction; label: string }[] = [
  { value: 'generate', label: 'Generate' },
  { value: 'improve', label: 'Improve' },
  { value: 'shorten', label: 'Shorten' },
  { value: 'expand', label: 'Expand' },
  { value: 'translate_arabic', label: 'Translate to Arabic' },
  { value: 'translate_english', label: 'Translate to English' },
]

/** Actions that transform the section's existing text (so it must be sent). */
export const TEXT_ACTIONS: AiAction[] = [
  'improve',
  'shorten',
  'expand',
  'translate_arabic',
  'translate_english',
]

export function actionNeedsCurrentText(action: AiAction): boolean {
  return TEXT_ACTIONS.includes(action)
}

/** One-click presets shown as quick-action buttons in the editor. */
export interface QuickAction {
  key: string
  label: string
  action: AiAction
  tone?: AiTone
  language?: AiLanguage
}

export const QUICK_ACTIONS: QuickAction[] = [
  { key: 'improve', label: 'Improve this text', action: 'improve' },
  { key: 'investor', label: 'Make investor-friendly', action: 'improve', tone: 'investor' },
  { key: 'arabic', label: 'Translate to Arabic', action: 'translate_arabic', language: 'arabic' },
  { key: 'shorten', label: 'Make shorter', action: 'shorten' },
]

export interface AiFormState {
  sectionKey?: string | null
  sectionTitle?: string | null
  userPrompt: string
  language: AiLanguage
  tone: AiTone
  action: AiAction
  currentText?: string | null
}

/** Build the exact request body sent to the backend, normalising fields. */
export function buildGeneratePayload(state: AiFormState): AiGenerateRequest {
  const needsText = actionNeedsCurrentText(state.action)
  return {
    section_key: state.sectionKey || null,
    section_title: state.sectionTitle || null,
    user_prompt: state.userPrompt.trim(),
    language: state.language,
    tone: state.tone,
    action: state.action,
    // Only send current_text when the action operates on it — keeps generate clean.
    current_text: needsText ? state.currentText ?? '' : null,
  }
}

/** Client-side guard mirroring the backend validator; returns an error or null. */
export function validateForm(state: AiFormState): string | null {
  if (!state.sectionKey && !state.sectionTitle) {
    return 'This section has no title yet — add one before generating.'
  }
  if (actionNeedsCurrentText(state.action) && !(state.currentText ?? '').trim()) {
    const label = ACTIONS.find((a) => a.value === state.action)?.label ?? state.action
    return `“${label}” needs existing text in the section first.`
  }
  if (
    state.action === 'generate' &&
    !state.userPrompt.trim() &&
    !(state.sectionTitle ?? '').trim()
  ) {
    return 'Describe what you want, or give the section a title.'
  }
  return null
}

const escapeHtml = (s: string): string =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

/**
 * Convert plain generated text into safe HTML paragraphs for the rich-text
 * editor. Blank lines separate paragraphs; single newlines become <br>.
 */
export function textToHtml(text: string): string {
  const blocks = text
    .replace(/\r\n/g, '\n')
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)
  if (blocks.length === 0) return ''
  return blocks
    .map((b) => `<p>${escapeHtml(b).replace(/\n/g, '<br>')}</p>`)
    .join('')
}

interface ApiErrorLike {
  status?: number
  message?: string
}

/** Turn any thrown value into a clear, user-facing message. */
export function aiErrorMessage(err: unknown): string {
  const e = err as ApiErrorLike | null
  if (e && typeof e.message === 'string' && e.message.trim()) {
    if (e.status === 503) {
      return e.message // backend already explains AI is not configured
    }
    return e.message
  }
  return 'AI generation failed. Please try again.'
}
