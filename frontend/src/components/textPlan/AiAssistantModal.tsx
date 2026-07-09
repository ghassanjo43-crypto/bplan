import { useEffect, useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { useGenerateSection } from '@/api/aiApi'
import type { AiAction, AiLanguage, AiTone } from '@/types/ai'
import {
  ACTIONS,
  DISCLAIMER,
  LANGUAGES,
  TONES,
  aiErrorMessage,
  actionNeedsCurrentText,
  buildGeneratePayload,
  textToHtml,
  validateForm,
  type AiFormState,
} from './aiAssistant'

export interface AiModalPreset {
  action?: AiAction
  tone?: AiTone
  language?: AiLanguage
}

export function AiAssistantModal({
  open,
  onClose,
  projectId,
  sectionKey,
  sectionTitle,
  currentText,
  preset,
  onInsert,
  onReplace,
}: {
  open: boolean
  onClose: () => void
  projectId: string
  sectionKey?: string | null
  sectionTitle?: string | null
  currentText?: string
  preset?: AiModalPreset
  /** Insert the generated text (as HTML) at the cursor. */
  onInsert: (html: string) => void
  /** Replace the whole section body with the generated text (as HTML). */
  onReplace: (html: string) => void
}) {
  const generate = useGenerateSection(projectId)
  const [userPrompt, setUserPrompt] = useState('')
  const [language, setLanguage] = useState<AiLanguage>('english')
  const [tone, setTone] = useState<AiTone>('formal')
  const [action, setAction] = useState<AiAction>('generate')
  const [result, setResult] = useState<string>('')
  const [error, setError] = useState<string>('')

  // Apply preset + reset transient state whenever the modal is (re)opened.
  useEffect(() => {
    if (!open) return
    setAction(preset?.action ?? 'generate')
    if (preset?.tone) setTone(preset.tone)
    if (preset?.language) setLanguage(preset.language)
    setResult('')
    setError('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const formState = (): AiFormState => ({
    sectionKey,
    sectionTitle,
    userPrompt,
    language,
    tone,
    action,
    currentText,
  })

  const run = () => {
    const state = formState()
    const invalid = validateForm(state)
    if (invalid) {
      setError(invalid)
      return
    }
    setError('')
    generate.mutate(buildGeneratePayload(state), {
      onSuccess: (data) => setResult(data.content),
      onError: (e) => setError(aiErrorMessage(e)),
    })
  }

  const insert = () => {
    if (!result.trim()) return
    onInsert(textToHtml(result))
    onClose()
  }

  const replace = () => {
    if (!result.trim()) return
    onReplace(textToHtml(result))
    onClose()
  }

  const busy = generate.isPending
  const needsText = actionNeedsCurrentText(action)

  return (
    <Modal
      title="Generate with AI"
      open={open}
      onClose={onClose}
      wide
      footer={
        <div className="row" style={{ justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <span className="muted" style={{ fontSize: 12 }}>⚠ {DISCLAIMER}</span>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn--secondary" onClick={onClose}>
              Cancel
            </button>
            {result ? (
              <>
                <button className="btn btn--ghost" disabled={busy} onClick={run}>
                  {busy ? 'Regenerating…' : 'Regenerate'}
                </button>
                <button className="btn btn--secondary" onClick={replace}>
                  Replace current text
                </button>
                <button className="btn btn--primary" onClick={insert}>
                  Insert into section
                </button>
              </>
            ) : (
              <button className="btn btn--primary" disabled={busy} onClick={run}>
                {busy ? 'Generating…' : 'Generate'}
              </button>
            )}
          </div>
        </div>
      }
    >
      <div className="stack--sm">
        <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
          <label className="field" style={{ flex: '1 1 160px' }}>
            <span className="field__label">Action</span>
            <select className="input" value={action} onChange={(e) => setAction(e.target.value as AiAction)}>
              {ACTIONS.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: '1 1 160px' }}>
            <span className="field__label">Language</span>
            <select className="input" value={language} onChange={(e) => setLanguage(e.target.value as AiLanguage)}>
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: '1 1 160px' }}>
            <span className="field__label">Tone</span>
            <select className="input" value={tone} onChange={(e) => setTone(e.target.value as AiTone)}>
              {TONES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="field">
          <span className="field__label">What should the AI write?</span>
          <textarea
            className="input"
            rows={3}
            value={userPrompt}
            placeholder={
              needsText
                ? 'Optional: extra guidance for how to transform the section text…'
                : 'e.g. Write an executive summary highlighting our recurring revenue and market opportunity.'
            }
            onChange={(e) => setUserPrompt(e.target.value)}
          />
        </label>

        {needsText && (
          <p className="muted" style={{ fontSize: 12, margin: 0 }}>
            This action uses the section’s current text
            {currentText?.trim() ? '.' : ' — but the section is empty.'}
          </p>
        )}

        {error && <div className="login__error">{error}</div>}

        {result && (
          <div className="field">
            <span className="field__label">Generated draft (editable after insert)</span>
            <div
              className="ai-result"
              style={{
                whiteSpace: 'pre-wrap',
                border: '1px solid var(--border, #e2e8f0)',
                borderRadius: 8,
                padding: '12px 14px',
                maxHeight: 280,
                overflowY: 'auto',
                fontSize: 14,
                lineHeight: 1.6,
              }}
              dir={language === 'arabic' ? 'rtl' : 'ltr'}
            >
              {result}
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
