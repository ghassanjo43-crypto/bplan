import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SectionCard } from '@/components/SectionCard'
import { LoadingScreen } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useProjectContext } from '@/layouts/ProjectContext'
import { useCashFlow, useCashFlowReconciliation, useCashFlowSummary } from '@/api/cashFlowApi'
import type { CashFlowLineItem, CFView, ScenarioKey } from '@/types/cashFlow'
import { ScenarioSelector } from '@/components/financials/ScenarioSelector'
import { PeriodViewToggle } from '@/components/financials/PeriodViewToggle'
import { ExportButtons } from '@/components/financials/ExportButtons'
import { CashFlowHeader } from '@/components/financials/CashFlowHeader'
import { CashFlowMetricCards } from '@/components/financials/CashFlowMetricCards'
import { CashFlowWarningBanner } from '@/components/financials/CashFlowWarningBanner'
import { CashFlowTable } from '@/components/financials/CashFlowTable'
import { CashReconciliationPanel } from '@/components/financials/CashReconciliationPanel'
import { CashFlowReconciliationPanel } from '@/components/financials/CashFlowReconciliationPanel'
import { CashFlowDrilldown } from '@/components/financials/CashFlowDrilldown'

export function CashFlowPage() {
  const { projectId } = useProjectContext()
  const [scenario, setScenario] = useState<ScenarioKey>('base')
  const [view, setView] = useState<CFView>('yearly')
  const [drill, setDrill] = useState<CashFlowLineItem | null>(null)

  const cfQ = useCashFlow(projectId, scenario, view)
  const summaryQ = useCashFlowSummary(projectId, scenario)
  const reconQ = useCashFlowReconciliation(projectId, scenario)

  return (
    <>
      <PageHeader
        breadcrumb="Financial Statements"
        title="Cash Flow Statement"
        subtitle="An IFRS-style Statement of Cash Flows (indirect method) reconciled to the balance sheet cash."
      />

      <div className="stack">
        <SectionCard>
          <div className="row row--wrap" style={{ gap: 28, alignItems: 'flex-end' }}>
            <ScenarioSelector projectId={projectId} value={scenario} onChange={setScenario} />
            <PeriodViewToggle value={view} onChange={setView} />
            <div className="spacer" />
            <ExportButtons />
          </div>
        </SectionCard>

        {cfQ.isLoading ? (
          <LoadingScreen label="Building the cash flow statement…" />
        ) : cfQ.isError || !cfQ.data ? (
          <SectionCard>
            <EmptyState icon="⚠" title="Could not generate the cash flow statement"
              description={(cfQ.error as Error)?.message ?? 'Ensure assumptions are entered and the backend is running.'} />
          </SectionCard>
        ) : (
          <>
            {summaryQ.data && <CashFlowMetricCards summary={summaryQ.data} />}
            <CashFlowWarningBanner warnings={cfQ.data.warnings} />

            <div className="card">
              <div className="card__body">
                <CashFlowHeader meta={cfQ.data.metadata} />
                <CashFlowTable statement={cfQ.data} onDrilldown={setDrill} />
              </div>
            </div>

            <CashReconciliationPanel
              recon={cfQ.data.cash_reconciliation}
              totals={cfQ.data.totals}
              periods={cfQ.data.periods}
              currency={cfQ.data.metadata.currency}
            />
            <CashFlowReconciliationPanel data={reconQ.data} loading={reconQ.isLoading} />
          </>
        )}
      </div>

      {drill && (
        <CashFlowDrilldown
          item={drill}
          periods={cfQ.data?.periods ?? []}
          currency={cfQ.data?.metadata.currency ?? 'USD'}
          onClose={() => setDrill(null)}
        />
      )}
    </>
  )
}
