import { useEffect, useMemo, useState } from 'react'
import { useProjectContext } from '@/layouts/ProjectContext'
import { useToast } from '@/components/ui/Toast'
import { LoadingScreen } from '@/components/ui/Spinner'
import { SectionOutlineTree } from '@/components/textPlan/SectionOutlineTree'
import { TopicEditorPanel } from '@/components/textPlan/TopicEditorPanel'
import { TextPlanRightPanel } from '@/components/textPlan/TextPlanRightPanel'
import { OutlineSuggestionModal } from '@/components/textPlan/OutlineSuggestionModal'
import { TextPlanCompletionBadge } from '@/components/textPlan/TextPlanCompletionBadge'
import {
  useCreateSection,
  useCreateTopic,
  useDeleteSection,
  useDeleteTopic,
  useDuplicateSection,
  useDuplicateTopic,
  useMoveTopic,
  useReorderSections,
  useReorderTopics,
  useTextPlan,
  useTextPlanCompletion,
  useUpdateSection,
} from '@/api/textPlanApi'
import '@/styles/textBuilder.css'

export function TextBuilderPage() {
  const { projectId } = useProjectContext()
  const { notify } = useToast()
  const docQ = useTextPlan(projectId)
  const completionQ = useTextPlanCompletion(projectId)

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null)
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)
  const [outlineOpen, setOutlineOpen] = useState(false)
  // Collapse side columns to widen the editor (persisted across visits).
  const [leftCollapsed, setLeftCollapsed] = useState(() => localStorage.getItem('tb.leftCollapsed') === '1')
  const [rightCollapsed, setRightCollapsed] = useState(() => localStorage.getItem('tb.rightCollapsed') === '1')
  const collapseLeft = (v: boolean) => { setLeftCollapsed(v); localStorage.setItem('tb.leftCollapsed', v ? '1' : '0') }
  const collapseRight = (v: boolean) => { setRightCollapsed(v); localStorage.setItem('tb.rightCollapsed', v ? '1' : '0') }

  const createSection = useCreateSection(projectId)
  const updateSection = useUpdateSection(projectId)
  const deleteSection = useDeleteSection(projectId)
  const duplicateSection = useDuplicateSection(projectId)
  const createTopic = useCreateTopic(projectId)
  const deleteTopic = useDeleteTopic(projectId)
  const duplicateTopic = useDuplicateTopic(projectId)
  const reorderSections = useReorderSections(projectId)
  const reorderTopics = useReorderTopics(projectId)
  const moveTopic = useMoveTopic(projectId)

  const doc = docQ.data
  const sections = doc?.sections ?? []

  // Default selection.
  useEffect(() => {
    if (!doc || sections.length === 0) return
    if (!selectedSectionId || !sections.some((s) => s.id === selectedSectionId)) {
      const first = sections[0]
      setSelectedSectionId(first.id)
      setSelectedTopicId(first.topics[0]?.id ?? null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc])

  const section = useMemo(() => sections.find((s) => s.id === selectedSectionId) ?? null, [sections, selectedSectionId])
  const topic = useMemo(
    () => sections.flatMap((s) => s.topics).find((t) => t.id === selectedTopicId) ?? null,
    [sections, selectedTopicId],
  )

  if (docQ.isLoading || !doc) return <LoadingScreen label="Loading your written plan…" />

  const addSection = () =>
    createSection.mutate(
      { title: 'New Section', section_type: 'custom' },
      { onSuccess: (s) => { setSelectedSectionId(s.id); setSelectedTopicId(null); notify('Section added.', 'success') } },
    )

  const addTopic = () => {
    if (!section) return
    createTopic.mutate(
      { section_id: section.id, title: 'New Topic' },
      { onSuccess: (t) => { setSelectedTopicId(t.id); notify('Topic added.', 'success') } },
    )
  }

  // -------- empty state --------
  if (sections.length === 0) {
    return (
      <div className="tb-empty">
        <div className="tb-empty__card">
          <div className="tb-empty__icon">✎</div>
          <h1>Build your written business plan</h1>
          <p>
            Create the narrative that accompanies your financial study — executive summary, market, strategy, risks
            and more. Start from a smart suggested outline or a blank canvas.
          </p>
          <div className="row" style={{ gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn--primary btn--lg" onClick={() => setOutlineOpen(true)}>
              ✨ Generate suggested outline
            </button>
            <button className="btn btn--secondary btn--lg" onClick={() => setOutlineOpen(true)}>
              Choose a template
            </button>
            <button className="btn btn--ghost btn--lg" onClick={addSection}>
              Start from blank
            </button>
          </div>
        </div>
        <OutlineSuggestionModal projectId={projectId} open={outlineOpen} onClose={() => setOutlineOpen(false)} hasExisting={false} />
      </div>
    )
  }

  return (
    <div className={`tb${leftCollapsed ? ' tb--left-collapsed' : ''}${rightCollapsed ? ' tb--right-collapsed' : ''}`}>
      {/* Left: outline navigator (collapsible) */}
      {leftCollapsed ? (
        <aside className="tb-col tb-col--left">
          <button className="tb-rail" title="Expand outline" onClick={() => collapseLeft(false)}>
            <span className="tb-rail__icon">›</span>
            <span className="tb-rail__label">Outline</span>
          </button>
        </aside>
      ) : (
      <aside className="tb-col tb-col--left">
        <div className="tb-col__head">
          <span className="tb-col__head-left">
            <button className="tb-collapse-btn" title="Collapse outline" onClick={() => collapseLeft(true)}>
              ‹
            </button>
            Outline
          </span>
          <button className="btn btn--secondary btn--sm" onClick={addSection}>
            ＋ Section
          </button>
        </div>
        <div className="tb-col__scroll">
          <SectionOutlineTree
            doc={doc}
            selectedSectionId={selectedSectionId}
            selectedTopicId={selectedTopicId}
            onSelectSection={(sid) => { setSelectedSectionId(sid); setSelectedTopicId(null) }}
            onSelectTopic={(sid, tid) => { setSelectedSectionId(sid); setSelectedTopicId(tid) }}
            handlers={{
              onReorderSections: (ids) => reorderSections.mutate(ids, { onSuccess: () => notify('Sections reordered.', 'success') }),
              onReorderTopics: (sid, ids) => reorderTopics.mutate({ section_id: sid, ordered_topic_ids: ids }),
              onMoveTopic: (tid, target, index) =>
                moveTopic.mutate({ topic_id: tid, target_section_id: target, target_order_index: index },
                  { onSuccess: () => notify('Topic moved.', 'success') }),
            }}
          />
        </div>
        <div className="tb-col__foot">
          <TextPlanCompletionBadge completion={completionQ.data} />
          <button className="btn btn--ghost btn--sm" style={{ width: '100%', marginTop: 8 }} onClick={() => setOutlineOpen(true)}>
            ✨ Outline suggestions
          </button>
        </div>
      </aside>
      )}

      {/* Center: editor */}
      <main className="tb-col tb-col--center">
        {section && (
          <div className="tb-section-bar">
            <input
              className="tb-section-bar__title"
              value={section.title}
              onChange={(e) => updateSection.mutate({ id: section.id, body: { title: e.target.value } })}
            />
            <div className="row" style={{ gap: 6 }}>
              <button className="btn btn--secondary btn--sm" onClick={addTopic}>＋ Topic</button>
              <button className="btn btn--ghost btn--sm" title="Duplicate section"
                onClick={() => duplicateSection.mutate(section.id, { onSuccess: () => notify('Section duplicated.', 'success') })}>
                ⧉
              </button>
              <button className="btn btn--ghost btn--sm" title="Delete section"
                onClick={() => {
                  if (!window.confirm(`Delete section "${section.title}" and its topics?`)) return
                  deleteSection.mutate(section.id, { onSuccess: () => { setSelectedSectionId(null); setSelectedTopicId(null); notify('Section deleted.', 'success') } })
                }}>
                🗑
              </button>
            </div>
          </div>
        )}

        <div className="tb-col__scroll tb-col__scroll--pad">
          {topic ? (
            <>
              <div className="tb-topic-actions">
                <button className="btn btn--ghost btn--sm" onClick={() => duplicateTopic.mutate(topic.id, { onSuccess: (t) => { setSelectedTopicId(t.id); notify('Topic duplicated.', 'success') } })}>
                  ⧉ Duplicate
                </button>
                <button className="btn btn--ghost btn--sm" onClick={() => {
                  if (!window.confirm(`Delete topic "${topic.title}"?`)) return
                  deleteTopic.mutate(topic.id, { onSuccess: () => { setSelectedTopicId(null); notify('Topic deleted.', 'success') } })
                }}>
                  🗑 Delete
                </button>
              </div>
              <TopicEditorPanel key={topic.id} projectId={projectId} topic={topic} />
            </>
          ) : section ? (
            <div className="tb-pick">
              <h2>{section.title}</h2>
              <p className="tb-muted-text">{section.description || 'Select a topic from the outline, or add a new one.'}</p>
              {section.topics.length === 0 ? (
                <button className="btn btn--primary" onClick={addTopic}>＋ Add the first topic</button>
              ) : (
                <div className="tb-pick-list">
                  {section.topics.map((t) => (
                    <button key={t.id} className="tb-pick-item" onClick={() => setSelectedTopicId(t.id)}>
                      <span className="tb-status-dot" /> {t.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="tb-muted-text">Select a section to begin.</p>
          )}
        </div>
      </main>

      {/* Right: guidance / settings / preview (collapsible) */}
      {rightCollapsed ? (
        <aside className="tb-col tb-col--right">
          <button className="tb-rail" title="Expand details" onClick={() => collapseRight(false)}>
            <span className="tb-rail__icon">‹</span>
            <span className="tb-rail__label">Details</span>
          </button>
        </aside>
      ) : (
        <aside className="tb-col tb-col--right">
          <div className="tb-col__head">
            <span className="tb-col__head-left">Details</span>
            <button className="tb-collapse-btn" title="Collapse details" onClick={() => collapseRight(true)}>
              ›
            </button>
          </div>
          <TextPlanRightPanel projectId={projectId} section={section} topic={topic} />
        </aside>
      )}

      <OutlineSuggestionModal projectId={projectId} open={outlineOpen} onClose={() => setOutlineOpen(false)} hasExisting={sections.length > 0} />
    </div>
  )
}
