import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/PageHeader'
import { ExcelModelButton } from '@/components/reports/ExcelModelButton'
import { SaveBar } from '@/components/SaveBar'
import { SectionCard } from '@/components/SectionCard'
import { ReviewSection, type SummaryRow } from '@/components/ReviewSection'
import { LoadingScreen } from '@/components/ui/Spinner'
import { exportJsonUrl } from '@/api/hooks'
import { downloadFile } from '@/api/client'
import { useProjectContext } from '@/layouts/ProjectContext'
import { useReview } from '@/api/hooks'
import { useToast } from '@/components/ui/Toast'
import { formatCurrency, formatDate, formatPercent, formatNumber } from '@/utils/format'
import {
  businessModelOptions,
  labelFor,
  projectionPeriodOptions,
  reportingStandardOptions,
} from '@/utils/options'

export function ReviewPage() {
  const { projectId, project, currency } = useProjectContext()
  const { data: review, isLoading } = useReview(projectId)
  const { notify } = useToast()

  if (isLoading || !project || !review) return <LoadingScreen />

  const setup = project.setup
  const pct = (key: string) => review.completion.sections.find((s) => s.key === key)?.complete
  const sectionPercent = (key: string) => (pct(key) ? 100 : 0)

  const setupRows: SummaryRow[] = setup
    ? [
        { label: 'Business Name', value: setup.business_name },
        { label: 'Project Name', value: setup.project_name || '—' },
        { label: 'Industry', value: setup.industry || '—' },
        { label: 'Business Model', value: labelFor(businessModelOptions, setup.business_model) },
        { label: 'Location', value: [setup.city, setup.country].filter(Boolean).join(', ') || '—' },
        { label: 'Currency', value: setup.currency },
        { label: 'Start Date', value: formatDate(setup.projection_start_date) },
        { label: 'Period', value: labelFor(projectionPeriodOptions, setup.projection_period) },
        { label: 'Reporting Standard', value: labelFor(reportingStandardOptions, setup.reporting_standard) },
        { label: 'Scenario Mode', value: setup.scenario_mode_enabled ? 'Enabled' : 'Disabled' },
      ]
    : []

  const totalStaffCost = project.staffing
    .filter((s) => s.active)
    .reduce((sum, s) => sum + s.monthly_salary * s.number_of_employees, 0)
  const totalStartup = project.startup_costs.reduce((s, c) => s + c.amount, 0)
  const totalCapex = project.fixed_assets.reduce((s, a) => s + a.purchase_amount, 0)
  const totalFunding =
    (project.financing?.equity?.founder_capital ?? 0) +
    (project.financing?.equity?.investor_equity ?? 0) +
    (project.financing?.loans ?? []).reduce((s, l) => s + l.amount, 0) +
    (project.financing?.grants ?? []).reduce((s, g) => s + g.amount, 0)

  const handleExport = async () => {
    try {
      await downloadFile(exportJsonUrl(projectId), `business-plan-${projectId}.json`)
      notify('Assumptions exported as JSON')
    } catch (e) {
      notify((e as Error).message || 'Export failed', 'error')
    }
  }

  return (
    <>
      <PageHeader
        breadcrumb="Business Plan · Planning"
        title="Review & Completion"
        subtitle="A full summary of every assumption before generating financial statements."
        actions={
          <>
            <button className="btn btn--secondary" onClick={handleExport}>
              ⤓ Export JSON
            </button>
            <Link className="btn btn--secondary" to={`/projects/${projectId}/reports`}>
              ⎙ Business Plan Report
            </Link>
            <ExcelModelButton projectId={projectId} />
            <button className="btn btn--primary" disabled={!review.ready_for_projection} title={
              review.ready_for_projection ? 'Ready to generate statements' : 'Complete required sections first'
            }>
              Generate Statements →
            </button>
          </>
        }
      />

      <div className="stack">
        {/* Readiness banner */}
        {review.ready_for_projection ? (
          <div className="banner banner--success">
            <span className="banner__icon">✓</span>
            <div>
              <strong>Plan is ready for projection.</strong> All required sections are complete. You can now generate
              the Profit &amp; Loss, Cash Flow, and Balance Sheet projections.
            </div>
          </div>
        ) : (
          <div className="banner banner--warning">
            <span className="banner__icon">⚠</span>
            <div>
              <strong>Some required sections are incomplete.</strong> Resolve the blocking items below before
              generating statements.
            </div>
          </div>
        )}

        {/* Completion checklist */}
        <SectionCard title="Completion Checklist" subtitle={`${review.completion.completion_percent}% complete · ${review.completion.completed_sections} of ${review.completion.total_sections} sections`} icon="✓">
          <div className="checklist">
            {review.completion.sections.map((s) => {
              const mark = s.complete ? 'done' : s.required ? 'required' : 'todo'
              return (
                <div className="checklist__item" key={s.key}>
                  <span className={`checklist__mark checklist__mark--${mark}`}>
                    {s.complete ? '✓' : s.required ? '!' : '○'}
                  </span>
                  <span style={{ flex: 1 }}>{s.label}</span>
                  {s.item_count !== null && s.item_count !== undefined && (
                    <span className="muted" style={{ fontSize: 12 }}>{s.item_count} items</span>
                  )}
                  {s.required && !s.complete && <span className="badge badge--amber">Required</span>}
                </div>
              )
            })}
          </div>
        </SectionCard>

        {/* Blocking issues / warnings */}
        {(review.blocking_issues.length > 0 || review.warnings.length > 0) && (
          <SectionCard title="Validation" subtitle="Issues detected across your assumptions." icon="⚠">
            {review.blocking_issues.map((b, i) => (
              <div className="banner banner--warning" key={`b-${i}`} style={{ marginBottom: 8 }}>
                <span className="banner__icon">⛔</span>
                <div>{b}</div>
              </div>
            ))}
            {review.warnings.map((w, i) => (
              <div className="banner banner--info" key={`w-${i}`} style={{ marginBottom: 8 }}>
                <span className="banner__icon">ℹ</span>
                <div>{w}</div>
              </div>
            ))}
            {review.blocking_issues.length === 0 && review.warnings.length === 0 && (
              <p className="muted">No issues found.</p>
            )}
          </SectionCard>
        )}

        {/* Section summaries */}
        <ReviewSection title="Project Setup" slug="setup" icon="◧" percent={sectionPercent('setup')} rows={setupRows} empty="Project setup has not been completed." />

        <ReviewSection
          title="Products & Services" slug="products" icon="◫" percent={sectionPercent('products')}
          rows={[
            { label: 'Total Offerings', value: project.products.length },
            { label: 'Active', value: project.products.filter((p) => p.active).length },
            { label: 'Revenue Assumptions Set', value: project.revenue.length },
            { label: 'Direct Costs Set', value: project.direct_costs.length },
          ]}
          empty="No products defined yet."
        />

        <ReviewSection
          title="Staffing" slug="staffing" icon="◶" percent={sectionPercent('staffing')}
          rows={[
            { label: 'Positions', value: project.staffing.length },
            { label: 'Total Headcount', value: project.staffing.reduce((s, r) => s + r.number_of_employees, 0) },
            { label: 'Base Payroll / mo', value: formatCurrency(totalStaffCost, currency) },
            { label: 'Base Payroll / yr', value: formatCurrency(totalStaffCost * 12, currency) },
          ]}
          empty="No staff roles defined yet."
        />

        <ReviewSection
          title="Operating Expenses" slug="operating-expenses" icon="◷" percent={sectionPercent('operating-expenses')}
          rows={[{ label: 'Expense Lines', value: project.operating_expenses.length }]}
          empty="No operating expenses defined yet."
        />

        <ReviewSection
          title="Startup Costs & CapEx" slug="startup-costs" icon="◰" percent={sectionPercent('startup-costs')}
          rows={[
            { label: 'Startup Cost Items', value: project.startup_costs.length },
            { label: 'Total Startup Costs', value: formatCurrency(totalStartup, currency) },
            { label: 'Fixed Assets', value: project.fixed_assets.length },
            { label: 'Total CapEx', value: formatCurrency(totalCapex, currency) },
          ]}
        />

        <ReviewSection
          title="Working Capital" slug="working-capital" icon="◲" percent={sectionPercent('working-capital')}
          rows={
            project.working_capital
              ? [
                  { label: 'AR Days', value: `${project.working_capital.accounts_receivable_days} days` },
                  { label: 'AP Days', value: `${project.working_capital.accounts_payable_days} days` },
                  { label: 'Inventory Days', value: `${project.working_capital.inventory_days} days` },
                  { label: 'Min. Cash Balance', value: formatCurrency(project.working_capital.minimum_cash_balance, currency) },
                ]
              : undefined
          }
          empty="Working capital assumptions not set."
        />

        <ReviewSection
          title="Financing" slug="financing" icon="◳" percent={sectionPercent('financing')}
          rows={[
            { label: 'Founder Capital', value: formatCurrency(project.financing?.equity?.founder_capital ?? 0, currency) },
            { label: 'Investor Equity', value: formatCurrency(project.financing?.equity?.investor_equity ?? 0, currency) },
            { label: 'Loans', value: project.financing?.loans?.length ?? 0 },
            { label: 'Total Funding', value: formatCurrency(totalFunding, currency) },
          ]}
        />

        <ReviewSection
          title="Tax & Regulatory" slug="tax" icon="⊞" percent={sectionPercent('tax')}
          rows={
            project.tax
              ? [
                  { label: 'Corporate Tax Rate', value: formatPercent(project.tax.corporate_tax_rate) },
                  { label: 'VAT Rate', value: formatPercent(project.tax.vat_rate) },
                  { label: 'Withholding Tax', value: formatPercent(project.tax.withholding_tax_rate) },
                ]
              : undefined
          }
          empty="Tax assumptions not set."
        />

        <ReviewSection
          title="Scenarios" slug="scenarios" icon="⊟" percent={sectionPercent('scenarios')}
          rows={[{ label: 'Scenarios Defined', value: project.scenarios.length }]}
          empty="No scenarios defined yet."
        />

        <ReviewSection
          title="KPIs & Targets" slug="kpis" icon="⊡" percent={sectionPercent('kpis')}
          rows={
            project.kpis
              ? [
                  { label: 'Target Gross Margin', value: formatPercent(project.kpis.target_gross_margin_percent ?? undefined) },
                  { label: 'Target Net Margin', value: formatPercent(project.kpis.target_net_profit_margin_percent ?? undefined) },
                  { label: 'Break-even Target', value: formatDate(project.kpis.break_even_target_date) },
                  { label: 'Min. Monthly Revenue', value: formatCurrency(project.kpis.min_monthly_revenue_target, currency) },
                  { label: 'CAC Target', value: formatCurrency(project.kpis.cac_target, currency) },
                  { label: 'LTV Target', value: formatCurrency(project.kpis.ltv_target, currency) },
                ]
              : undefined
          }
          empty="KPI targets not set."
        />

        <SectionCard title="Next: Financial Statements" subtitle="What this plan unlocks once complete." icon="→">
          <p className="muted" style={{ fontSize: 13.5, marginBottom: 12 }}>
            These assumptions form the foundation for the projection engine. The next development phase will generate:
          </p>
          <div className="row row--wrap" style={{ gap: 8 }}>
            {['Profit & Loss', 'Cash Flow', 'Balance Sheet', 'Break-even Analysis', 'Scenario Comparison', 'Investor Report'].map((x) => (
              <span key={x} className="badge badge--neutral">{x}</span>
            ))}
          </div>
          <div className="muted text-mono" style={{ fontSize: 12, marginTop: 12 }}>
            {formatNumber(project.products.length)} products · {formatNumber(project.staffing.length)} roles ·{' '}
            {formatNumber(project.operating_expenses.length)} expenses captured
          </div>
        </SectionCard>
      </div>

      <SaveBar slug="review" />
    </>
  )
}
