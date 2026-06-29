import { CollectionPage } from '@/components/pages/CollectionPage'
import type { Column } from '@/components/DataTable'
import type { FormConfig } from '@/components/form/types'
import { SummaryCard } from '@/components/SummaryCard'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import type { StaffRole } from '@/types'
import { formatCurrency, formatDate } from '@/utils/format'
import { departmentOptions, labelFor } from '@/utils/options'
import { useProjectContext } from '@/layouts/ProjectContext'

const config: FormConfig = [
  {
    title: 'Role',
    fields: [
      { name: 'department', label: 'Department', kind: 'select', options: departmentOptions, required: true },
      { name: 'job_title', label: 'Job Title', kind: 'text', required: true, placeholder: 'e.g. Software Engineer' },
      { name: 'number_of_employees', label: 'Number of Employees', kind: 'number', required: true, min: 1 },
      { name: 'monthly_salary', label: 'Monthly Salary (per employee)', kind: 'currency', required: true },
      { name: 'hiring_start_date', label: 'Hiring Start Date', kind: 'date' },
      { name: 'active', label: 'Active', kind: 'switch' },
    ],
  },
  {
    title: 'Compensation & Benefits',
    advanced: true,
    fields: [
      { name: 'annual_increase_percent', label: 'Annual Salary Increase', kind: 'percent' },
      { name: 'benefits_percent', label: 'Benefits %', kind: 'percent', help: 'Benefits as a percentage of base salary.' },
      { name: 'health_insurance_amount', label: 'Health Insurance (per employee)', kind: 'currency' },
      { name: 'visa_permit_cost', label: 'Visa / Work Permit Cost', kind: 'currency' },
      { name: 'bonus_amount', label: 'Bonus Amount', kind: 'currency' },
      { name: 'bonus_percent', label: 'Bonus %', kind: 'percent' },
      { name: 'sales_commission_percent', label: 'Sales Commission %', kind: 'percent' },
      { name: 'employer_social_security_percent', label: 'Employer Social Security % (override)', kind: 'percent', help: 'Optional role-specific override. Leave blank to use the global default set on the Tax & Regulatory page.' },
      { name: 'gratuity_percent', label: 'End-of-service / Gratuity %', kind: 'percent' },
      { name: 'notes', label: 'Notes', kind: 'textarea', span: 2 },
    ],
  },
]

export function StaffingPage() {
  const { currency } = useProjectContext()

  const columns: Column<StaffRole>[] = [
    { header: 'Department', cell: (r) => <Badge tone="blue">{labelFor(departmentOptions, r.department)}</Badge> },
    { header: 'Job Title', cell: (r) => <strong>{r.job_title}</strong> },
    { header: 'Headcount', align: 'right', cell: (r) => r.number_of_employees },
    { header: 'Salary / mo', align: 'right', cell: (r) => formatCurrency(r.monthly_salary, currency) },
    { header: 'Base Cost / mo', align: 'right', cell: (r) => formatCurrency(r.monthly_salary * r.number_of_employees, currency) },
    { header: 'Start', cell: (r) => formatDate(r.hiring_start_date) },
    { header: 'Status', cell: (r) => <ActiveBadge active={r.active} /> },
  ]

  return (
    <CollectionPage<StaffRole>
      slug="staffing"
      sectionKey="staffing"
      itemNoun="Role"
      config={config}
      columns={columns}
      modalWide
      emptyIcon="◶"
      emptyDescription="Add each position with headcount, salary, and benefits to build the payroll plan."
      renderSummary={(rows) => {
        const headcount = rows.filter((r) => r.active).reduce((s, r) => s + r.number_of_employees, 0)
        const monthly = rows.filter((r) => r.active).reduce((s, r) => s + r.monthly_salary * r.number_of_employees, 0)
        return (
          <div className="stat-grid">
            <SummaryCard label="Total Headcount" value={headcount} accent="blue" />
            <SummaryCard label="Base Payroll / mo" value={formatCurrency(monthly, currency)} accent="amber" />
            <SummaryCard label="Base Payroll / yr" value={formatCurrency(monthly * 12, currency)} accent="slate" />
          </div>
        )
      }}
    />
  )
}
