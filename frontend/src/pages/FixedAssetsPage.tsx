import { CollectionPage } from '@/components/pages/CollectionPage'
import type { Column } from '@/components/DataTable'
import type { FormConfig } from '@/components/form/types'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import type { FixedAsset } from '@/types'
import { formatCurrency, formatDate } from '@/utils/format'
import {
  depreciationMethodOptions,
  financingSourceOptions,
  fixedAssetCategoryOptions,
  labelFor,
} from '@/utils/options'
import { useProjectContext } from '@/layouts/ProjectContext'

const config: FormConfig = [
  {
    title: 'Asset',
    fields: [
      { name: 'name', label: 'Asset Name', kind: 'text', required: true, span: 2, placeholder: 'e.g. Delivery Van' },
      { name: 'category', label: 'Asset Category', kind: 'select', options: fixedAssetCategoryOptions, required: true },
      { name: 'active', label: 'Active', kind: 'switch' },
      { name: 'description', label: 'Description', kind: 'textarea', span: 2 },
    ],
  },
  {
    title: 'Acquisition & Financing',
    icon: '◰',
    fields: [
      { name: 'purchase_amount', label: 'Purchase Amount', kind: 'currency', required: true },
      { name: 'purchase_date', label: 'Purchase Date', kind: 'date', required: true },
      { name: 'ready_for_use_date', label: 'Ready-for-use Date', kind: 'date', help: 'Depreciation starts from this date (else purchase date).' },
      { name: 'financing_source', label: 'Financing Source', kind: 'select', options: financingSourceOptions, help: 'Classification only. Actual loan / equity / grant amounts are entered on the Financing page — selecting a source here does not create funding and is not double-counted.' },
      { name: 'supplier_name', label: 'Supplier / Vendor', kind: 'text' },
      { name: 'capitalized', label: 'Capitalized', kind: 'switch', help: 'Capitalised assets are depreciated over their life.' },
      { name: 'vat_applicable', label: 'This item is VAT-applicable', kind: 'switch', help: 'Marks whether this asset is subject to VAT at the project default rate (set on the Tax page). It does not set the rate.' },
    ],
  },
  {
    title: 'Depreciation',
    subtitle: 'How the asset loses value over its useful life.',
    icon: '◱',
    fields: [
      {
        name: 'depreciation_method', label: 'Depreciation Method', kind: 'select', options: depreciationMethodOptions,
        help: 'Straight-line spreads cost evenly; reducing balance front-loads it.',
      },
      { name: 'useful_life_years', label: 'Useful Life (years)', kind: 'number', help: 'Years the asset is expected to be in service.' },
      { name: 'residual_value', label: 'Residual Value', kind: 'currency', help: 'Expected value at the end of useful life (cannot exceed purchase amount).' },
    ],
  },
  {
    title: 'Maintenance & Replacement',
    advanced: true,
    fields: [
      { name: 'replacement_cycle_years', label: 'Replacement Cycle (years)', kind: 'number' },
      { name: 'maintenance_cost_percent', label: 'Annual Maintenance %', kind: 'percent', help: 'Annual maintenance as a % of purchase cost.' },
      { name: 'notes', label: 'Notes', kind: 'textarea', span: 2 },
    ],
  },
]

function annualDepreciation(a: FixedAsset): number {
  if (a.depreciation_method === 'none' || a.useful_life_years <= 0) return 0
  return (a.purchase_amount - a.residual_value) / a.useful_life_years
}

export function FixedAssetsPage({ embedded }: { embedded?: boolean } = {}) {
  const { currency } = useProjectContext()

  const columns: Column<FixedAsset>[] = [
    { header: 'Asset', cell: (r) => <strong>{r.name}</strong> },
    { header: 'Category', cell: (r) => labelFor(fixedAssetCategoryOptions, r.category) },
    { header: 'Purchase', cell: (r) => formatDate(r.purchase_date) },
    { header: 'Cost', align: 'right', cell: (r) => formatCurrency(r.purchase_amount, currency) },
    { header: 'Life', align: 'right', cell: (r) => `${r.useful_life_years} yr` },
    { header: 'Method', cell: (r) => <Badge tone="neutral">{labelFor(depreciationMethodOptions, r.depreciation_method)}</Badge> },
    { header: 'Depr. / yr', align: 'right', cell: (r) => formatCurrency(annualDepreciation(r), currency) },
    { header: 'Funding', cell: (r) => labelFor(financingSourceOptions, r.financing_source) },
    { header: 'Status', cell: (r) => <ActiveBadge active={r.active} /> },
  ]

  return (
    <CollectionPage<FixedAsset>
      slug="fixed-assets"
      sectionKey="fixed-assets"
      itemNoun="Asset"
      config={config}
      columns={columns}
      modalWide
      embedded={embedded}
      emptyIcon="◱"
      emptyDescription="Register long-term assets and their depreciation assumptions — they feed depreciation, the balance sheet, and cash-flow capital expenditure."
    />
  )
}
