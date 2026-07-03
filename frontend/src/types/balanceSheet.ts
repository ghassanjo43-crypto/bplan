/* Types mirroring backend/app/schemas/balance_sheet.py */
import type { Severity } from './incomeStatement'

export type { Severity }
// A scenario id (named saved scenarios) or a legacy type string.
export type ScenarioKey = string
export type BSView = 'monthly' | 'yearly'

export interface BalanceSheetPeriod {
  index: number
  label: string
  period_type: 'monthly' | 'annual'
  as_at_date: string
}

export interface BalanceSheetLineItem {
  key: string
  label: string
  classification: string
  level: number
  values_by_period: number[]
  is_header: boolean
  is_subtotal: boolean
  is_grand_total: boolean
  is_balance_check: boolean
  drilldown_available: boolean
  note?: string | null
  children: BalanceSheetLineItem[]
}

export interface BalanceCheckResult {
  values_by_period: number[]
  is_balanced_by_period: boolean[]
  max_difference: number
  status: 'balanced' | 'out_of_balance'
}

export interface BalanceSheetTotals {
  total_non_current_assets: number[]
  total_current_assets: number[]
  total_assets: number[]
  total_equity: number[]
  total_non_current_liabilities: number[]
  total_current_liabilities: number[]
  total_liabilities: number[]
  total_equity_and_liabilities: number[]
}

export interface BalanceSheetWarning {
  code: string
  severity: Severity
  message: string
}

export interface BalanceSheetMetadata {
  project_id: string
  project_name: string
  scenario: ScenarioKey
  scenario_label: string
  view: string
  currency: string
  statement_title: string
  as_at_caption: string
  generated_at: string
}

export interface BalanceSheet {
  metadata: BalanceSheetMetadata
  periods: BalanceSheetPeriod[]
  rows: BalanceSheetLineItem[]
  totals: BalanceSheetTotals
  balance_check: BalanceCheckResult
  warnings: BalanceSheetWarning[]
}

export interface BalanceSheetSummary {
  project_id: string
  scenario: ScenarioKey
  currency: string
  total_assets: number
  cash: number
  net_working_capital: number
  total_borrowings: number
  total_equity: number
  inventory: number
  receivables: number
  payables: number
  current_ratio: number | null
  debt_to_equity: number | null
  balance_status: string
}

export interface BSReconciliationCheck {
  key: string
  label: string
  passed: boolean
  severity: Severity
  detail: string | null
}

export interface BalanceSheetReconciliation {
  project_id: string
  scenario: ScenarioKey
  all_passed: boolean
  checks: BSReconciliationCheck[]
  warnings: BalanceSheetWarning[]
}

export interface CashBridgeLine {
  key: string
  label: string
  values: number[]
}

export interface CashBridge {
  project_id: string
  scenario: string
  view: string
  currency: string
  periods: string[]
  opening_cash: number[]
  lines: CashBridgeLine[]
  closing_cash: number[]
}
