import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SectionCard } from '@/components/SectionCard'
import { LoadingScreen } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useProjectContext } from '@/layouts/ProjectContext'
import {
  useIncomeStatement,
  useIncomeStatementReconciliation,
} from '@/api/incomeStatementApi'
import type { ScenarioKey, ViewKey } from '@/types/incomeStatement'
import { ScenarioSelector } from '@/components/financials/ScenarioSelector'
import { PeriodViewToggle } from '@/components/financials/PeriodViewToggle'
import { ExportButtons } from '@/components/financials/ExportButtons'
import { FinancialStatementHeader } from '@/components/financials/FinancialStatementHeader'
import { FinancialMetricCards } from '@/components/financials/FinancialMetricCards'
import { StatementWarningBanner } from '@/components/financials/StatementWarningBanner'
import { ReconciliationPanel } from '@/components/financials/ReconciliationPanel'
import { FinancialStatementTable } from '@/components/financials/FinancialStatementTable'

export function IncomeStatementPage() {
  const { projectId } = useProjectContext()
  const [scenario, setScenario] = useState<ScenarioKey>('base')
  const [view, setView] = useState<ViewKey>('yearly')

  const stmtQ = useIncomeStatement(projectId, scenario, view)
  const reconQ = useIncomeStatementReconciliation(projectId, scenario)

  return (
    <>
      <PageHeader
        breadcrumb="Financial Statements"
        title="Income Statement"
        subtitle="An IFRS-style Statement of Profit or Loss generated from your assumptions."
      />

      <div className="stack">
        {/* Controls */}
        <SectionCard>
          <div className="row row--wrap" style={{ gap: 28, alignItems: 'flex-end' }}>
            <ScenarioSelector projectId={projectId} value={scenario} onChange={setScenario} />
            <PeriodViewToggle value={view} onChange={setView} />
            <div className="spacer" />
            <ExportButtons />
          </div>
        </SectionCard>

        {stmtQ.isLoading ? (
          <LoadingScreen label="Building the statement…" />
        ) : stmtQ.isError || !stmtQ.data ? (
          <SectionCard>
            <EmptyState
              icon="⚠"
              title="Could not generate the statement"
              description={(stmtQ.error as Error)?.message ?? 'Please ensure assumptions are entered and the backend is running.'}
            />
          </SectionCard>
        ) : stmtQ.data.totals.total_revenue === 0 ? (
          <SectionCard>
            <EmptyState
              icon="◴"
              title="No revenue yet"
              description="Add products and revenue assumptions to generate a meaningful income statement."
            />
          </SectionCard>
        ) : (
          <>
            <FinancialMetricCards
              totals={stmtQ.data.totals}
              margins={stmtQ.data.margins}
              currency={stmtQ.data.metadata.currency}
            />

            <StatementWarningBanner warnings={stmtQ.data.warnings} />

            <div className="card">
              <div className="card__body">
                <FinancialStatementHeader meta={stmtQ.data.metadata} />
                <FinancialStatementTable statement={stmtQ.data} />
              </div>
            </div>

            <ReconciliationPanel data={reconQ.data} loading={reconQ.isLoading} />
          </>
        )}
      </div>
    </>
  )
}
