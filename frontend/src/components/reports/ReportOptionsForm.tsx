import { ScenarioSelector } from '@/components/financials/ScenarioSelector'
import { PeriodViewToggle } from '@/components/financials/PeriodViewToggle'
import type { ReportRequest, ReportStyle } from '@/types/reports'
import type { ScenarioKey } from '@/types/incomeStatement'

const STYLES: { value: ReportStyle; label: string; hint: string }[] = [
  { value: 'investor', label: 'Investor', hint: 'For prospective investors' },
  { value: 'bank', label: 'Bank / Lender', hint: 'For financing banks' },
  { value: 'board', label: 'Board', hint: 'For the board of directors' },
  { value: 'management', label: 'Management', hint: 'Internal management copy' },
  { value: 'full', label: 'Full / Combined', hint: 'Investors, lenders & management' },
]

const TOGGLES: { key: keyof ReportRequest; label: string; hint: string }[] = [
  { key: 'include_assumptions', label: 'Assumptions', hint: 'Revenue, costs, staffing, capex, financing' },
  { key: 'include_charts', label: 'Charts & analysis', hint: 'KPIs and chart data tables' },
  { key: 'include_warnings', label: 'Warnings & reconciliations', hint: 'Balance and cash-flow checks' },
  { key: 'include_appendices', label: 'Appendices', hint: 'Detailed schedules and registers' },
]

const TEXT_PLAN_TOGGLES: { key: keyof ReportRequest; label: string; hint: string }[] = [
  { key: 'include_text_plan', label: 'Written business plan', hint: 'Include the narrative sections and topics' },
  { key: 'text_plan_include_completed', label: 'Completed topics', hint: 'Include topics marked completed' },
  { key: 'text_plan_include_drafts', label: 'Draft topics', hint: 'Include draft / in-progress topics' },
  { key: 'text_plan_include_images', label: 'Topic images', hint: 'Include images inserted in topics' },
  { key: 'text_plan_include_guidance', label: 'Section guidance', hint: 'Include writing guidance (off by default)' },
]

export function ReportOptionsForm({
  value,
  onChange,
  projectId,
}: {
  value: ReportRequest
  onChange: (next: ReportRequest) => void
  projectId?: string
}) {
  const set = (patch: Partial<ReportRequest>) => onChange({ ...value, ...patch })

  return (
    <div className="stack--sm">
      <div className="row row--wrap" style={{ gap: 28, alignItems: 'flex-end' }}>
        <ScenarioSelector projectId={projectId} value={value.scenario} onChange={(s: ScenarioKey) => set({ scenario: s })} />
        <PeriodViewToggle
          value={value.view}
          onChange={(v) => set({ view: v === 'yearly' ? 'yearly' : 'monthly' })}
        />
        <div className="field" style={{ minWidth: 220 }}>
          <span className="field__label">Report style</span>
          <select
            className="input"
            value={value.report_style}
            onChange={(e) => set({ report_style: e.target.value as ReportStyle })}
          >
            {STYLES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label} — {s.hint}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field">
        <span className="field__label">Financial study</span>
        <div className="row row--wrap" style={{ gap: 18 }}>
          {TOGGLES.map((t) => (
            <label key={t.key} className="row" style={{ gap: 8, alignItems: 'center', cursor: 'pointer' }} title={t.hint}>
              <input
                type="checkbox"
                checked={value[t.key] as boolean}
                onChange={(e) => set({ [t.key]: e.target.checked } as Partial<ReportRequest>)}
              />
              <span style={{ fontSize: 13.5 }}>{t.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <span className="field__label">Written business plan</span>
        <div className="row row--wrap" style={{ gap: 18 }}>
          {TEXT_PLAN_TOGGLES.map((t) => {
            const disabled = t.key !== 'include_text_plan' && !value.include_text_plan
            return (
              <label
                key={t.key}
                className="row"
                style={{ gap: 8, alignItems: 'center', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1 }}
                title={t.hint}
              >
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={value[t.key] as boolean}
                  onChange={(e) => set({ [t.key]: e.target.checked } as Partial<ReportRequest>)}
                />
                <span style={{ fontSize: 13.5 }}>{t.label}</span>
              </label>
            )
          })}
        </div>
      </div>
    </div>
  )
}
