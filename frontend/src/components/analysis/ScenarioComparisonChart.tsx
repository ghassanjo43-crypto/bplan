import type { ScenarioMetric } from '@/types/financialAnalysis'
import type { ChartSeries } from '@/types/financialAnalysis'
import { ProfessionalLineChart } from '@/components/charts/ProfessionalLineChart'

// Coloured by position, so it works for any set of scenario ids (not just the
// three legacy types).
const PALETTE = ['#2563eb', '#059669', '#d97706', '#7c3aed']

/** Renders one scenario-comparison metric (by scenario id) as a line chart card. */
export function ScenarioComparisonChart({
  metric, periods, currency,
}: {
  metric: ScenarioMetric
  periods: string[]
  currency: string
}) {
  const data = periods.map((p, i) => {
    const row: Record<string, number | string> = { period: p }
    for (const s of metric.series) row[s.scenario] = s.values[i] ?? 0
    return row
  })
  const series: ChartSeries[] = metric.series.map((s, i) => ({
    key: s.scenario, label: s.label, format: metric.format, color: PALETTE[i % PALETTE.length], axis: 'left',
  }))
  const unit = metric.format === 'percent' ? 'percent' : 'currency'

  return (
    <section className="chart-card">
      <header className="chart-card__head">
        <h3 className="chart-card__title">{metric.label}</h3>
      </header>
      <div className="chart-card__body">
        <ProfessionalLineChart data={data} series={series} currency={currency} unit={unit} />
      </div>
      <footer className="chart-card__footer">Source: Projected financial statements (all scenarios)</footer>
    </section>
  )
}
