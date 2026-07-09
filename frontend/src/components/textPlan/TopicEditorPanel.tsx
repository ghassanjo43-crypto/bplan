import { useCallback, useEffect, useRef, useState } from 'react'
import type { Editor, JSONContent } from '@tiptap/react'
import { RichTextEditor } from '@/components/editor/RichTextEditor'
import { useToast } from '@/components/ui/Toast'
import { AutosaveIndicator, type SaveState } from './AutosaveIndicator'
import { AiAssistantModal, type AiModalPreset } from './AiAssistantModal'
import { HelpTooltip } from '@/components/ui/HelpTooltip'
import { QUICK_ACTIONS } from './aiAssistant'
import { uploadTopicImage, useUpdateTopic } from '@/api/textPlanApi'
import type { TextPlanTopic, TopicStatus } from '@/types/textPlan'

const STATUSES: { value: TopicStatus; label: string }[] = [
  { value: 'not_started', label: 'Not started' },
  { value: 'draft', label: 'Draft' },
  { value: 'in_review', label: 'In review' },
  { value: 'completed', label: 'Completed' },
]

export function TopicEditorPanel({ projectId, topic }: { projectId: string; topic: TextPlanTopic }) {
  const update = useUpdateTopic(projectId)
  const { notify } = useToast()
  const [title, setTitle] = useState(topic.title)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [savedAt, setSavedAt] = useState<Date | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pending = useRef<{ title?: string; content_html?: string; content_json?: JSONContent }>({})
  const editorRef = useRef<Editor | null>(null)
  const [aiOpen, setAiOpen] = useState(false)
  const [aiPreset, setAiPreset] = useState<AiModalPreset | undefined>(undefined)

  const onEditorReady = useCallback((ed: Editor) => {
    editorRef.current = ed
  }, [])

  // content_json is the preferred editor source; fall back to HTML then plain text.
  const initialContent: string | JSONContent =
    topic.content_json && Object.keys(topic.content_json).length > 0
      ? (topic.content_json as JSONContent)
      : topic.content_html || ''

  // Reset local state when switching topics.
  useEffect(() => {
    setTitle(topic.title)
    setSaveState('idle')
    pending.current = {}
    if (timer.current) clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic.id])

  // Warn before leaving with unsaved changes.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (saveState === 'unsaved' || saveState === 'saving') {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [saveState])

  const flush = () => {
    const body = { ...pending.current }
    if (Object.keys(body).length === 0) return
    pending.current = {}
    setSaveState('saving')
    update.mutate(
      { id: topic.id, body },
      {
        onSuccess: () => {
          setSaveState('saved')
          setSavedAt(new Date())
        },
        onError: () => setSaveState('error'),
      },
    )
  }

  const queue = (patch: { title?: string; content_html?: string; content_json?: JSONContent }) => {
    pending.current = { ...pending.current, ...patch }
    setSaveState('unsaved')
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(flush, 1000)
  }

  const openAi = (preset?: AiModalPreset) => {
    setAiPreset(preset)
    setAiOpen(true)
  }

  // Insert generated HTML at the cursor; the editor's onUpdate queues the save.
  const insertAi = (html: string) => {
    editorRef.current?.chain().focus().insertContent(html).run()
  }

  // Replace the whole section body; `true` emits an update so autosave runs.
  const replaceAi = (html: string) => {
    editorRef.current?.commands.setContent(html, true)
  }

  const saveField = (body: Record<string, unknown>) => {
    setSaveState('saving')
    update.mutate(
      { id: topic.id, body },
      { onSuccess: () => { setSaveState('saved'); setSavedAt(new Date()) }, onError: () => setSaveState('error') },
    )
  }

  return (
    <div className="tb-editor">
      <div className="tb-editor__bar">
        <input
          className="tb-title-input"
          value={title}
          placeholder="Topic title"
          onChange={(e) => {
            setTitle(e.target.value)
            queue({ title: e.target.value })
          }}
          onBlur={flush}
        />
        <AutosaveIndicator state={saveState} savedAt={savedAt} />
      </div>

      <div className="tb-editor__meta">
        <label className="row" style={{ gap: 6, alignItems: 'center', fontSize: 13 }}>
          Status
          <select className="input input--sm" value={topic.status} onChange={(e) => saveField({ status: e.target.value })}>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="row" style={{ gap: 6, alignItems: 'center', fontSize: 13 }}>
          <input
            type="checkbox"
            checked={topic.include_in_report}
            onChange={(e) => saveField({ include_in_report: e.target.checked })}
          />
          Include in report
        </label>
        <span className="muted" style={{ fontSize: 12 }}>
          {topic.word_count} words · ~{topic.reading_time_minutes} min read
        </span>
      </div>

      {topic.guidance_text && <div className="tb-guidance-inline">💡 {topic.guidance_text}</div>}

      <RichTextEditor
        content={initialContent}
        onReady={onEditorReady}
        onChange={(html, json) => queue({ content_html: html, content_json: json })}
        uploadImage={(file) => uploadTopicImage(projectId, topic.id, file)}
        onUploadError={(err) => notify((err as Error)?.message ?? 'Image upload failed.', 'error')}
      />
      <p className="muted" style={{ fontSize: 12, margin: '2px 2px 0' }}>
        Use the 🖼 toolbar button to insert an image at the cursor. Select an image to align, resize, caption, or delete it.
      </p>

      <div className="tb-ai-row">
        <HelpTooltip helpKey="ai.generateText">
          <button className="btn btn--primary btn--sm" onClick={() => openAi()}>
            ✨ Generate with AI
          </button>
        </HelpTooltip>
        <span className="muted" style={{ fontSize: 12 }}>Quick actions:</span>
        {QUICK_ACTIONS.map((q) => (
          <button
            key={q.key}
            className="btn btn--ghost btn--sm"
            onClick={() => openAi({ action: q.action, tone: q.tone, language: q.language })}
          >
            {q.label}
          </button>
        ))}
      </div>

      <AiAssistantModal
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        projectId={projectId}
        sectionKey={topic.topic_type || undefined}
        sectionTitle={title}
        currentText={editorRef.current?.getText() ?? topic.plain_text}
        preset={aiPreset}
        onInsert={insertAi}
        onReplace={replaceAi}
      />
    </div>
  )
}
