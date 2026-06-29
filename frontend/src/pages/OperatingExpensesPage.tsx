import { CollectionPage } from '@/components/pages/CollectionPage'
import type { Column } from '@/components/DataTable'
import type { FormConfig } from '@/components/form/types'
import { SummaryCard } from '@/components/SummaryCard'
import { Badge } from '@/components/ui/Badge'
import type { ExpenseFrequency, OperatingExpense } from '@/types'
import { formatCurrency } from '@/utils/format'
import { expenseCategoryOptions, expenseFrequencyOptions, labelFor } from '@/utils/options'
import { useProjectContext } from '@/layouts/ProjectContext'

const config: FormConfig = [
  {
    title: 'Expense',
    fields: [
      { name: 'name', label: 'Expense Name', kind: 'text', required: true, span: 2, placeholder: 'e.g. Office Rent' },
      { name: 'category', label: 'Category', kind: 'select', options: expenseCategoryOptions, required: true },
      { name: 'amount', label: 'Amount', kind: 'currency', required: true },
      { name: 'frequency', label: 'Frequency', kind: 'select', options: expenseFrequencyOptions, required: true },
      { name: 'is_fixed', label: 'Fixed Cost', kind: 'switch', help: 'Fixed costs stay constant; variable costs scale with activity.' },
    ],
  },
  {
    title: 'Schedule & Tax',
    advanced: true,
    fields: [
      { name: 'start_date', label: 'Start Date', kind: 'date' },
      { name: 'end_date', label: 'End Date (optional)', kind: 'date' },
      { name: 'inflation_percent', label: 'Annual Escalation %', kind: 'percent', help: 'Yearly increase applied to this expense.' },
      { name: 'vat_applicable', label: 'This item is VAT-applicable', kind: 'switch', help: 'Marks whether this expense is subject to VAT at the project default rate (set on the Tax page). It does not set the rate.' },
      { name: 'notes', label: 'Notes', kind: 'textarea', span: 2 },
    ],
  },
]

const monthlyFactor: Record<ExpenseFrequency, number> = {
  monthly: 1,
  quarterly: 1 / 3,
  yearly: 1 / 12,
  one_time: 0,
}

export function OperatingExpensesPage({ embedded }: { embedded?: boolean } = {}) {
  const { currency } = useProjectContext()

  const columns: Column<OperatingExpense>[] = [
    { header: 'Name', cell: (r) => <strong>{r.name}</strong> },
    { header: 'Category', cell: (r) => labelFor(expenseCategoryOptions, r.category) },
    { header: 'Amount', align: 'right', cell: (r) => formatCurrency(r.amount, currency) },
    { header: 'Frequency', cell: (r) => <Badge tone="neutral">{labelFor(expenseFrequencyOptions, r.frequency)}</Badge> },
    { header: 'Monthly Equiv.', align: 'right', cell: (r) => formatCurrency(r.amount * monthlyFactor[r.frequency], currency) },
    { header: 'Type', cell: (r) => <Badge tone={r.is_fixed ? 'blue' : 'amber'}>{r.is_fixed ? 'Fixed' : 'Variable'}</Badge> },
  ]

  return (
    <CollectionPage<OperatingExpense>
      slug="operating-expenses"
      sectionKey="operating-expenses"
      itemNoun="Expense"
      embedded={embedded}
      config={config}
      columns={columns}
      emptyIcon="◷"
      emptyDescription="Capture recurring running costs like rent, software, marketing, and professional fees."
      renderSummary={(rows) => {
        const monthly = rows.reduce((s, r) => s + r.amount * monthlyFactor[r.frequency], 0)
        const oneTime = rows.filter((r) => r.frequency === 'one_time').reduce((s, r) => s + r.amount, 0)
        return (
          <div className="stat-grid">
            <SummaryCard label="Monthly Operating Cost" value={formatCurrency(monthly, currency)} accent="amber" />
            <SummaryCard label="Annual Operating Cost" value={formatCurrency(monthly * 12, currency)} accent="slate" />
            <SummaryCard label="One-time Costs" value={formatCurrency(oneTime, currency)} accent="blue" />
          </div>
        )
      }}
    />
  )
}
