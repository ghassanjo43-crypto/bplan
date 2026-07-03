/* Types mirroring backend/app/schemas/income_statement.py */

// A scenario id (named saved scenarios) or a legacy type string.
export type ScenarioKey = string
export type ViewKey = 'monthly' | 'yearly'
export type Severity = 'info' | 'warning' | 'critical'

export interface ISPeriod {
  index: number
  label: string
  period_type: 'month' | 'year'
  year_index: number
  month: number | null
  year: number
  start_date: string
  end_date: string
}

export interface ISLineItem {
  key: string
  label: string
  classification: string
  values_by_period: number[]
  total: number
  is_subtotal: boolean
  is_grand_total: boolean
  display_order: number
  drilldown_available: boolean
  note: string | null
  children: ISLineItem[]
}

export interface ISSection {
  key: string
  title: string
  display_order: number
  line_items: ISLineItem[]
  subtotal: ISLineItem | null
}

export interface ISTotals {
  total_revenue: number
  total_cost_of_sales: number
  gross_profit: number
  total_other_income: number
  total_operating_expenses: number
  operating_profit: number
  ebitda: number
  total_finance_costs: number
  profit_before_tax: number
  income_tax_expense: number
  profit_for_period: number
}

export interface ISMargins {
  gross_margin_pct: number[]
  ebitda: number[]
  ebitda_margin_pct: number[]
  operating_margin_pct: number[]
  net_margin_pct: number[]
  gross_margin_total_pct: number
  ebitda_margin_total_pct: number
  operating_margin_total_pct: number
  net_margin_total_pct: number
}

export interface ISWarning {
  code: string
  severity: Severity
  message: string
}

export interface ISMetadata {
  project_id: string
  project_name: string
  scenario: ScenarioKey
  scenario_label: string
  view: ViewKey
  currency: string
  statement_title: string
  period_caption: string
  generated_at: string
}

export interface IncomeStatement {
  metadata: ISMetadata
  periods: ISPeriod[]
  sections: ISSection[]
  totals: ISTotals
  margins: ISMargins
  analytical: ISLineItem[]
  warnings: ISWarning[]
}

export interface IncomeStatementSummary {
  project_id: string
  scenario: ScenarioKey
  currency: string
  total_revenue: number
  gross_profit: number
  ebitda: number
  operating_profit: number
  profit_before_tax: number
  net_profit: number
  gross_margin: number
  ebitda_margin: number
  net_profit_margin: number
}

export interface ReconciliationCheck {
  key: string
  label: string
  passed: boolean
  severity: Severity
  detail: string | null
}

export interface IncomeStatementReconciliation {
  project_id: string
  scenario: ScenarioKey
  all_passed: boolean
  checks: ReconciliationCheck[]
  warnings: ISWarning[]
}
