/* Direct-cost helpers: association labels, per-unit estimates, quick-add
   templates, and the gross-margin preview model used by Page 4. */
import type {
  CostBehavior,
  CostCalculationMethod,
  DirectCostCategory,
  DirectCostItem,
  ProductService,
} from '@/types'
import { formatCurrency, formatPercent } from './format'
import { PERCENT_METHODS, PER_UNIT_METHODS } from './options'

export type AssociationMode = 'one' | 'multiple' | 'all' | 'unassigned'

/** Anything a direct cost can associate with — a revenue stream (primary) or,
 *  for legacy projects, a product/service. Only id + display name are needed. */
export interface Associable {
  id: string
  name: string
}

export function usesPercent(method: CostCalculationMethod): boolean {
  return PERCENT_METHODS.includes(method)
}
export function isPerUnit(method: CostCalculationMethod): boolean {
  return PER_UNIT_METHODS.includes(method)
}

export function appliesTo(item: DirectCostItem, productId: string): boolean {
  return item.apply_to_all || item.product_ids.includes(productId)
}

export function isUnassigned(item: DirectCostItem): boolean {
  return !item.apply_to_all && item.product_ids.length === 0
}

export function spansMultiple(item: DirectCostItem): boolean {
  return item.apply_to_all || item.product_ids.length > 1
}

export function deriveMode(item: DirectCostItem): AssociationMode {
  if (item.apply_to_all) return 'all'
  if (item.product_ids.length > 1) return 'multiple'
  if (item.product_ids.length === 1) return 'one'
  return 'unassigned'
}

/** Human-readable label of what a cost item is associated with. */
export function associationLabel(item: DirectCostItem, sources: Associable[]): string {
  if (item.apply_to_all) return 'All revenue streams'
  if (item.product_ids.length === 0) return 'Unassigned'
  const names = item.product_ids
    .map((id) => sources.find((s) => s.id === id)?.name)
    .filter(Boolean) as string[]
  if (names.length === 1) return names[0]
  return `${names.length} revenue streams`
}

/** The "amount / percentage" cell value. */
export function methodValueLabel(item: DirectCostItem, currency: string): string {
  return usesPercent(item.calculation_method)
    ? formatPercent(item.percent)
    : formatCurrency(item.amount, item.currency_override || currency)
}

/** Estimated per-unit direct cost for a product across all applicable items.
 *  Per-unit amounts form the "purchased cost" base; percentage methods are then
 *  charged on either the selling price or that base (% of purchased goods cost). */
export function estimatedUnitCost(product: ProductService, items: DirectCostItem[]): number {
  const applicable = items.filter((i) => i.active && appliesTo(i, product.id))
  const perUnitBase = applicable
    .filter((i) => isPerUnit(i.calculation_method))
    .reduce((s, i) => s + i.amount, 0)

  let total = perUnitBase
  for (const item of applicable) {
    const m = item.calculation_method
    if (m === 'percent_of_revenue' || m === 'percent_of_selling_price') {
      total += (item.percent / 100) * product.selling_price
    } else if (m === 'percent_of_purchase_cost') {
      total += (item.percent / 100) * perUnitBase
    }
  }
  return total
}

export interface MarginRow {
  product: ProductService
  unitCost: number
  margin: number
  marginPct: number
  negative: boolean
}

export function marginByProduct(products: ProductService[], items: DirectCostItem[]): MarginRow[] {
  return products.map((product) => {
    const unitCost = estimatedUnitCost(product, items)
    const margin = product.selling_price - unitCost
    const marginPct = product.selling_price > 0 ? (margin / product.selling_price) * 100 : 0
    return { product, unitCost, margin, marginPct, negative: margin < 0 }
  })
}

// -- Quick-add templates ----------------------------------------------------
export interface CostTemplate {
  key: string
  label: string
  category: DirectCostCategory
  method: CostCalculationMethod
  behavior: CostBehavior
}

export const COST_TEMPLATES: CostTemplate[] = [
  { key: 'raw', label: 'Raw material per unit', category: 'raw_materials', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'purchased', label: 'Purchased product per unit', category: 'purchased_goods', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'mfg', label: 'Manufacturing per unit', category: 'manufacturing', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'pack', label: 'Packaging per unit', category: 'packaging', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'delivery', label: 'Delivery / logistics per unit', category: 'delivery', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'gateway', label: 'Payment gateway %', category: 'payment_gateway', method: 'percent_of_revenue', behavior: 'variable' },
  { key: 'commission', label: 'Sales commission %', category: 'sales_commission', method: 'percent_of_revenue', behavior: 'variable' },
  { key: 'labor', label: 'Direct labor per unit', category: 'direct_labor', method: 'fixed_per_unit', behavior: 'variable' },
  { key: 'hosting', label: 'Hosting / API per customer', category: 'hosting', method: 'per_customer', behavior: 'variable' },
  { key: 'subcontractor', label: 'Subcontractor per contract', category: 'subcontractor', method: 'per_contract', behavior: 'variable' },
  { key: 'waste', label: 'Waste / defect allowance', category: 'waste_defect', method: 'percent_of_revenue', behavior: 'variable' },
  { key: 'warranty', label: 'Warranty provision %', category: 'warranty', method: 'percent_of_revenue', behavior: 'semi_variable' },
  { key: 'install', label: 'Installation per project', category: 'installation', method: 'per_contract', behavior: 'variable' },
  { key: 'custom', label: 'Other custom direct cost', category: 'other', method: 'fixed_per_unit', behavior: 'variable' },
]
