import { PerProductPage } from '@/components/pages/PerProductPage'
import type { FormConfig } from '@/components/form/types'
import type { ProductService, RevenueAssumption } from '@/types'
import { formatNumber, formatPercent } from '@/utils/format'
import {
  labelFor, paymentTermsOptions, recognitionMethodOptions, refundBasisOptions,
  revenueTimingOptions, revenueTypeOptions, sellingUnitLabel,
} from '@/utils/options'

// First-month quantity means different things per revenue model — the help text
// adapts so users enter the right unit without a separate field per type.
const VOLUME_HELP: Record<string, string> = {
  unit_sales: 'Quantity sold in Month 1 — measured in the product’s selling unit (pieces, Kg, grams, metric tons, litres, bottles, cartons, etc.).',
  subscription: 'Active paying subscribers in Month 1.',
  service_contract: 'Contracts expected in Month 1.',
  project_based: 'Contracts / projects expected in Month 1.',
  commission: 'Commissionable transactions in Month 1.',
  licensing: 'Licenses active / sold in Month 1.',
  other: 'Sales quantity in Month 1.',
}

// Derived end date for contract/project revenue = last day of (start + duration - 1).
function contractEndDate(start: unknown, durationRaw: unknown): string {
  const d = Number(durationRaw)
  if (!start || !Number.isFinite(d) || d < 1) return '—'
  const dt = new Date(String(start))
  if (Number.isNaN(dt.getTime())) return '—'
  dt.setMonth(dt.getMonth() + d) // first month after the contract window…
  dt.setDate(0) // …then back up to the last day of the final active month
  return dt.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

// Per-model price override: the product Selling Price is the master price; these
// only override it when a revenue model charges differently.
const overrideHelp = (price: number, label: string) =>
  `Optional override. Leave blank to use the product's Selling Price (${formatNumber(price)}) as the ${label}.`

function configFor(product: ProductService): FormConfig {
  const t = product.revenue_type
  const unit = sellingUnitLabel(product.selling_unit, product.unit_of_sale)
  return [
    {
      title: 'Timing & Recurrence',
      subtitle: 'Whether this revenue is one-time or recurring, and the period over which it appears in the projection.',
      icon: '◷',
      fields: [
        {
          name: 'revenue_timing', label: 'Revenue Timing / Recurrence', kind: 'select',
          options: revenueTimingOptions, required: true, defaultValue: 'continuous', span: 2,
          help: 'How this stream recurs. One-time = a single month. Monthly/Annual recurring repeat each month/year. Contract/project spreads a cohort over a fixed duration. Seasonal uses per-month seasonality multipliers. Custom = edit month-by-month in the projection grid. “Continuous monthly” keeps the legacy behaviour.',
        },
        {
          name: 'revenue_start_date', label: 'Revenue Start Date', kind: 'date',
          // Required for every timed mode unless the product already provides a
          // launch date to fall back to. Custom is grid-driven and exempt.
          requiredWhen: (v) => v.revenue_timing !== 'custom' && !product.launch_date,
          // One-time revenue happens on a fixed date, so the field is a
          // "Revenue Date" rather than a start of an ongoing stream.
          labelWhen: (v) => (v.revenue_timing === 'one_time' ? 'Revenue Date' : 'Revenue Start Date'),
          helpWhen: (v) => {
            if (v.revenue_timing === 'one_time') return 'The revenue will be recognized once in this date/month.'
            if (v.revenue_timing === 'contract_period') return 'Revenue begins from this date and spreads across the contract duration below.'
            const base = 'Revenue begins from this date and continues according to the selected timing until the end date, if provided.'
            return product.launch_date ? base : `Required: this product has no launch date. ${base}`
          },
        },
        {
          // Manual end date for every mode EXCEPT contract/project, where the
          // end is derived from Start + Duration (single source of truth).
          name: 'revenue_end_date', label: 'Revenue End Date', kind: 'date',
          visibleWhen: (v) =>
            v.revenue_timing !== 'one_time' && v.revenue_timing !== 'custom' && v.revenue_timing !== 'contract_period',
          validateWith: (v, vals) =>
            vals.revenue_timing !== 'contract_period' && v && vals.revenue_start_date
              && String(v) < String(vals.revenue_start_date)
              ? 'End date cannot be before the start date.'
              : undefined,
          help: 'Revenue stops after this month. Leave blank to run to the end of the projection.',
        },
        {
          name: 'contract_duration_months', label: 'Contract Duration', kind: 'number', unit: 'months', min: 1,
          visibleWhen: (v) => v.revenue_timing === 'contract_period',
          requiredWhen: (v) => v.revenue_timing === 'contract_period',
          help: 'Contract duration determines how many months the contract value is spread across. The end date is calculated automatically.',
        },
        {
          // Read-only derived end date for contract/project revenue.
          name: 'revenue_end_date_calc', label: 'Revenue End Date (calculated)', kind: 'computed',
          visibleWhen: (v) => v.revenue_timing === 'contract_period',
          compute: (v) => contractEndDate(v.revenue_start_date, v.contract_duration_months),
          help: 'Automatically calculated from Revenue Start Date + Contract Duration.',
        },
        {
          name: 'recognition_method', label: 'Recognition Method', kind: 'select',
          options: recognitionMethodOptions, defaultValue: 'spread',
          visibleWhen: (v) => v.revenue_timing === 'annual_recurring' || v.revenue_timing === 'contract_period',
          help: 'Spread = distribute evenly across the period’s months (accrual). Lump = recognise the whole amount in a single month (cash timing).',
        },
      ],
    },
    {
      title: 'Volume & Growth',
      subtitle: `How sales quantity starts and scales over time. Quantities are in ${unit} — Revenue = quantity × selling price per ${unit}.`,
      icon: '◴',
      fields: [
        {
          name: 'starting_monthly_volume', label: 'First-month sales quantity', kind: 'number', required: true, unit,
          help: `${VOLUME_HELP[t] ?? VOLUME_HELP.other} Interpreted per the Revenue Timing above (one-time total, recurring monthly quantity, per-year quantity for annual, or contract cohort size). This is the master quantity that drives revenue.`,
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
          help: 'Apply month-by-month multipliers so revenue reflects seasonal peaks and troughs. Selecting “Seasonal” as the Revenue Timing also applies these multipliers.',
          hint: 'Per-month multipliers can be tuned in the revenue projection grid.',
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
            <Tile label="Timing" value={labelFor(revenueTimingOptions, a.revenue_timing ?? 'continuous')} />
            <Tile label="Start Volume / mo" value={`${formatNumber(a.starting_monthly_volume)} ${sellingUnitLabel(product.selling_unit, product.unit_of_sale)}`} />
            <Tile label="Annual Growth" value={formatPercent(a.annual_growth_rate)} />
            <Tile label="Payment Terms" value={labelFor(paymentTermsOptions, a.payment_terms)} />
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
