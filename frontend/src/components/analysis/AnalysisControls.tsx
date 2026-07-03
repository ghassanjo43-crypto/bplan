import { Link } from 'react-router-dom'
import { ScenarioSelector } from '@/components/financials/ScenarioSelector'
import { PeriodViewToggle } from '@/components/financials/PeriodViewToggle'
import { ExcelModelButton } from '@/components/reports/ExcelModelButton'
import type { FAView, ScenarioKey } from '@/types/financialAnalysis'

const SECTIONS: { key: string; label: string }[] = [
  { key: 'overview', label: 'Executive Overview' },
  { key: 'revenue', label: 'Revenue' },
  { key: 'cost_profitability', label: 'Cost & Profitability' },
  { key: 'cash', label: 'Cash Flow' },
  { key: 'balance_sheet', label: 'Balance Sheet' },
  { key: 'working_capital', label: 'Working Capital' },
  { key: 'scenarios', label: 'Scenario Comparison' },
]

export function AnalysisControls({
  scenario, onScenario, view, onView, section, onSection, projectId,
}: {
  scenario: ScenarioKey
  onScenario: (s: ScenarioKey) => void
  view: FAView
  onView: (v: FAView) => void
  section: string
  onSection: (s: string) => void
  projectId: string
}) {
  return (
    <div className="stack--sm">
      <div className="card">
        <div className="card__body">
          <div className="row row--wrap" style={{ gap: 28, alignItems: 'flex-end' }}>
            <ScenarioSelector projectId={projectId} value={scenario} onChange={onScenario} />
            <PeriodViewToggle value={view === 'yearly' ? 'yearly' : 'monthly'} onChange={(v) => onView(v === 'yearly' ? 'yearly' : 'monthly')} />
            <div className="spacer" />
            <div className="field" style={{ minWidth: 0 }}>
              <span className="field__label">Export</span>
              <div className="row" style={{ gap: 8 }}>
                <Link className="btn btn--primary btn--sm" to={`/projects/${projectId}/reports`}>
                  ⎙ Business Plan Report
                </Link>
                <ExcelModelButton projectId={projectId} className="btn btn--secondary btn--sm" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="tabs" style={{ marginBottom: 0 }}>
        {SECTIONS.map((s) => (
          <button key={s.key} className={`tab${section === s.key ? ' tab--active' : ''}`} onClick={() => onSection(s.key)}>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  )
}
