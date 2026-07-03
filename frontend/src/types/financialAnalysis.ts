/* Types mirroring backend/app/schemas/financial_analysis.py */

// A scenario id (named saved scenarios) or a legacy type string.
export type ScenarioKey = string
export type FAView = 'monthly' | 'yearly'
export type Severity = 'info' | 'warning' | 'critical'
export type ChartType =
  | 'line' | 'bar' | 'grouped_bar' | 'stacked_bar' | 'donut' | 'pie' | 'area' | 'waterfall' | 'combo'

export interface ChartSeries {
  key: string
  label: string
  format: string          // currency | percent | ratio | number
  color?: string | null
  type?: string | null    // bar | line (combo)
  axis: string            // left | right
}

export interface FinancialAnalysisChart {
  key: string
  title: string
  description?: string | null
  chart_type: ChartType
  unit: string
  data: Record<string, number | string>[]
  series: ChartSeries[]
  source_statement: string
  insight?: string | null
  warnings: string[]
}

export interface FinancialAnalysisSection {
  key: string
  title: string
  description?: string | null
  charts: FinancialAnalysisChart[]
}

export interface FinancialAnalysisKPI {
  key: string
  label: string
  value: number | null
  format: string
  group: string           // profitability | liquidity | leverage | efficiency | cash
  hint?: string | null
  good?: boolean | null
}

export interface FinancialAnalysisWarning {
  code: string
  severity: Severity
  message: string
}

export interface FinancialAnalysisMetadata {
  project_id: string
  project_name: string
  scenario: ScenarioKey
  scenario_label: string
  view: string
  currency: string
  generated_at: string
}

export interface FinancialAnalysisResponse {
  metadata: FinancialAnalysisMetadata
  periods: { index: number; label: string; period_type: string }[]
  kpis: FinancialAnalysisKPI[]
  sections: FinancialAnalysisSection[]
  insights: string[]
  warnings: FinancialAnalysisWarning[]
}

export interface ScenarioSeries {
  scenario: string
  label: string
  values: number[]
}

export interface ScenarioMetric {
  key: string
  label: string
  format: string
  series: ScenarioSeries[]
}

export interface ScenarioComparisonResponse {
  project_id: string
  project_name: string
  view: string
  currency: string
  periods: string[]
  metrics: ScenarioMetric[]
}
