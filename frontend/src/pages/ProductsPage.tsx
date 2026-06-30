import { CollectionPage } from '@/components/pages/CollectionPage'
import type { Column } from '@/components/DataTable'
import type { FormConfig } from '@/components/form/types'
import { SummaryCard } from '@/components/SummaryCard'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import type { ProductService } from '@/types'
import { formatCurrency, formatDate } from '@/utils/format'
import { labelFor, revenueTypeOptions, sellingUnitLabel, sellingUnitOptions } from '@/utils/options'
import { useProjectContext } from '@/layouts/ProjectContext'

const config: FormConfig = [
  {
    title: 'Product / Service',
    fields: [
      { name: 'name', label: 'Name', kind: 'text', required: true, span: 2, placeholder: 'e.g. Pro Subscription' },
      { name: 'category', label: 'Category', kind: 'text', placeholder: 'e.g. SaaS' },
      {
        name: 'revenue_type', label: 'Revenue Type', kind: 'select', options: revenueTypeOptions, required: true,
        help: 'How this offering earns money. Drives which revenue assumptions apply. “Unit Sales” is not limited to pieces — a unit can be Kg, gram, metric ton, litre, bottle, carton, box, m², hour, or any custom selling measure.',
      },
      {
        name: 'selling_unit', label: 'Selling Unit / Unit of Measure', kind: 'select', options: sellingUnitOptions,
        required: true, defaultValue: 'unit',
        help: 'The unit this product is priced and sold in. Manufacturers: choose Kg, Metric Ton, Litre, Bottle, Carton, etc. The Selling Price below is the price per this unit.',
      },
      {
        name: 'unit_of_sale', label: 'Custom Unit Name', kind: 'text', placeholder: 'e.g. pallet, roll, drum',
        visibleWhen: (v) => v.selling_unit === 'custom',
        help: 'Name your custom selling unit. Used only when Selling Unit is “Custom”.',
      },
      {
        name: 'selling_price', label: 'Selling Price (per selling unit)', kind: 'currency', required: true,
        help: 'Price per selected selling unit — e.g. $2 per Kg, $420 per Metric Ton, $6 per Litre, $1 per Bottle.',
      },
      { name: 'launch_date', label: 'Launch Date', kind: 'date' },
      { name: 'active', label: 'Active', kind: 'switch' },
      { name: 'description', label: 'Description', kind: 'textarea', span: 2, placeholder: 'What the product/service includes.' },
      { name: 'notes', label: 'Notes', kind: 'textarea', span: 2 },
    ],
  },
]

export function ProductsPage() {
  const { currency } = useProjectContext()

  const columns: Column<ProductService>[] = [
    { header: 'Name', cell: (r) => <strong>{r.name}</strong> },
    { header: 'Category', cell: (r) => r.category || '—' },
    { header: 'Revenue Type', cell: (r) => <Badge tone="blue">{labelFor(revenueTypeOptions, r.revenue_type)}</Badge> },
    { header: 'Price', align: 'right', cell: (r) => `${formatCurrency(r.selling_price, currency)} / ${sellingUnitLabel(r.selling_unit, r.unit_of_sale)}` },
    { header: 'Unit', cell: (r) => sellingUnitLabel(r.selling_unit, r.unit_of_sale) },
    { header: 'Launch', cell: (r) => formatDate(r.launch_date) },
    { header: 'Status', cell: (r) => <ActiveBadge active={r.active} /> },
  ]

  return (
    <CollectionPage<ProductService>
      slug="products"
      sectionKey="products"
      itemNoun="Product"
      config={config}
      columns={columns}
      emptyIcon="◫"
      emptyDescription="Define each product or service the company sells. These drive every revenue and cost assumption."
      renderSummary={(rows) => {
        const active = rows.filter((r) => r.active).length
        const avgPrice = rows.length ? rows.reduce((s, r) => s + r.selling_price, 0) / rows.length : 0
        return (
          <div className="stat-grid">
            <SummaryCard label="Total Offerings" value={rows.length} accent="blue" />
            <SummaryCard label="Active" value={active} accent="green" />
            <SummaryCard label="Avg. Selling Price" value={formatCurrency(avgPrice, currency)} accent="slate" />
          </div>
        )
      }}
    />
  )
}
