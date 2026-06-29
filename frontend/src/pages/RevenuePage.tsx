import { PerProductPage } from '@/components/pages/PerProductPage'
import type { FormConfig } from '@/components/form/types'
import type { ProductService, RevenueAssumption } from '@/types'
import { formatNumber, formatPercent } from '@/utils/format'
import { labelFor, paymentTermsOptions, refundBasisOptions, revenueTypeOptions } from '@/utils/options'

// First-month quantity means different things per revenue model — the help text
// adapts so users enter the right unit without a separate field per type.
const VOLUME_HELP: Record<string, string> = {
  unit_sales: 'Units sold in Month 1.',
  subscription: 'Active paying subscribers in Month 1.',
  service_contract: 'Contracts expected in Month 1.',
  project_based: 'Contracts / projects expected in Month 1.',
  commission: 'Commissionable transactions in Month 1.',
  licensing: 'Licenses active / sold in Month 1.',
  other: 'Sales quantity in Month 1.',
}

// Per-model price override: the product Selling Price is the master price; these
// only override it when a revenue model charges differently.
const overrideHelp = (price: number, label: string) =>
  `Optional override. Leave blank to use the product's Selling Price (${formatNumber(price)}) as the ${label}.`

function configFor(product: ProductService): FormConfig {
  const t = product.revenue_type
  return [
    {
      title: 'Volume & Growth',
      subtitle: 'How sales quantity starts and scales over time. This is the single master sales-quantity input.',
      icon: '◴',
      fields: [
        {
          name: 'starting_monthly_volume', label: 'First-month sales quantity', kind: 'number', required: true,
          help: `${VOLUME_HELP[t] ?? VOLUME_HELP.other} This is the master quantity that drives revenue — you don't enter it again per revenue model.`,
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
        {
          name: 'number_of_customers', label: 'Starting customer base', kind: 'number',
          visibleWhen: () => t === 'unit_sales' || t === 'other',
          help: 'Optional. The installed base of customers, used together with Purchase Frequency. Different from the first-month sales quantity above.',
        },
        { name: 'customer_growth_rate', label: 'Customer Growth Rate', kind: 'percent', allowNegative: true, max: 1000,
          visibleWhen: () => t === 'unit_sales' || t === 'other' },
      ],
    },
    // -- Revenue-type specific block ------------------------------------
    {
      title: 'Revenue Drivers',
      subtitle: `Pricing defaults to the product's Selling Price — only set an override below if “${labelFor(revenueTypeOptions, t)}” revenue is priced differently.`,
      icon: '◵',
      fields: [
        { name: 'average_order_value', label: 'Override Average Order Value', kind: 'currency', visibleWhen: () => t === 'unit_sales' || t === 'other',
          help: overrideHelp(product.selling_price, 'average order value') },
        { name: 'purchase_frequency', label: 'Purchase Frequency / yr', kind: 'number', visibleWhen: () => t === 'unit_sales' || t === 'other' },
        {
          name: 'repeat_purchase_rate', label: 'Repeat Purchase Rate', kind: 'percent', visibleWhen: () => t === 'unit_sales' || t === 'other',
          help: 'Share of customers who buy again.',
        },
        { name: 'subscription_price', label: 'Override Subscription Price', kind: 'currency', visibleWhen: () => t === 'subscription',
          help: overrideHelp(product.selling_price, 'subscription price') },
        {
          name: 'churn_rate', label: 'Monthly Churn Rate', kind: 'percent', visibleWhen: () => t === 'subscription',
          help: 'Percentage of subscribers lost each month.',
        },
        { name: 'contract_value', label: 'Override Contract Value', kind: 'currency', visibleWhen: () => t === 'service_contract' || t === 'project_based',
          help: overrideHelp(product.selling_price, 'value per contract') },
        { name: 'commission_rate', label: 'Commission Rate', kind: 'percent', visibleWhen: () => t === 'commission',
          help: 'Applied to the order value to earn commission revenue.' },
        { name: 'licensing_fee', label: 'Override Licensing Fee', kind: 'currency', visibleWhen: () => t === 'licensing',
          help: overrideHelp(product.selling_price, 'licensing fee') },
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
          help: 'Primary driver of when this stream collects cash (receivables). Overrides the Working Capital default collection days.',
        },
        {
          name: 'custom_payment_days', label: 'Custom Payment Days', kind: 'number', unit: 'days', min: 1,
          visibleWhen: (v) => v.payment_terms === 'custom',
          requiredWhen: (v) => v.payment_terms === 'custom',
          help: 'Required when Payment Terms is Custom. Number of days customers take to pay.',
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
