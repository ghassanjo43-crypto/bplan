/* Select option lists — labels are the plain-English display values. */
import type {
  BusinessModelType, CostAllocationMethod, CostBehavior, CostCalculationMethod,
  Department, DepreciationMethod, DirectCostCategory, ExpenseCategory,
  ExpenseFrequency, FinancingSource, FixedAssetCategory, PaymentTerms,
  ProjectionFrequency, ProjectionPeriod, RefundBasis, RepaymentType,
  RecognitionMethod, ReportingStandard, RevenueTiming, RevenueType, ScenarioType,
  SellingUnit, StartupCostCategory, StockPurchaseCycle, TaxFrequency,
} from '@/types'

export interface Option<T = string> {
  value: T
  label: string
}

export const projectionPeriodOptions: Option<ProjectionPeriod>[] = [
  { value: '3_years', label: '3 Years' },
  { value: '5_years', label: '5 Years' },
  { value: '10_years', label: '10 Years' },
]

export const projectionFrequencyOptions: Option<ProjectionFrequency>[] = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Yearly' },
]

export const reportingStandardOptions: Option<ReportingStandard>[] = [
  { value: 'management', label: 'Management Accounts' },
  { value: 'ifrs', label: 'IFRS-style' },
  { value: 'bank', label: 'Bank Presentation' },
  { value: 'investor', label: 'Investor Presentation' },
]

export const businessModelOptions: Option<BusinessModelType>[] = [
  { value: 'b2b', label: 'B2B' },
  { value: 'b2c', label: 'B2C' },
  { value: 'b2b2c', label: 'B2B2C' },
  { value: 'marketplace', label: 'Marketplace' },
  { value: 'saas', label: 'SaaS' },
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'retail', label: 'Retail' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'services', label: 'Services' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'other', label: 'Other' },
]

export const revenueTypeOptions: Option<RevenueType>[] = [
  { value: 'unit_sales', label: 'Unit Sales' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'service_contract', label: 'Service Contract' },
  { value: 'project_based', label: 'Project-based' },
  { value: 'commission', label: 'Commission' },
  { value: 'licensing', label: 'Licensing' },
  { value: 'other', label: 'Other' },
]

export const paymentTermsOptions: Option<PaymentTerms>[] = [
  { value: 'cash', label: 'Cash (immediate)' },
  { value: 'net_15', label: '15 days' },
  { value: 'net_30', label: '30 days' },
  { value: 'net_45', label: '45 days' },
  { value: 'net_60', label: '60 days' },
  { value: 'net_90', label: '90 days' },
  { value: 'custom', label: 'Custom' },
]

export const refundBasisOptions: Option<RefundBasis>[] = [
  { value: 'percent_of_revenue', label: '% of Revenue' },
  { value: 'percent_of_units', label: '% of Units' },
]

// How a revenue stream recurs over the projection horizon.
export const revenueTimingOptions: Option<RevenueTiming>[] = [
  { value: 'continuous', label: 'Continuous monthly' },
  { value: 'one_time', label: 'One-time' },
  { value: 'monthly_recurring', label: 'Monthly recurring' },
  { value: 'annual_recurring', label: 'Annual recurring / yearly renewal' },
  { value: 'contract_period', label: 'Contract / project over fixed period' },
  { value: 'seasonal', label: 'Seasonal' },
  { value: 'custom', label: 'Custom month-by-month schedule' },
]

// Whether a periodic amount is smoothed across months or lands in one month.
export const recognitionMethodOptions: Option<RecognitionMethod>[] = [
  { value: 'spread', label: 'Spread / smoothed' },
  { value: 'lump', label: 'Lump / cash timing' },
]

// Unit of measure a product is priced and sold in. "Unit Sales" covers weight,
// volume, packaging, area, time, etc. — not just discrete pieces.
export const sellingUnitOptions: Option<SellingUnit>[] = [
  { value: 'unit', label: 'Piece / Unit' },
  { value: 'kg', label: 'Kg' },
  { value: 'gram', label: 'Gram' },
  { value: 'metric_ton', label: 'Metric Ton' },
  { value: 'litre', label: 'Litre' },
  { value: 'millilitre', label: 'Millilitre' },
  { value: 'bottle', label: 'Bottle' },
  { value: 'box', label: 'Box' },
  { value: 'carton', label: 'Carton' },
  { value: 'bag', label: 'Bag' },
  { value: 'square_meter', label: 'Square meter' },
  { value: 'cubic_meter', label: 'Cubic meter' },
  { value: 'hour', label: 'Hour' },
  { value: 'day', label: 'Day' },
  { value: 'contract', label: 'Contract' },
  { value: 'license', label: 'License' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'custom', label: 'Custom' },
]

/** Resolve the concise selling-unit label (mirrors backend ProductService.unit_label). */
export function sellingUnitLabel(sellingUnit?: SellingUnit | null, unitOfSale?: string | null): string {
  const su = sellingUnit ?? 'unit'
  const legacy = (unitOfSale ?? '').trim()
  if (su === 'custom') return legacy || 'Custom'
  if (su === 'unit') {
    if (legacy && !['unit', 'units', 'piece', 'pieces'].includes(legacy.toLowerCase())) return legacy
    return 'Unit'
  }
  return sellingUnitOptions.find((o) => o.value === su)?.label ?? su
}

export const departmentOptions: Option<Department>[] = [
  { value: 'management', label: 'Management' },
  { value: 'sales', label: 'Sales' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'operations', label: 'Operations' },
  { value: 'finance', label: 'Finance' },
  { value: 'administration', label: 'Administration' },
  { value: 'technology', label: 'Technology' },
  { value: 'production', label: 'Production' },
  { value: 'customer_support', label: 'Customer Support' },
  { value: 'other', label: 'Other' },
]

export const expenseCategoryOptions: Option<ExpenseCategory>[] = [
  { value: 'rent', label: 'Rent' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'internet', label: 'Internet' },
  { value: 'software', label: 'Software Subscriptions' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'advertising', label: 'Advertising' },
  { value: 'legal', label: 'Legal Fees' },
  { value: 'accounting', label: 'Accounting / Audit' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'travel', label: 'Travel' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'office_supplies', label: 'Office Supplies' },
  { value: 'bank_charges', label: 'Bank Charges' },
  { value: 'professional_fees', label: 'Professional Fees' },
  { value: 'licenses', label: 'Licenses' },
  { value: 'training', label: 'Training' },
  { value: 'miscellaneous', label: 'Miscellaneous' },
  { value: 'other', label: 'Other' },
]

export const expenseFrequencyOptions: Option<ExpenseFrequency>[] = [
  { value: 'monthly', label: 'Monthly recurring' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Annual' },
  { value: 'one_time', label: 'One-time' },
]

export const startupCostCategoryOptions: Option<StartupCostCategory>[] = [
  { value: 'registration', label: 'Company Registration' },
  { value: 'trade_license', label: 'Trade License' },
  { value: 'legal_setup', label: 'Legal Setup' },
  { value: 'branding', label: 'Initial Branding' },
  { value: 'website', label: 'Website' },
  { value: 'software_development', label: 'App / Software Development' },
  { value: 'initial_marketing', label: 'Initial Marketing' },
  { value: 'recruitment', label: 'Recruitment' },
  { value: 'office_deposit', label: 'Office Deposit' },
  { value: 'rent_advance', label: 'Rent Advance' },
  { value: 'initial_inventory', label: 'Initial Inventory' },
  { value: 'raw_materials', label: 'Initial Raw Materials' },
  { value: 'equipment', label: 'Initial Equipment' },
  { value: 'consultancy', label: 'Consultancy' },
  { value: 'permits', label: 'Permits' },
  { value: 'other', label: 'Other Startup Costs' },
]

export const fixedAssetCategoryOptions: Option<FixedAssetCategory>[] = [
  { value: 'machinery', label: 'Machinery' },
  { value: 'equipment', label: 'Equipment' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'furniture', label: 'Furniture' },
  { value: 'computers', label: 'Computers' },
  { value: 'software_development', label: 'Software Development' },
  { value: 'leasehold_improvements', label: 'Leasehold Improvements' },
  { value: 'lab_equipment', label: 'Lab Equipment' },
  { value: 'production_line', label: 'Production Line' },
  { value: 'tools', label: 'Tools' },
  { value: 'office_fit_out', label: 'Office Fit-out' },
  { value: 'warehouse_equipment', label: 'Warehouse Equipment' },
  { value: 'other', label: 'Other' },
]

export const depreciationMethodOptions: Option<DepreciationMethod>[] = [
  { value: 'straight_line', label: 'Straight-line' },
  { value: 'reducing_balance', label: 'Reducing Balance' },
  { value: 'none', label: 'None' },
]

export const financingSourceOptions: Option<FinancingSource>[] = [
  { value: 'cash', label: 'Cash' },
  { value: 'loan', label: 'Loan' },
  { value: 'lease', label: 'Lease' },
  { value: 'founder_capital', label: 'Founder Capital' },
  { value: 'investor_funded', label: 'Investor-funded' },
  { value: 'grant_funded', label: 'Grant-funded' },
]

export const repaymentTypeOptions: Option<RepaymentType>[] = [
  { value: 'equal_installments', label: 'Equal Monthly Installments' },
  { value: 'interest_only_then_principal', label: 'Interest-only then Principal' },
  { value: 'bullet', label: 'Bullet Repayment' },
  { value: 'custom', label: 'Custom' },
]

export const stockPurchaseCycleOptions: Option<StockPurchaseCycle>[] = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Yearly' },
]

export const taxFrequencyOptions: Option<TaxFrequency>[] = [
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Yearly' },
]

export const scenarioTypeOptions: Option<ScenarioType>[] = [
  { value: 'base', label: 'Base Case' },
  { value: 'conservative', label: 'Conservative Case' },
  { value: 'optimistic', label: 'Optimistic Case' },
]

export const directCostCategoryOptions: Option<DirectCostCategory>[] = [
  { value: 'raw_materials', label: 'Raw Materials' },
  { value: 'purchased_goods', label: 'Purchased Goods' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'packaging', label: 'Packaging' },
  { value: 'delivery', label: 'Delivery / Logistics' },
  { value: 'payment_gateway', label: 'Payment Gateway' },
  { value: 'sales_commission', label: 'Sales Commission' },
  { value: 'direct_labor', label: 'Direct Labor' },
  { value: 'hosting', label: 'Hosting / API' },
  { value: 'waste_defect', label: 'Waste / Defect' },
  { value: 'subcontractor', label: 'Subcontractor' },
  { value: 'installation', label: 'Installation' },
  { value: 'maintenance', label: 'Maintenance / Service Delivery' },
  { value: 'warranty', label: 'Warranty Cost' },
  { value: 'customs', label: 'Import / Customs' },
  { value: 'other', label: 'Other' },
]

export const costBehaviorOptions: Option<CostBehavior>[] = [
  { value: 'variable', label: 'Variable' },
  { value: 'semi_variable', label: 'Semi-variable' },
  { value: 'direct_fixed', label: 'Direct Fixed' },
]

export const costCalculationMethodOptions: Option<CostCalculationMethod>[] = [
  { value: 'fixed_per_unit', label: 'Cost per selling unit' },
  { value: 'percent_of_revenue', label: 'Percentage of revenue' },
  { value: 'percent_of_selling_price', label: 'Percentage of selling price' },
  { value: 'per_customer', label: 'Amount per customer' },
  { value: 'per_order', label: 'Amount per order' },
  { value: 'per_contract', label: 'Fixed amount per contract' },
  { value: 'per_service_delivery', label: 'Amount per service delivery' },
  { value: 'percent_of_purchase_cost', label: 'Percentage of purchased goods cost' },
  { value: 'monthly_allocated', label: 'Fixed direct cost per month' },
  { value: 'annual_allocated', label: 'Annual allocated direct cost' },
  { value: 'one_time', label: 'One-time direct cost' },
  { value: 'manual_by_period', label: 'Manual by period (month-by-month grid)' },
]

export const costAllocationMethodOptions: Option<CostAllocationMethod>[] = [
  { value: 'equal_split', label: 'Equal split' },
  { value: 'revenue_share', label: 'Based on revenue share' },
  { value: 'sales_volume', label: 'Based on sales volume' },
  { value: 'manual', label: 'Manual percentage allocation' },
]

/** Methods whose primary value is a percentage rather than an amount. */
export const PERCENT_METHODS: CostCalculationMethod[] = [
  'percent_of_revenue',
  'percent_of_selling_price',
  'percent_of_purchase_cost',
]
/** Methods that contribute to a per-unit cost estimate for margin previews. */
export const PER_UNIT_METHODS: CostCalculationMethod[] = [
  'fixed_per_unit', 'per_customer', 'per_order', 'per_contract', 'per_service_delivery',
]

export const currencyOptions: Option[] = [
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'AED', label: 'AED — UAE Dirham' },
  { value: 'SAR', label: 'SAR — Saudi Riyal' },
  { value: 'QAR', label: 'QAR — Qatari Riyal' },
  { value: 'KWD', label: 'KWD — Kuwaiti Dinar' },
  { value: 'BHD', label: 'BHD — Bahraini Dinar' },
  { value: 'OMR', label: 'OMR — Omani Rial' },
  { value: 'EGP', label: 'EGP — Egyptian Pound' },
  { value: 'INR', label: 'INR — Indian Rupee' },
  { value: 'PKR', label: 'PKR — Pakistani Rupee' },
  { value: 'CAD', label: 'CAD — Canadian Dollar' },
  { value: 'AUD', label: 'AUD — Australian Dollar' },
  { value: 'SGD', label: 'SGD — Singapore Dollar' },
  { value: 'JPY', label: 'JPY — Japanese Yen' },
  { value: 'CNY', label: 'CNY — Chinese Yuan' },
]

/** Build a quick value→label lookup for rendering option labels in tables. */
export function labelFor(options: Option<string>[], value?: string | null): string {
  if (!value) return '—'
  return options.find((o) => o.value === value)?.label ?? value
}
