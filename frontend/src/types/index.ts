/* ==========================================================================
   Domain types — mirror the backend Pydantic models (app/models).
   Kept strict; section item types extend EntityBase.
   ========================================================================== */

export interface EntityBase {
  id: string
  created_at: string
  updated_at: string
  notes?: string | null
}

// -- Enums (string unions) --------------------------------------------------
export type ProjectionPeriod = '3_years' | '5_years' | '10_years'
export type ProjectionFrequency = 'monthly' | 'quarterly' | 'yearly'
export type ReportingStandard = 'management' | 'ifrs' | 'bank' | 'investor'
export type BusinessModelType =
  | 'b2b' | 'b2c' | 'b2b2c' | 'marketplace' | 'saas' | 'ecommerce'
  | 'retail' | 'manufacturing' | 'services' | 'subscription' | 'other'
export type RevenueType =
  | 'unit_sales' | 'subscription' | 'service_contract' | 'project_based'
  | 'commission' | 'licensing' | 'other'
export type PaymentTerms =
  | 'cash' | 'net_15' | 'net_30' | 'net_45' | 'net_60' | 'net_90' | 'custom'
export type RefundBasis = 'percent_of_revenue' | 'percent_of_units'
export type SellingUnit =
  | 'unit' | 'kg' | 'gram' | 'metric_ton' | 'litre' | 'millilitre'
  | 'bottle' | 'box' | 'carton' | 'bag' | 'square_meter' | 'cubic_meter'
  | 'hour' | 'day' | 'contract' | 'license' | 'subscription' | 'custom'
export type Department =
  | 'management' | 'sales' | 'marketing' | 'operations' | 'finance'
  | 'administration' | 'technology' | 'production' | 'customer_support' | 'other'
export type ExpenseCategory =
  | 'rent' | 'utilities' | 'internet' | 'software' | 'marketing' | 'advertising'
  | 'legal' | 'accounting' | 'insurance' | 'travel' | 'maintenance'
  | 'office_supplies' | 'bank_charges' | 'professional_fees' | 'licenses'
  | 'training' | 'miscellaneous' | 'other'
export type ExpenseFrequency = 'monthly' | 'quarterly' | 'yearly' | 'one_time'
export type StartupCostCategory =
  | 'registration' | 'trade_license' | 'legal_setup' | 'branding' | 'website'
  | 'software_development' | 'initial_marketing' | 'recruitment'
  | 'office_deposit' | 'rent_advance' | 'initial_inventory' | 'raw_materials'
  | 'equipment' | 'consultancy' | 'permits' | 'other'
export type FixedAssetCategory =
  | 'machinery' | 'equipment' | 'vehicle' | 'furniture' | 'computers'
  | 'software_development' | 'leasehold_improvements' | 'lab_equipment'
  | 'production_line' | 'tools' | 'office_fit_out' | 'warehouse_equipment' | 'other'
export type DepreciationMethod = 'straight_line' | 'reducing_balance' | 'none'
export type FinancingSource =
  | 'cash' | 'loan' | 'lease' | 'founder_capital' | 'investor_funded' | 'grant_funded'
export type RepaymentType =
  | 'equal_installments' | 'interest_only_then_principal' | 'bullet' | 'custom'
export type StockPurchaseCycle = 'weekly' | 'monthly' | 'quarterly' | 'yearly'
export type TaxFrequency = 'monthly' | 'quarterly' | 'yearly'
export type ScenarioType = 'base' | 'conservative' | 'optimistic'

// -- Section models ---------------------------------------------------------
export interface ProjectSetup extends EntityBase {
  business_name: string
  project_name?: string | null
  business_description?: string | null
  industry?: string | null
  business_model?: BusinessModelType | null
  country?: string | null
  city?: string | null
  currency: string
  projection_start_date: string
  projection_period: ProjectionPeriod
  projection_frequency: ProjectionFrequency
  tax_jurisdiction?: string | null
  reporting_standard: ReportingStandard
  scenario_mode_enabled: boolean
}

export interface ProductService extends EntityBase {
  name: string
  category?: string | null
  description?: string | null
  revenue_type: RevenueType
  /** Price per selected selling unit (e.g. $2 per Kg). */
  selling_price: number
  /** Structured unit of measure; defaults to 'unit' for legacy data. */
  selling_unit?: SellingUnit | null
  /** Free-text descriptor / custom unit label when selling_unit = 'custom'. */
  unit_of_sale?: string | null
  launch_date?: string | null
  active: boolean
}

export interface SeasonalityMonth extends EntityBase {
  month: number
  adjustment_percent: number
}

export type RevenueTiming =
  | 'continuous' | 'one_time' | 'monthly_recurring' | 'annual_recurring'
  | 'contract_period' | 'seasonal' | 'custom'
export type RecognitionMethod = 'spread' | 'lump'

export interface RevenueAssumption extends EntityBase {
  product_id: string
  /** Timing/recurrence; 'continuous' = legacy behaviour (default). */
  revenue_timing?: RevenueTiming | null
  revenue_start_date?: string | null
  revenue_end_date?: string | null
  contract_duration_months?: number | null
  recognition_method?: RecognitionMethod | null
  starting_monthly_volume: number
  annual_growth_rate: number
  monthly_growth_rate?: number | null
  number_of_customers?: number | null
  customer_growth_rate?: number | null
  average_order_value?: number | null
  purchase_frequency?: number | null
  repeat_purchase_rate?: number | null
  subscription_price?: number | null
  churn_rate?: number | null
  contract_value?: number | null
  number_of_contracts?: number | null
  commission_rate?: number | null
  licensing_fee?: number | null
  discount_percent: number
  refund_percent: number
  refund_basis: RefundBasis
  seasonality_enabled: boolean
  seasonality: SeasonalityMonth[]
  payment_terms: PaymentTerms
  custom_payment_days?: number | null
}

export type DirectCostCategory =
  | 'raw_materials' | 'purchased_goods' | 'manufacturing' | 'packaging'
  | 'delivery' | 'payment_gateway' | 'sales_commission' | 'direct_labor'
  | 'hosting' | 'waste_defect' | 'subcontractor' | 'installation'
  | 'maintenance' | 'warranty' | 'customs' | 'other'
export type CostBehavior = 'variable' | 'semi_variable' | 'direct_fixed'
export type CostCalculationMethod =
  | 'fixed_per_unit' | 'percent_of_revenue' | 'percent_of_selling_price'
  | 'per_customer' | 'per_order' | 'per_contract' | 'per_service_delivery'
  | 'percent_of_purchase_cost' | 'monthly_allocated' | 'one_time'
export type CostAllocationMethod = 'equal_split' | 'revenue_share' | 'sales_volume' | 'manual'

export interface CostAllocation {
  product_id: string
  percent: number
}

export interface DirectCostItem extends EntityBase {
  name: string
  category: DirectCostCategory
  apply_to_all: boolean
  product_ids: string[]
  cost_behavior: CostBehavior
  calculation_method: CostCalculationMethod
  amount: number
  percent: number
  allocation_method?: CostAllocationMethod | null
  manual_allocations: CostAllocation[]
  supplier_name?: string | null
  supplier_payment_terms: PaymentTerms
  cost_inflation_rate: number
  waste_defect_rate_percent: number
  minimum_order_quantity?: number | null
  currency_override?: string | null
  vat_applicable: boolean
  /** Optional — blank follows the linked product's launch date. */
  start_date?: string | null
  end_date?: string | null
  active: boolean
}

export interface StaffRole extends EntityBase {
  department: Department
  job_title: string
  number_of_employees: number
  monthly_salary: number
  hiring_start_date?: string | null
  annual_increase_percent: number
  benefits_percent: number
  health_insurance_amount: number
  visa_permit_cost: number
  bonus_amount: number
  bonus_percent: number
  sales_commission_percent: number
  /** Optional role-specific override; null uses the Tax page global default. */
  employer_social_security_percent?: number | null
  gratuity_percent: number
  active: boolean
}

export interface OperatingExpense extends EntityBase {
  name: string
  category: ExpenseCategory
  amount: number
  frequency: ExpenseFrequency
  start_date?: string | null
  end_date?: string | null
  inflation_percent: number
  vat_applicable: boolean
  is_fixed: boolean
}

export interface StartupCost extends EntityBase {
  name: string
  category: StartupCostCategory
  amount: number
  payment_date: string
  capitalized: boolean
}

export interface FixedAsset extends EntityBase {
  name: string
  category: FixedAssetCategory
  description?: string | null
  purchase_amount: number
  purchase_date?: string | null
  ready_for_use_date?: string | null
  useful_life_years: number
  depreciation_method: DepreciationMethod
  residual_value: number
  capitalized: boolean
  replacement_cycle_years?: number | null
  maintenance_cost_percent: number
  financing_source: FinancingSource
  supplier_name?: string | null
  vat_applicable: boolean
  active: boolean
}

export interface WorkingCapitalAssumption extends EntityBase {
  accounts_receivable_days: number
  percent_sales_on_credit: number
  accounts_payable_days: number
  inventory_days: number
  minimum_cash_balance: number
  safety_stock_percent: number
  bad_debt_percent: number
  customer_deposit_percent: number
  supplier_advance_percent: number
  stock_purchase_cycle: StockPurchaseCycle
  collection_warning_threshold_days: number
}

export interface EquityFunding extends EntityBase {
  founder_capital: number
  investor_equity: number
  investment_date?: string | null
  shareholding_percent: number
  investor_name?: string | null
  use_of_funds?: string | null
  dividend_policy_percent: number
}

export interface LoanFunding extends EntityBase {
  name: string
  lender?: string | null
  amount: number
  drawdown_date?: string | null
  interest_rate: number
  repayment_period_months: number
  grace_period_months: number
  repayment_type: RepaymentType
  collateral?: string | null
  arrangement_fee: number
}

export interface GrantFunding extends EntityBase {
  name: string
  amount: number
  expected_date?: string | null
  restrictions?: string | null
}

export interface Financing extends EntityBase {
  equity: EquityFunding
  loans: LoanFunding[]
  grants: GrantFunding[]
}

export interface TaxAssumption extends EntityBase {
  corporate_tax_rate: number
  vat_rate: number
  vat_registration_threshold: number
  customs_duty_rate: number
  municipality_fees: number
  license_renewal_fees: number
  withholding_tax_rate: number
  zakat_rate?: number | null
  employer_social_security_rate: number
  employee_social_security_rate: number
  tax_payment_frequency: TaxFrequency
  vat_payment_frequency: TaxFrequency
  tax_loss_carryforward_enabled: boolean
  corporate_tax_enabled: boolean
  vat_enabled: boolean
}

export interface ScenarioAssumption extends EntityBase {
  scenario_type: ScenarioType
  label?: string | null
  sales_volume_adjustment: number
  selling_price_adjustment: number
  direct_cost_adjustment: number
  salary_adjustment: number
  rent_adjustment: number
  marketing_adjustment: number
  customer_growth_adjustment: number
  collection_days_adjustment: number
  inventory_days_adjustment: number
  interest_rate_adjustment: number
  exchange_rate_adjustment: number
  tax_rate_adjustment: number
  inflation_adjustment: number
}

export interface RevenueMilestone extends EntityBase {
  label: string
  target_date?: string | null
  target_amount: number
  is_profit_milestone: boolean
}

export interface KPIAssumption extends EntityBase {
  target_gross_margin_percent?: number | null
  target_ebitda_margin_percent?: number | null
  target_net_profit_margin_percent?: number | null
  break_even_target_date?: string | null
  min_monthly_revenue_target: number
  min_cash_balance_target: number
  cac_target: number
  ltv_target: number
  payback_period_target_months?: number | null
  roi_target_percent?: number | null
  dscr_target?: number | null
  current_ratio_target?: number | null
  milestones: RevenueMilestone[]
}

// -- Aggregate / meta -------------------------------------------------------
export interface BusinessPlanProject extends EntityBase {
  name: string
  company_id?: string | null
  setup?: ProjectSetup | null
  products: ProductService[]
  revenue: RevenueAssumption[]
  direct_costs: DirectCostItem[]
  staffing: StaffRole[]
  operating_expenses: OperatingExpense[]
  startup_costs: StartupCost[]
  fixed_assets: FixedAsset[]
  working_capital?: WorkingCapitalAssumption | null
  financing: Financing
  tax?: TaxAssumption | null
  scenarios: ScenarioAssumption[]
  kpis?: KPIAssumption | null
}

export interface ProjectSummary {
  id: string
  name: string
  company_id?: string | null
  company_name?: string | null
  project_name?: string | null
  business_name?: string | null
  industry?: string | null
  country?: string | null
  currency?: string | null
  projection_period?: string | null
  completion_percent: number
  products_count?: number
  direct_costs_count?: number
  staff_roles_count?: number
  operating_expenses_count?: number
  fixed_assets_count?: number
  scenarios_count?: number
  total_funding?: number
  created_at: string
  updated_at: string
}

export interface SectionStatus {
  key: string
  label: string
  complete: boolean
  required: boolean
  item_count?: number | null
  missing_fields: string[]
  warnings: string[]
}

export interface CompletionReport {
  project_id: string
  completion_percent: number
  completed_sections: number
  total_sections: number
  sections: SectionStatus[]
}

export interface ReviewStatus {
  project_id: string
  completion: CompletionReport
  ready_for_projection: boolean
  blocking_issues: string[]
  warnings: string[]
}
