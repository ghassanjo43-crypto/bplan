import { Modal } from '@/components/ui/Modal'
import { LoadingScreen } from '@/components/ui/Spinner'
import { ScenarioComparisonChart } from '@/components/analysis/ScenarioComparisonChart'
import { useScenarioComparison } from '@/api/financialAnalysisApi'
import { formatCurrency, formatPercent } from '@/utils/format'
import type { ScenarioMetric } from '@/types/financialAnalysis'

// Charts to draw (line comparison over time) — the ones that read best over time.
const CHART_KEYS = ['revenue', 'ebitda', 'net_profit', 'cash_balance', 'break_even', 'funding_requirement']

/** Headline number per metric per scenario (the summary shown in the table). */
function headline(metric: ScenarioMetric, values: number[]): number {
  switch (metric.key) {
    case 'gross_margin':          // percent → average across periods
      return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0
    case 'cash_balance':          // closing cash → end of horizon
    case 'break_even':            // cumulative net profit → final cumulative
      return values[values.length - 1] ?? 0
    case 'funding_requirement':   // trough of cumulative pre-financing cash = peak funding need
      return Math.max(0, -Math.min(0, ...values))
    default:                      // currency flows → total over the horizon
      return values.reduce((a, b) => a + b, 0)
  }
}

const fmt = (metric: ScenarioMetric, v: number, currency: string) =>
  metric.format === 'percent' ? formatPercent(v) : formatCurrency(v, currency)

export function ScenarioCompareModal({
  projectId, scenarioIds, onClose,
}: {
  projectId: string
  scenarioIds: string[]
  onClose: () => void
}) {
  const { data, isLoading } = useScenarioComparison(projectId, 'yearly', scenarioIds)

  return (
    <Modal open wide title={`Compare Scenarios (${scenarioIds.length})`} onClose={onClose} footer={
      <button className="btn btn--primary" onClick={onClose}>Close</button>
    }>
      {isLoading || !data ? (
        <LoadingScreen />
      ) : (
        <div className="stack">
          {/* Headline metrics table */}
          <div className="table-wrap">
            <table className="table">
              <thead><tr>
                <th>Metric</th>
                {(data.metrics[0]?.series ?? []).map((s) => (
                  <th key={s.scenario} style={{ textAlign: 'right' }}>{s.label}</th>
                ))}
              </tr></thead>
              <tbody>
                {data.metrics.map((m) => (
                  <tr key={m.key}>
                    <td>{m.label}</td>
                    {m.series.map((s) => (
                      <td key={s.scenario} className="table__num">{fmt(m, headline(m, s.values), data.currency)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ fontSize: 12 }}>
            Currency flows are totals over the plan; margins are averages; cash balance and cumulative
            metrics are end-of-horizon; funding requirement is the peak cash shortfall before financing.
            All figures come from the same statement engines as the Income Statement, Balance Sheet and
            Cash Flow.
          </p>

          {/* Charts */}
          <div className="chart-grid">
            {CHART_KEYS.map((k) => {
              const metric = data.metrics.find((m) => m.key === k)
              return metric ? (
                <ScenarioComparisonChart key={k} metric={metric} periods={data.periods} currency={data.currency} />
              ) : null
            })}
          </div>
        </div>
      )}
    </Modal>
  )
}
