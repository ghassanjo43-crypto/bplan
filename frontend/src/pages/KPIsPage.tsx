import { SingletonFormPage } from '@/components/pages/SingletonFormPage'
import type { FormConfig } from '@/components/form/types'
import type { KPIAssumption } from '@/types'

const config: FormConfig = [
  {
    title: 'Profitability Targets',
    subtitle: 'Margin goals management is steering toward.',
    icon: '⊡',
    fields: [
      { name: 'target_gross_margin_percent', label: 'Target Gross Margin', kind: 'percent', help: 'Revenue minus direct costs, as a % of revenue.' },
      { name: 'target_ebitda_margin_percent', label: 'Target EBITDA Margin', kind: 'percent', allowNegative: true, help: 'Earnings before interest, tax, depreciation & amortization.' },
      { name: 'target_net_profit_margin_percent', label: 'Target Net Profit Margin', kind: 'percent', allowNegative: true },
      { name: 'break_even_target_date', label: 'Break-even Target Date', kind: 'date', help: 'When the business expects to stop losing money.' },
    ],
  },
  {
    title: 'Cash & Revenue Targets',
    icon: '◰',
    fields: [
      { name: 'min_monthly_revenue_target', label: 'Min. Monthly Revenue', kind: 'currency' },
      { name: 'min_cash_balance_target', label: 'Target minimum cash balance (reporting)', kind: 'currency', help: 'Reporting benchmark only — compared against projected cash. The operating cash reserve that affects funding/cash-flow is set in Working Capital.' },
    ],
  },
  {
    title: 'Investor Metrics',
    subtitle: 'Unit economics and return metrics investors look for.',
    icon: '⊟',
    fields: [
      { name: 'cac_target', label: 'CAC Target', kind: 'currency', help: 'Customer Acquisition Cost — cost to win one customer.' },
      { name: 'ltv_target', label: 'LTV Target', kind: 'currency', help: 'Customer Lifetime Value — total profit from one customer.' },
      { name: 'payback_period_target_months', label: 'Payback Period', kind: 'number', unit: 'months', help: 'Months to recover the cost of acquiring a customer.' },
      { name: 'roi_target_percent', label: 'ROI Target', kind: 'percent', allowNegative: true, help: 'Return on investment.' },
      { name: 'dscr_target', label: 'DSCR Target', kind: 'number', help: 'Debt Service Coverage Ratio — operating income ÷ debt payments.' },
      { name: 'current_ratio_target', label: 'Current Ratio Target', kind: 'number', help: 'Current assets ÷ current liabilities; >1 indicates liquidity.' },
    ],
  },
]

export function KPIsPage() {
  return <SingletonFormPage<KPIAssumption> slug="kpis" sectionKey="kpis" config={config} />
}
