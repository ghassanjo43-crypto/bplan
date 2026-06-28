import { PerProductPage } from '@/components/pages/PerProductPage'
import type { FormConfig } from '@/components/form/types'
import type { ProductService, RevenueAssumption } from '@/types'
import { formatNumber, formatPercent } from '@/utils/format'
import { labelFor, paymentTermsOptions, refundBasisOptions, revenueTypeOptions } from '@/utils/options'

function configFor(product: ProductService): FormConfig {
  const t = product.revenue_type
  return [
    {
      title: 'Volume & Growth',
      subtitle: 'How sales volume starts and scales over time.',
      icon: '◴',
      fields: [
        {
          name: 'starting_monthly_volume', label: 'Starting Monthly Volume', kind: 'number', required: true,
          help: 'Units (or transactions) sold in the first month.',
        },
        {
          name: 'annual_growth_rate', label: 'Annual Sales Growth', kind: 'percent', allowNegative: true, max: 1000,
          help: 'Year-over-year sales growth as a percentage (e.g. enter 20 for +20% per year). May be negative; extreme values trigger a warning.',
        },
        {
          name: 'monthly_growth_rate', label: 'Monthly Growth (optional)', kind: 'percent', allowNegative: true, max: 1000,
          help: 'Optional override of the annual figure. Disabled while Annual Sales Growth has a value.',
          disabledWhen: (v) => v.annual_growth_rate !== null && v.annual_growth_rate !== undefined && v.annual_growth_rate !== '',
          disabledHint: 'Clear Annual Sales Growth to set a monthly rate instead.',
        },
        { name: 'number_of_customers', label: 'Number of Customers', kind: 'number' },
        { name: 'customer_growth_rate', label: 'Customer Growth Rate', kind: 'percent', allowNegative: true, max: 1000 },
      ],
    },
    // -- Revenue-type specific block ------------------------------------
    {
      title: 'Revenue Drivers',
      subtitle: `Fields tailored to “${labelFor(revenueTypeOptions, t)}” style revenue.`,
      icon: '◵',
      fields: [
        { name: 'average_order_value', label: 'Average Order Value', kind: 'currency', visibleWhen: () => t === 'unit_sales' || t === 'other' },
        { name: 'purchase_frequency', label: 'Purchase Frequency / yr', kind: 'number', visibleWhen: () => t === 'unit_sales' || t === 'other' },
        {
          name: 'repeat_purchase_rate', label: 'Repeat Purchase Rate', kind: 'percent', visibleWhen: () => t === 'unit_sales' || t === 'other',
          help: 'Share of customers who buy again.',
        },
        { name: 'subscription_price', label: 'Subscription Price', kind: 'currency', visibleWhen: () => t === 'subscription' },
        {
          name: 'churn_rate', label: 'Monthly Churn Rate', kind: 'percent', visibleWhen: () => t === 'subscription',
          help: 'Percentage of subscribers lost each month.',
        },
        { name: 'contract_value', label: 'Contract Value', kind: 'currency', visibleWhen: () => t === 'service_contract' || t === 'project_based' },
        { name: 'number_of_contracts', label: 'Number of Contracts', kind: 'number', visibleWhen: () => t === 'service_contract' || t === 'project_based' },
        { name: 'commission_rate', label: 'Commission Rate', kind: 'percent', visibleWhen: () => t === 'commission' },
        { name: 'licensing_fee', label: 'Licensing Fee', kind: 'currency', visibleWhen: () => t === 'licensing' },
      ],
    },
    {
      title: 'Adjustments & Collections',
      icon: '◷',
      fields: [
        { name: 'discount_percent', label: 'Discount %', kind: 'percent', help: 'Average discount applied to list price.' },
        { name: 'refund_percent', label: 'Refund / Return %', kind: 'percent' },
        { name: 'refund_basis', label: 'Refund Basis', kind: 'select', options: refundBasisOptions },
        {
          name: 'payment_terms', label: 'Payment Terms', kind: 'select', options: paymentTermsOptions,
          help: 'When customers pay — affects accounts receivable and cash flow.',
        },
        {
          name: 'custom_payment_days', label: 'Custom Payment Days', kind: 'number', unit: 'days',
          visibleWhen: (v) => v.payment_terms === 'custom',
        },
      ],
    },
    {
      title: 'Seasonality',
      advanced: true,
      fields: [
        {
          name: 'seasonality_enabled', label: 'Enable Seasonality', kind: 'switch', span: 2,
          help: 'Apply month-by-month multipliers so revenue reflects seasonal peaks and troughs.',
          hint: 'Per-month seasonality multipliers can be tuned once enabled.',
        },
      ],
    },
  ]
}

export function RevenuePage({ embedded }: { embedded?: boolean } = {}) {
  return (
    <PerProductPage<RevenueAssumption>
      slug="revenue"
      sectionKey="revenue"
      itemNoun="Revenue Assumptions"
      modalWide
      embedded={embedded}
      configFor={configFor}
      renderSummary={(a, product) =>
        a ? (
          <div className="stat-grid">
            <Tile label="Start Volume / mo" value={formatNumber(a.starting_monthly_volume)} />
            <Tile label="Annual Growth" value={formatPercent(a.annual_growth_rate)} />
            <Tile label="Payment Terms" value={labelFor(paymentTermsOptions, a.payment_terms)} />
            <Tile label="Discount" value={formatPercent(a.discount_percent)} />
          </div>
        ) : (
          <p className="muted" style={{ fontSize: 13 }}>
            No revenue assumptions yet for <strong>{product.name}</strong>. Configure how it generates revenue.
          </p>
        )
      }
    />
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat stat__accent-blue">
      <div className="stat__label">{label}</div>
      <div className="stat__value" style={{ fontSize: 18 }}>
        {value}
      </div>
    </div>
  )
}
