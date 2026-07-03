"""Sample seed project so the app is non-empty on first run."""
from __future__ import annotations

from datetime import date

from ..models import (
    BusinessPlanProject,
    DirectCostItem,
    EquityFunding,
    Financing,
    FixedAsset,
    KPIAssumption,
    LoanFunding,
    OperatingExpense,
    ProductService,
    ProjectSetup,
    RevenueAssumption,
    RevenueStream,
    ScenarioAssumption,
    StaffRole,
    StartupCost,
    TaxAssumption,
    WorkingCapitalAssumption,
)
from ..models.enums import (
    BillingFrequency,
    BusinessModel,
    CostAllocationMethod,
    CostBehavior,
    CostCalculationMethod,
    DirectCostCategory,
    Department,
    DepreciationMethod,
    ExpenseCategory,
    ExpenseFrequency,
    FinancingSource,
    FixedAssetCategory,
    PaymentTerms,
    ProjectionFrequency,
    ProjectionPeriod,
    ReportingStandard,
    RepaymentType,
    RevenueStreamType,
    RevenueType,
    ScenarioType,
    StartupCostCategory,
)
from ..storage.base import StorageBackend


def build_seed_project() -> BusinessPlanProject:
    saas = ProductService(
        name="Pro Subscription",
        category="SaaS",
        description="Monthly subscription to the core platform.",
        revenue_type=RevenueType.SUBSCRIPTION,
        selling_price=49.0,
        unit_of_sale="seat / month",
        launch_date=date(2026, 1, 1),
    )
    onboarding = ProductService(
        name="Onboarding Service",
        category="Professional Services",
        description="One-off implementation and onboarding package.",
        revenue_type=RevenueType.PROJECT_BASED,
        selling_price=2500.0,
        unit_of_sale="project",
        launch_date=date(2026, 1, 1),
    )

    revenue = [
        RevenueAssumption(
            product_id=saas.id,
            starting_monthly_volume=120,
            annual_growth_rate=60,
            number_of_customers=120,
            customer_growth_rate=8,
            subscription_price=49,
            churn_rate=4,
            payment_terms=PaymentTerms.CASH,
        ),
        RevenueAssumption(
            product_id=onboarding.id,
            starting_monthly_volume=8,
            annual_growth_rate=30,
            contract_value=2500,
            number_of_contracts=8,
            payment_terms=PaymentTerms.NET_30,
        ),
    ]

    # Revenue Streams are now the primary revenue workflow (the wizard). These
    # mirror the two offerings above so the demo's revenue is driven by streams;
    # the products/RevenueAssumptions are kept for backward compatibility and so
    # the direct costs below (per-customer, per-contract, % of revenue) still
    # resolve. The income statement uses streams when present (no double count).
    pro_sub_stream = RevenueStream(
        name="Pro Subscription",
        stream_type=RevenueStreamType.RECURRING_CHARGES,
        initial_customers=120,
        signups_constant=10,
        recurring_charge=49,
        billing_frequency=BillingFrequency.MONTHLY,
        churn_rate_percent=4,
    )
    onboarding_stream = RevenueStream(
        name="Onboarding Service",
        stream_type=RevenueStreamType.UNIT_SALES,
        quantity_constant=8,
        price_constant=2500,
    )
    revenue_streams = [pro_sub_stream, onboarding_stream]

    # Direct costs link to the revenue STREAMS (the primary workflow): the
    # per-customer hosting cost uses the subscription's active-customer forecast,
    # the per-contract labor uses the onboarding stream's unit quantity, and the
    # gateway fee is a % of all stream revenue.
    direct_costs = [
        DirectCostItem(
            name="Cloud Hosting & API",
            category=DirectCostCategory.HOSTING,
            product_ids=[pro_sub_stream.id],
            cost_behavior=CostBehavior.VARIABLE,
            calculation_method=CostCalculationMethod.PER_CUSTOMER,
            amount=3.5,
            supplier_name="CloudCo",
            cost_inflation_rate=3,
            start_date=date(2026, 1, 1),
        ),
        DirectCostItem(
            name="Payment Gateway Fee",
            category=DirectCostCategory.PAYMENT_GATEWAY,
            apply_to_all=True,
            cost_behavior=CostBehavior.VARIABLE,
            calculation_method=CostCalculationMethod.PERCENT_OF_REVENUE,
            percent=2.9,
            allocation_method=CostAllocationMethod.REVENUE_SHARE,
            start_date=date(2026, 1, 1),
        ),
        DirectCostItem(
            name="Onboarding Direct Labor",
            category=DirectCostCategory.DIRECT_LABOR,
            product_ids=[onboarding_stream.id],
            cost_behavior=CostBehavior.VARIABLE,
            calculation_method=CostCalculationMethod.PER_CONTRACT,
            amount=600,
            cost_inflation_rate=3,
            start_date=date(2026, 1, 1),
        ),
    ]

    staffing = [
        StaffRole(
            department=Department.MANAGEMENT,
            job_title="CEO / Founder",
            number_of_employees=1,
            monthly_salary=8000,
            hiring_start_date=date(2026, 1, 1),
            employer_social_security_percent=11,
        ),
        StaffRole(
            department=Department.TECHNOLOGY,
            job_title="Software Engineer",
            number_of_employees=3,
            monthly_salary=6000,
            hiring_start_date=date(2026, 1, 1),
            annual_increase_percent=5,
            benefits_percent=10,
            employer_social_security_percent=11,
        ),
        StaffRole(
            department=Department.SALES,
            job_title="Account Executive",
            number_of_employees=2,
            monthly_salary=4500,
            hiring_start_date=date(2026, 3, 1),
            sales_commission_percent=8,
            employer_social_security_percent=11,
        ),
    ]

    operating_expenses = [
        OperatingExpense(name="Office Rent", category=ExpenseCategory.RENT, amount=4500,
                         frequency=ExpenseFrequency.MONTHLY, inflation_percent=4, is_fixed=True),
        OperatingExpense(name="Cloud & Software", category=ExpenseCategory.SOFTWARE, amount=1200,
                         frequency=ExpenseFrequency.MONTHLY, is_fixed=False),
        OperatingExpense(name="Marketing", category=ExpenseCategory.MARKETING, amount=6000,
                         frequency=ExpenseFrequency.MONTHLY, is_fixed=False),
        OperatingExpense(name="Annual Audit", category=ExpenseCategory.ACCOUNTING, amount=9000,
                         frequency=ExpenseFrequency.YEARLY, is_fixed=True),
    ]

    startup_costs = [
        StartupCost(name="Company Registration", category=StartupCostCategory.REGISTRATION,
                    amount=3500, payment_date=date(2025, 12, 1)),
        StartupCost(name="Brand & Website", category=StartupCostCategory.BRANDING,
                    amount=12000, payment_date=date(2025, 12, 15), capitalized=True),
        StartupCost(name="Initial Marketing Launch", category=StartupCostCategory.INITIAL_MARKETING,
                    amount=15000, payment_date=date(2026, 1, 1)),
    ]

    fixed_assets = [
        FixedAsset(name="Laptops & Workstations", category=FixedAssetCategory.COMPUTERS,
                   purchase_amount=24000, purchase_date=date(2026, 1, 1), useful_life_years=4,
                   depreciation_method=DepreciationMethod.STRAIGHT_LINE,
                   financing_source=FinancingSource.CASH),
        FixedAsset(name="Office Fit-out", category=FixedAssetCategory.LEASEHOLD,
                   purchase_amount=40000, purchase_date=date(2026, 1, 1), useful_life_years=7,
                   depreciation_method=DepreciationMethod.STRAIGHT_LINE,
                   financing_source=FinancingSource.LOAN),
    ]

    financing = Financing(
        equity=EquityFunding(founder_capital=100000, investor_equity=500000,
                             investment_date=date(2026, 1, 1), shareholding_percent=25,
                             investor_name="Seed Ventures", use_of_funds="Product & GTM"),
        loans=[
            LoanFunding(name="SME Growth Loan", lender="First Bank", amount=150000,
                        drawdown_date=date(2026, 1, 15), interest_rate=8.5,
                        repayment_period_months=48, grace_period_months=6,
                        repayment_type=RepaymentType.EQUAL_INSTALLMENTS, arrangement_fee=1500),
        ],
    )

    scenarios = [
        ScenarioAssumption(scenario_type=ScenarioType.BASE, label="Base Case"),
        ScenarioAssumption(scenario_type=ScenarioType.CONSERVATIVE, label="Conservative",
                           sales_volume_adjustment=-20, selling_price_adjustment=-5,
                           direct_cost_adjustment=8, marketing_adjustment=-10),
        ScenarioAssumption(scenario_type=ScenarioType.OPTIMISTIC, label="Optimistic",
                           sales_volume_adjustment=25, customer_growth_adjustment=15,
                           selling_price_adjustment=5),
    ]

    project = BusinessPlanProject(
        name="Acme SaaS — Demo Plan",
        setup=ProjectSetup(
            business_name="Acme Technologies",
            project_name="Acme SaaS Launch Plan",
            business_description="A B2B SaaS platform for SME financial planning.",
            industry="Software / Fintech",
            business_model=BusinessModel.SAAS,
            country="United Arab Emirates",
            city="Dubai",
            currency="AED",
            projection_start_date=date(2026, 1, 1),
            projection_period=ProjectionPeriod.FIVE_YEARS,
            projection_frequency=ProjectionFrequency.MONTHLY,
            tax_jurisdiction="UAE",
            reporting_standard=ReportingStandard.INVESTOR,
            scenario_mode_enabled=True,
        ),
        products=[saas, onboarding],
        revenue=revenue,
        revenue_streams=revenue_streams,
        direct_costs=direct_costs,
        staffing=staffing,
        operating_expenses=operating_expenses,
        startup_costs=startup_costs,
        fixed_assets=fixed_assets,
        working_capital=WorkingCapitalAssumption(
            accounts_receivable_days=30, percent_sales_on_credit=40,
            accounts_payable_days=45, inventory_days=0, minimum_cash_balance=50000,
        ),
        financing=financing,
        tax=TaxAssumption(corporate_tax_rate=9, vat_rate=5, vat_registration_threshold=375000,
                          employer_social_security_rate=12.5, employee_social_security_rate=5),
        scenarios=scenarios,
        kpis=KPIAssumption(
            target_gross_margin_percent=80, target_ebitda_margin_percent=20,
            target_net_profit_margin_percent=15, break_even_target_date=date(2027, 6, 1),
            min_monthly_revenue_target=120000, cac_target=350, ltv_target=4200,
            roi_target_percent=35,
        ),
    )
    return project


def seed_if_empty(storage: StorageBackend) -> None:
    if storage.list_projects():
        return
    storage.save_project(build_seed_project())
