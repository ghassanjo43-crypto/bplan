/* Types mirroring backend/app/schemas/cash_flow.py */
import type { Severity } from './incomeStatement'

export type { Severity }
// A scenario id (named saved scenarios) or a legacy type string.
export type ScenarioKey = string
export type CFView = 'monthly' | 'yearly'

export interface CashFlowPeriod {
  index: number
  label: string
  period_type: 'monthly' | 'annual'
  start_date: string
  end_date: string
}

export interface CashFlowLineItem {
  key: string
  label: string
  classification: string
  level: number
  values_by_period: number[]
  total: number
  is_section_header: boolean
  is_subtotal: boolean
  is_grand_total: boolean
  drilldown_available: boolean
  note?: string | null
  children: CashFlowLineItem[]
}

export interface CashFlowTotals {
  net_cash_from_operating_activities: number[]
  net_cash_used_in_investing_activities: number[]
  net_cash_from_financing_activities: number[]
  net_change_in_cash: number[]
  opening_cash: number[]
  closing_cash: number[]
}

export interface CashReconciliationResult {
  closing_cash_cash_flow: number[]
  cash_balance_sheet: number[]
  difference: number[]
  max_difference: number
  status: 'reconciled' | 'not_reconciled'
}

export interface CashFlowWarning {
  code: string
  severity: Severity
  message: string
}

export interface CashFlowMetadata {
  project_id: string
  project_name: string
  scenario: ScenarioKey
  scenario_label: string
  view: string
  method: string
  currency: string
  statement_title: string
  period_caption: string
  generated_at: string
}

export interface CashFlowStatement {
  metadata: CashFlowMetadata
  periods: CashFlowPeriod[]
  rows: CashFlowLineItem[]
  totals: CashFlowTotals
  cash_reconciliation: CashReconciliationResult
  warnings: CashFlowWarning[]
}

export interface CashFlowSummary {
  project_id: string
  scenario: ScenarioKey
  currency: string
  net_operating_cash_flow: number
  net_investing_cash_flow: number
  net_financing_cash_flow: number
  net_change_in_cash: number
  closing_cash: number
  free_cash_flow: number
  reconciliation_status: string
}

export interface CFReconciliationCheck {
  key: string
  label: string
  passed: boolean
  severity: Severity
  detail: string | null
}

export interface CashFlowReconciliation {
  project_id: string
  scenario: ScenarioKey
  all_passed: boolean
  checks: CFReconciliationCheck[]
  warnings: CashFlowWarning[]
}
