"""Enumerations used across the financial assumption models.

Using string enums keeps the JSON store human-readable and gives the
frontend stable, typed option values for select inputs.
"""
from __future__ import annotations

from enum import Enum


class ProjectionPeriod(str, Enum):
    THREE_YEARS = "3_years"
    FIVE_YEARS = "5_years"
    TEN_YEARS = "10_years"

    @property
    def years(self) -> int:
        return {"3_years": 3, "5_years": 5, "10_years": 10}[self.value]


class ProjectionFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportingStandard(str, Enum):
    MANAGEMENT = "management"
    IFRS = "ifrs"
    BANK = "bank"
    INVESTOR = "investor"


class BusinessModel(str, Enum):
    B2B = "b2b"
    B2C = "b2c"
    B2B2C = "b2b2c"
    MARKETPLACE = "marketplace"
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    SERVICES = "services"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


class RevenueType(str, Enum):
    UNIT_SALES = "unit_sales"
    SUBSCRIPTION = "subscription"
    SERVICE_CONTRACT = "service_contract"
    PROJECT_BASED = "project_based"
    COMMISSION = "commission"
    LICENSING = "licensing"
    OTHER = "other"


class PaymentTerms(str, Enum):
    CASH = "cash"
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    NET_90 = "net_90"
    CUSTOM = "custom"

    @property
    def days(self) -> int | None:
        return {
            "cash": 0,
            "net_15": 15,
            "net_30": 30,
            "net_45": 45,
            "net_60": 60,
            "net_90": 90,
            "custom": None,
        }[self.value]


class SellingUnit(str, Enum):
    """Unit of measure a product/service is priced and sold in.

    "Unit Sales" is not limited to discrete pieces — a manufacturer may sell by
    weight (Kg, Metric Ton), volume (Litre), packaging (Bottle, Carton), area,
    time, etc. The selling price is always "price per selected selling unit" and
    revenue stays quantity x price-per-unit.
    """

    UNIT = "unit"
    KG = "kg"
    GRAM = "gram"
    METRIC_TON = "metric_ton"
    LITRE = "litre"
    MILLILITRE = "millilitre"
    BOTTLE = "bottle"
    BOX = "box"
    CARTON = "carton"
    BAG = "bag"
    SQUARE_METER = "square_meter"
    CUBIC_METER = "cubic_meter"
    HOUR = "hour"
    DAY = "day"
    CONTRACT = "contract"
    LICENSE = "license"
    SUBSCRIPTION = "subscription"
    CUSTOM = "custom"


class RevenueTiming(str, Enum):
    """How a revenue stream recurs over the projection horizon.

    CONTINUOUS is the legacy behaviour (a monthly series from launch, shaped by
    growth/seasonality) and is the default so existing projects are unchanged.
    """

    CONTINUOUS = "continuous"          # legacy: monthly series w/ growth & seasonality
    ONE_TIME = "one_time"              # a single month only
    MONTHLY_RECURRING = "monthly_recurring"
    ANNUAL_RECURRING = "annual_recurring"
    CONTRACT_PERIOD = "contract_period"  # spread a cohort over contract_duration_months
    SEASONAL = "seasonal"             # shaped by per-month seasonality multipliers
    CUSTOM = "custom"                 # custom month-by-month schedule (projection grid)


class RecognitionMethod(str, Enum):
    """Whether a periodic amount is smoothed across months or lands in one month."""

    SPREAD = "spread"   # distributed evenly across the months of the period (accrual)
    LUMP = "lump"       # recognised in the payment/anniversary month (cash timing)


class RevenueStreamType(str, Enum):
    """Forecast types for the Add Revenue Stream wizard."""

    UNIT_SALES = "unit_sales"            # revenue = units x unit_price
    BILLABLE_HOURS = "billable_hours"    # revenue = hours x hourly_rate
    RECURRING_CHARGES = "recurring_charges"  # signups + churn + recurring charge (+ upfront)
    REVENUE_ONLY = "revenue_only"        # total revenue entered directly


class ForecastInputMethod(str, Enum):
    """How a wizard input varies over the forecast."""

    CONSTANT = "constant"   # one value applied to every period
    VARYING = "varying"     # an explicit value per month


class BillingFrequency(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RefundBasis(str, Enum):
    PERCENT_OF_REVENUE = "percent_of_revenue"
    PERCENT_OF_UNITS = "percent_of_units"


class Department(str, Enum):
    MANAGEMENT = "management"
    SALES = "sales"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    FINANCE = "finance"
    ADMINISTRATION = "administration"
    TECHNOLOGY = "technology"
    PRODUCTION = "production"
    CUSTOMER_SUPPORT = "customer_support"
    OTHER = "other"


class ExpenseCategory(str, Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    INTERNET = "internet"
    SOFTWARE = "software"
    MARKETING = "marketing"
    ADVERTISING = "advertising"
    LEGAL = "legal"
    ACCOUNTING = "accounting"
    INSURANCE = "insurance"
    TRAVEL = "travel"
    MAINTENANCE = "maintenance"
    OFFICE_SUPPLIES = "office_supplies"
    BANK_CHARGES = "bank_charges"
    PROFESSIONAL_FEES = "professional_fees"
    LICENSES = "licenses"
    TRAINING = "training"
    MISCELLANEOUS = "miscellaneous"
    OTHER = "other"


class ExpenseFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class StartupCostCategory(str, Enum):
    REGISTRATION = "registration"
    TRADE_LICENSE = "trade_license"
    LEGAL_SETUP = "legal_setup"
    BRANDING = "branding"
    WEBSITE = "website"
    SOFTWARE_DEV = "software_development"
    INITIAL_MARKETING = "initial_marketing"
    RECRUITMENT = "recruitment"
    OFFICE_DEPOSIT = "office_deposit"
    RENT_ADVANCE = "rent_advance"
    INITIAL_INVENTORY = "initial_inventory"
    RAW_MATERIALS = "raw_materials"
    EQUIPMENT = "equipment"
    CONSULTANCY = "consultancy"
    PERMITS = "permits"
    OTHER = "other"


class FixedAssetCategory(str, Enum):
    MACHINERY = "machinery"
    EQUIPMENT = "equipment"
    VEHICLE = "vehicle"
    FURNITURE = "furniture"
    COMPUTERS = "computers"
    SOFTWARE_DEV = "software_development"
    LEASEHOLD = "leasehold_improvements"
    LAB_EQUIPMENT = "lab_equipment"
    PRODUCTION_LINE = "production_line"
    TOOLS = "tools"
    OFFICE_FIT_OUT = "office_fit_out"
    WAREHOUSE_EQUIPMENT = "warehouse_equipment"
    OTHER = "other"


class DepreciationMethod(str, Enum):
    STRAIGHT_LINE = "straight_line"
    REDUCING_BALANCE = "reducing_balance"
    NONE = "none"


class FinancingSource(str, Enum):
    CASH = "cash"
    LOAN = "loan"
    LEASE = "lease"
    FOUNDER_CAPITAL = "founder_capital"
    INVESTOR = "investor_funded"
    GRANT_FUNDED = "grant_funded"


class RepaymentType(str, Enum):
    EQUAL_INSTALLMENTS = "equal_installments"
    INTEREST_ONLY = "interest_only_then_principal"
    BULLET = "bullet"
    CUSTOM = "custom"


class StockPurchaseCycle(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TaxFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ScenarioType(str, Enum):
    BASE = "base"
    CONSERVATIVE = "conservative"
    OPTIMISTIC = "optimistic"
    CUSTOM = "custom"


# --------------------------------------------------------------------------
# Page 4 — flexible direct-cost item builder
# --------------------------------------------------------------------------
class DirectCostCategory(str, Enum):
    RAW_MATERIALS = "raw_materials"
    PURCHASED_GOODS = "purchased_goods"
    MANUFACTURING = "manufacturing"
    PACKAGING = "packaging"
    DELIVERY = "delivery"
    PAYMENT_GATEWAY = "payment_gateway"
    SALES_COMMISSION = "sales_commission"
    DIRECT_LABOR = "direct_labor"
    HOSTING = "hosting"
    WASTE_DEFECT = "waste_defect"
    SUBCONTRACTOR = "subcontractor"
    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    WARRANTY = "warranty"
    CUSTOMS = "customs"
    OTHER = "other"


class CostBehavior(str, Enum):
    VARIABLE = "variable"
    SEMI_VARIABLE = "semi_variable"
    DIRECT_FIXED = "direct_fixed"


class CostCalculationMethod(str, Enum):
    FIXED_PER_UNIT = "fixed_per_unit"
    PERCENT_OF_REVENUE = "percent_of_revenue"
    PERCENT_OF_SELLING_PRICE = "percent_of_selling_price"
    PER_CUSTOMER = "per_customer"
    PER_ORDER = "per_order"
    PER_CONTRACT = "per_contract"
    PER_SERVICE_DELIVERY = "per_service_delivery"
    PERCENT_OF_PURCHASE_COST = "percent_of_purchase_cost"
    MONTHLY_ALLOCATED = "monthly_allocated"
    ANNUAL_ALLOCATED = "annual_allocated"
    ONE_TIME = "one_time"
    MANUAL_BY_PERIOD = "manual_by_period"

    @property
    def uses_percent(self) -> bool:
        """Methods whose primary value is a percentage rather than an amount."""
        return self in {
            CostCalculationMethod.PERCENT_OF_REVENUE,
            CostCalculationMethod.PERCENT_OF_SELLING_PRICE,
            CostCalculationMethod.PERCENT_OF_PURCHASE_COST,
        }

    @property
    def is_per_unit(self) -> bool:
        """Methods that contribute to a per-unit cost for margin estimates."""
        return self in {
            CostCalculationMethod.FIXED_PER_UNIT,
            CostCalculationMethod.PER_CUSTOMER,
            CostCalculationMethod.PER_ORDER,
            CostCalculationMethod.PER_CONTRACT,
            CostCalculationMethod.PER_SERVICE_DELIVERY,
        }


class CostAllocationMethod(str, Enum):
    EQUAL_SPLIT = "equal_split"
    REVENUE_SHARE = "revenue_share"
    SALES_VOLUME = "sales_volume"
    MANUAL = "manual"
