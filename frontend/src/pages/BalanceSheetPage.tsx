import { useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SectionCard } from '@/components/SectionCard'
import { LoadingScreen } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useProjectContext } from '@/layouts/ProjectContext'
import {
  useBalanceSheet,
  useBalanceSheetReconciliation,
  useBalanceSheetSummary,
} from '@/api/balanceSheetApi'
import type { BalanceSheetLineItem, BSView, ScenarioKey } from '@/types/balanceSheet'
import { ScenarioSelector } from '@/components/financials/ScenarioSelector'
import { PeriodViewToggle } from '@/components/financials/PeriodViewToggle'
import { ExportButtons } from '@/components/financials/ExportButtons'
import { BalanceSheetHeader } from '@/components/financials/BalanceSheetHeader'
import { BalanceSheetMetricCards } from '@/components/financials/BalanceSheetMetricCards'
import { BalanceSheetWarningBanner } from '@/components/financials/BalanceSheetWarningBanner'
import { BalanceSheetTable } from '@/components/financials/BalanceSheetTable'
import { BalanceCheckPanel } from '@/components/financials/BalanceCheckPanel'
import { BalanceSheetReconciliationPanel } from '@/components/financials/BalanceSheetReconciliationPanel'
import { BalanceSheetDrilldown } from '@/components/financials/BalanceSheetDrilldown'

export function BalanceSheetPage() {
  const { projectId } = useProjectContext()
  const [scenario, setScenario] = useState<ScenarioKey>('base')
  const [view, setView] = useState<BSView>('yearly')
  const [drill, setDrill] = useState<{ key: string; label: string } | null>(null)

  const bsQ = useBalanceSheet(projectId, scenario, view)
  const summaryQ = useBalanceSheetSummary(projectId, scenario)
  const reconQ = useBalanceSheetReconciliation(projectId, scenario)

  const onDrilldown = (item: BalanceSheetLineItem) => setDrill({ key: item.key, label: item.label })

  return (
    <>
      <PageHeader
        breadcrumb="Financial Statements"
        title="Balance Sheet"
        subtitle="An IFRS-style Statement of Financial Position generated from your assumptions and the income statement."
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

        {bsQ.isLoading ? (
          <LoadingScreen label="Building the balance sheet…" />
        ) : bsQ.isError || !bsQ.data ? (
          <SectionCard>
            <EmptyState icon="⚠" title="Could not generate the balance sheet"
              description={(bsQ.error as Error)?.message ?? 'Ensure assumptions are entered and the backend is running.'} />
          </SectionCard>
        ) : (
          <>
            {summaryQ.data && <BalanceSheetMetricCards summary={summaryQ.data} />}
            <BalanceSheetWarningBanner warnings={bsQ.data.warnings} />

            <div className="card">
              <div className="card__body">
                <BalanceSheetHeader meta={bsQ.data.metadata} />
                <BalanceSheetTable statement={bsQ.data} onDrilldown={onDrilldown} />
              </div>
            </div>

            <BalanceCheckPanel check={bsQ.data.balance_check} periods={bsQ.data.periods} currency={bsQ.data.metadata.currency} />
            <BalanceSheetReconciliationPanel data={reconQ.data} loading={reconQ.isLoading} />
          </>
        )}
      </div>

      {drill && (
        <BalanceSheetDrilldown
          projectId={projectId}
          scenario={scenario}
          lineKey={drill.key}
          lineLabel={drill.label}
          onClose={() => setDrill(null)}
        />
      )}
    </>
  )
}
