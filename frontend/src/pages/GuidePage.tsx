import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { NAV_GROUPS, NAV_PAGES } from '@/routes/nav'
import { UserMenu } from '@/components/auth/UserMenu'

/**
 * Standalone, top-level user guide / manual for Business Plan Studio.
 *
 * It is intentionally project-independent so it is reachable before a project is
 * selected. The "workflow" section is driven by the same NAV model as the
 * sidebar, so it can never drift out of date. Everything else is a hand-written
 * page-by-page manual, a concepts glossary, common-mistake warnings and worked
 * examples. It reuses the app's existing card / banner / badge / table styles so
 * the layout stays consistent.
 */

// -- small presentational helpers ------------------------------------------
function H2({ id, children }: { id?: string; children: ReactNode }) {
  return <h2 className="guide-h2" id={id} style={{ scrollMarginTop: 24 }}>{children}</h2>
}

function H4({ children }: { children: ReactNode }) {
  return <div style={{ fontWeight: 700, marginTop: 18, marginBottom: 6, fontSize: 14 }}>{children}</div>
}

function Callout({ kind, title, children }: { kind: 'tip' | 'mistake' | 'investor'; title?: string; children: ReactNode }) {
  const map = {
    tip: { cls: 'banner--info', icon: 'ℹ', label: 'Tip' },
    mistake: { cls: 'banner--warning', icon: '⚠', label: 'Common mistake' },
    investor: { cls: 'banner--success', icon: '◑', label: 'Investor note' },
  }[kind]
  return (
    <div className={`banner ${map.cls}`} style={{ marginTop: 12 }}>
      <span className="banner__icon">{map.icon}</span>
      <div><strong>{title ?? map.label}:</strong> {children}</div>
    </div>
  )
}

function Bullets({ items }: { items: ReactNode[] }) {
  return <ul style={{ margin: '6px 0 0 18px', display: 'grid', gap: 4 }}>{items.map((it, i) => <li key={i}>{it}</li>)}</ul>
}

function FieldTable({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <div className="table-wrap" style={{ marginTop: 6 }}>
      <table className="table">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td style={{ width: '32%', verticalAlign: 'top' }}><strong>{k}</strong></td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// -- page-by-page data ------------------------------------------------------
interface PageGuide {
  id: string
  icon: string
  title: string
  purpose: ReactNode
  fields: [string, ReactNode][]
  model: ReactNode
  example: ReactNode
  mistakes: ReactNode[]
  tip?: ReactNode
  investor?: ReactNode
}

const PAGE_GUIDES: PageGuide[] = [
  {
    id: 'pg-setup', icon: '◧', title: 'Project Setup',
    purpose: 'Defines the identity of the plan and the shape of the whole projection — currency, when it starts, how long it runs, and the time granularity. Every other page builds on these settings.',
    fields: [
      ['Business / Company name', 'The legal or trading name of the entity the plan is for. Appears on reports.'],
      ['Project name', 'The title of this specific study or scenario (e.g. “2026 Expansion Plan”).'],
      ['Reporting currency', 'Chosen once and used everywhere — prices, costs, statements and reports.'],
      ['Projection start date', 'Month 1 of the model. All timing (launch dates, loans, depreciation) is measured from here.'],
      ['Projection period', 'How many years the model forecasts — 3, 5 or 10 years.'],
      ['Projection frequency', 'Monthly gives the most detail; quarterly/annual roll the same model up.'],
      ['Reporting standard', 'Tailors how statements are presented for the intended audience (management, IFRS, bank, investor).'],
    ],
    model: 'These settings frame the entire time series. Change the start date and every dated assumption shifts; change the period and the model lengthens or shortens. Currency formats every figure in every statement and export.',
    example: 'A UAE manufacturer sets currency = AED, start = 1 Jan 2026, period = 5 years, frequency = Monthly.',
    mistakes: [
      'Setting a start date in the past so historical months show no activity.',
      'Switching currency late — re-check that prices/costs are still sensible in the new unit.',
    ],
    tip: 'Fill Project Setup first. It is the foundation everything else depends on.',
  },
  {
    id: 'pg-products', icon: '◫', title: 'Products & Services',
    purpose: 'Lists everything the business sells. Each product/service becomes a revenue stream that drives revenue and the costs tied to it.',
    fields: [
      ['Name', 'What you sell (e.g. “Residential Filter”, “Annual Maintenance”).'],
      ['Revenue type', 'unit sales, subscription, service contract, project-based, commission, licensing or other — drives which revenue fields apply.'],
      ['Selling Unit / Unit of Measure', 'The unit you price and sell in. Not only “pieces” — choose Kg, gram, metric ton, litre, millilitre, bottle, box, carton, bag, m², hour, day, contract, license, subscription, or a custom unit.'],
      ['Selling Price (per selling unit)', 'The price of ONE selling unit — e.g. $2 per Kg, $420 per metric ton, $6 per litre, $1 per bottle.'],
      ['Launch date', 'When this product first becomes available (used as a default revenue start).'],
    ],
    model: 'Revenue = quantity × selling price per unit. The selling unit makes “unit sales” work for manufacturing (sell by weight/volume/packaging) as well as services (per contract/hour/license).',
    example: 'Manufacturing: “Bottled Water” priced at $1 per Bottle. Service: “Support Retainer” priced at $5,000 per Contract, or “Consulting” at $150 per Hour.',
    mistakes: [
      'Entering a monthly or annual total in “Selling Price” instead of the price of one unit.',
      'Leaving the selling unit as Piece when you actually sell by Kg or litre.',
    ],
    tip: 'Pick the selling unit that matches how you quote customers — it flows through to Revenue Assumptions and the reports.',
  },
  {
    id: 'pg-revenue', icon: '◴', title: 'Revenue Assumptions',
    purpose: 'For each product, describes how much you sell, how it grows, when it is earned, and when you collect the cash. This is the single most important driver of the model.',
    fields: [
      ['First-month sales quantity', 'Quantity sold in Month 1, in the product’s selling unit (e.g. 10,000 Kg). The master quantity that drives revenue.'],
      ['Annual / Monthly growth', 'How sales scale over time. Use one or the other.'],
      ['Revenue Timing / Recurrence', 'How the stream repeats — see the box below.'],
      ['Revenue Start Date / Revenue Date', 'When revenue begins. For One-time it is labelled “Revenue Date” (a single month), not a start.'],
      ['Revenue End Date', 'Optional — revenue stops after this month. Hidden for One-time and for Contract/project (calculated).'],
      ['Contract Duration (months)', 'For Contract/project only — how many months the contract value spreads across. The end date is calculated automatically.'],
      ['Recognition Method', 'Spread / smoothed = distribute evenly across the period’s months. Lump / cash timing = the whole amount lands in one month.'],
      ['Payment terms / collection days', 'When customers pay (cash, net 15/30/45/60/90, or custom days). Drives receivables and cash timing.'],
    ],
    model: 'The engine builds a month-by-month quantity series from the timing rules, multiplies by price to get revenue, then applies payment terms to decide when the cash actually arrives.',
    example: (
      <>Factory selling <strong>10,000 Kg/month</strong> → Continuous monthly. A <strong>one-time equipment sale</strong> → One-time on a Revenue Date. An <strong>annual license fee</strong> → Annual recurring / yearly renewal. A <strong>12-month service contract</strong> → Contract/project, duration 12. <strong>Seasonal tourism</strong> → Seasonal.</>
    ),
    mistakes: [
      'Using “Annual recurring” when the revenue is actually billed monthly.',
      'Forgetting payment terms, so cash looks like it arrives the moment a sale is booked.',
      'Entering the same revenue twice (once as a product and again as an override).',
    ],
    tip: 'One-time uses a “Revenue Date”. Contract/project uses Start Date + Contract Duration and calculates the end date — you never enter the end date manually for contracts.',
    investor: 'Investors scrutinise the quantity and growth assumptions first. Keep them defensible — tie them to capacity, pipeline or market size.',
  },
  {
    id: 'pg-direct', icon: '◵', title: 'Direct Costs / COGS',
    purpose: 'Costs that are directly caused by selling a product — the “cost of goods sold”. They scale with what and how much you sell. (Overheads that run regardless of sales belong in Operating Expenses.)',
    fields: [
      ['Calculation method', 'Cost per selling unit · % of revenue · % of selling price · fixed direct cost per month · annual allocated · one-time · manual by period.'],
      ['Linked product(s) vs Independent', 'Link the cost to one/many/all products so it follows their quantity/revenue, or leave it Independent / unassigned (it then stays out of cost of sales until assigned).'],
      ['Amount or %', 'A money amount per unit, or a percentage, depending on the method.'],
      ['Supplier payment terms', 'When you pay the supplier — drives payables and cash timing (overrides the Working Capital default).'],
      ['Start / End date', 'Optional. Blank follows the linked product’s launch date.'],
    ],
    model: 'For a linked cost the engine multiplies the method by the product’s projected driver (quantity or revenue). Direct costs sit between revenue and gross profit on the Income Statement.',
    example: (
      <>Raw material <strong>$1.25 per Kg</strong> sold (cost per selling unit). Packaging <strong>$0.10 per bottle</strong>. Payment-gateway <strong>2.5% of revenue</strong>. Subcontractor <strong>$8,000 per contract</strong>.</>
    ),
    mistakes: [
      'Putting overheads (rent, admin salaries) here — those are Operating Expenses.',
      'Leaving a direct cost Independent/unassigned, so it never enters cost of sales.',
      'Forgetting direct costs entirely, which inflates gross margin.',
    ],
    tip: 'A direct cost answers “if I sell one more unit, what extra cost do I incur?” If the answer is “nothing”, it is probably an operating expense.',
  },
  {
    id: 'pg-staffing', icon: '◶', title: 'Staffing Plan',
    purpose: 'The team and its fully-loaded payroll cost over time.',
    fields: [
      ['Department & Job title', 'Groups roles for reporting (Sales, Operations, Technology, …).'],
      ['Number of employees (headcount)', 'How many people in this role.'],
      ['Monthly salary (per employee)', 'Gross monthly pay for one person.'],
      ['Hiring start date', 'When payroll for this role begins.'],
      ['Benefits, bonus, gratuity, social security', 'Add-ons that load the base salary.'],
      ['Employer social security % (override)', 'Optional per-role override; blank uses the global rate from Tax & Regulatory.'],
    ],
    model: 'Payroll is an operating expense on the Income Statement, a cash outflow on the Cash Flow, and end-of-service/gratuity accrues as a liability on the Balance Sheet. Headcount × salary × months drives the total.',
    example: '3 Software Engineers at AED 8,000/month from Feb 2026, plus 10% benefits and the global social-security rate.',
    mistakes: [
      'Entering a team total instead of a per-employee salary × headcount.',
      'Setting the social-security rate twice (per role and globally) when one default would do.',
    ],
    tip: 'Leave the per-role social-security override blank to inherit the single global default — no duplication.',
  },
  {
    id: 'pg-opex', icon: '◷', title: 'Operating Expenses',
    purpose: 'Independent overheads — the recurring cost of running the business that does NOT scale one-for-one with sales. They never need a revenue link.',
    fields: [
      ['Cost Timing / Recurrence', 'Monthly recurring · Quarterly · Annual · One-time. Start + End dates make a temporary cost.'],
      ['Recognition Method', 'For quarterly/annual: Spread / smoothed (distribute across the period) or Lump / cash timing (the whole amount in the period’s month).'],
      ['Amount', 'For quarterly/annual, enter the full per-period amount (e.g. the annual insurance premium), not a monthly figure.'],
      ['Start / End date', 'When the cost runs. Set both for a defined-period (temporary) cost.'],
      ['Annual escalation %', 'Yearly increase applied to the cost.'],
    ],
    model: 'Operating expenses sit below gross profit and reduce operating profit / EBITDA. Timing controls which month(s) they hit; recognition controls smoothed vs lumpy.',
    example: 'Rent → Monthly. Insurance → Annual (Lump = once a year, or Spread = ÷12). A launch marketing campaign → One-time. Maintenance → Quarterly.',
    mistakes: [
      'Confusing operating expenses with direct costs.',
      'Entering a monthly figure for an annual cost (enter the full annual amount instead).',
      'Forgetting escalation, so multi-year costs stay flat unrealistically.',
    ],
    tip: 'Smoothed/Spread keeps the P&L even (accrual view); Lump shows the real cash month — pick to match how you want to read the plan.',
  },
  {
    id: 'pg-startup', icon: '◰', title: 'Startup Costs',
    purpose: 'One-off pre-opening and launch costs incurred before (or as) the business starts trading.',
    fields: [
      ['Cost name & category', 'Registration, trade license, branding, website, initial inventory, etc.'],
      ['Amount', 'The one-time amount.'],
      ['Payment date', 'When the cash goes out.'],
      ['Capitalized', 'On = becomes an asset and is depreciated; Off = expensed immediately to the P&L.'],
    ],
    model: 'Expensed startup costs hit profit once; capitalised ones become assets and depreciate over time. Either way the cash leaves on the payment date.',
    example: 'Company registration $5,000 (expensed) paid Dec 2025; initial equipment $40,000 (capitalised).',
    mistakes: [
      'Capitalising a cost that should be expensed (or vice-versa).',
      'Putting recurring costs here — those belong in Operating Expenses.',
    ],
  },
  {
    id: 'pg-assets', icon: '◱', title: 'Fixed Assets / CapEx',
    purpose: 'Long-term assets the business buys (capital expenditure) and how they depreciate.',
    fields: [
      ['Asset name & category', 'Machinery, vehicle, computers, fit-out, etc.'],
      ['Purchase amount & date', 'What it cost and when you paid.'],
      ['Useful life (years)', 'How long it serves before it is fully depreciated.'],
      ['Depreciation method', 'Straight-line spreads cost evenly; reducing balance front-loads it.'],
      ['Residual value', 'Expected value at the end of life (cannot exceed cost).'],
      ['Financing source', 'Classification only — it does NOT create funding. Actual loan/equity amounts are entered on Financing.'],
    ],
    model: 'The purchase is a one-time cash outflow (investing). Depreciation is a non-cash expense that reduces profit over the asset’s life and lowers the asset’s book value on the Balance Sheet.',
    example: 'A delivery van $120,000, 5-year life, straight-line → $24,000 depreciation per year; $120,000 cash out at purchase.',
    mistakes: [
      'Treating CapEx as an operating expense (it is capital spend, depreciated over time).',
      'Assuming depreciation is a cash cost — it reduces profit but no cash moves.',
    ],
    investor: 'CapEx-heavy plans need the cash flow to fund the purchases — investors check that financing covers the investing outflows.',
  },
  {
    id: 'pg-wc', icon: '◲', title: 'Working Capital',
    purpose: 'The timing of cash tied up in receivables, payables and inventory — the gap between booking a sale/cost and the cash actually moving.',
    fields: [
      ['Default customer collection days', 'Average days customers take to pay (DSO). Used only when a revenue stream has no specific payment terms — product terms override this.'],
      ['Default supplier payment days', 'Average days you take to pay suppliers (DPO). Used for costs without supplier-specific terms.'],
      ['Inventory days', 'Average days stock is held (DIO).'],
      ['Operating minimum cash reserve', 'The cash floor used for funding-gap checks (separate from the KPI reporting target).'],
    ],
    model: 'Receivables, payables and inventory are balance-sheet positions; their month-to-month change is a cash-flow movement. Longer collection = more cash tied up; longer payables = less.',
    example: 'Collect in 45 days, pay suppliers in 30, hold 60 days of stock → a cash-conversion cycle of 75 days to fund.',
    mistakes: [
      'Forgetting working capital, so cash looks healthier than reality.',
      'Setting collection days here when a product already has specific payment terms (the product terms win).',
    ],
    tip: 'These are defaults. Product Payment Terms (Revenue) and Supplier Payment Terms (Direct Costs) override them.',
  },
  {
    id: 'pg-financing', icon: '◳', title: 'Financing',
    purpose: 'How the business is funded — equity, loans and grants. Funding is NOT revenue; it is money put into the business.',
    fields: [
      ['Equity (founder / investor)', 'Capital contributed by owners and investors; investor shareholding %.'],
      ['Loans', 'Amount, interest rate, term, grace period, repayment type, arrangement fee.'],
      ['Grants', 'Non-dilutive funding, with expected date and any restrictions.'],
    ],
    model: 'Loan drawdowns and equity are financing cash inflows; repayments are outflows; interest is an expense on the Income Statement. Loans sit as liabilities on the Balance Sheet; equity sits in equity.',
    example: 'Founder $100,000 + investor $500,000 equity, plus a $300,000 loan at 7.5% over 60 months with a 6-month grace period.',
    mistakes: [
      'Treating a loan as revenue (it is a liability, not income).',
      'Forgetting interest, so the plan looks more profitable than it is.',
    ],
    investor: 'The Funding Request in the narrative should match the financing here, and the cash flow should show the money is actually needed and used.',
  },
  {
    id: 'pg-tax', icon: '⊞', title: 'Tax & Regulatory',
    purpose: 'Global tax settings for the model — corporate tax, VAT and payroll contributions.',
    fields: [
      ['Corporate tax', 'Enable it and set the rate; loss carry-forward optional.'],
      ['VAT system enabled', 'Turns the VAT mechanism on for the model.'],
      ['Default VAT rate', 'The rate applied to items marked VAT-applicable. Line-level VAT switches only flag whether an item is subject to VAT — they do not set the rate.'],
      ['Employer social security % (global default)', 'Applied to every staffing role unless a role overrides it.'],
    ],
    model: 'Corporate tax reduces net profit (and is paid out as cash later). VAT flows through a payable/receivable position. Social security loads payroll cost.',
    example: 'UAE: corporate tax 9%, VAT 5%, employer social security 12.5% as the global default.',
    mistakes: [
      'Enabling corporate tax or VAT but leaving the rate at 0%.',
      'Forgetting tax assumptions entirely, overstating net profit and cash.',
    ],
    tip: 'Tax is the global configuration; the per-line VAT switches only say “this item is subject to VAT” — they never set the rate.',
  },
  {
    id: 'pg-scenarios', icon: '⊟', title: 'Scenarios',
    purpose: 'Stress-test the plan by adjusting the base assumptions up or down for a Conservative and an Optimistic case.',
    fields: [
      ['Base case', 'Your central plan — 0% adjustments.'],
      ['Conservative / Optimistic', 'Percentage sliders for sales volume, price, costs, salaries, collection days, interest, tax, inflation, and more.'],
    ],
    model: 'Adjustments are applied at calculation time on top of the base assumptions (the base is never mutated). Statements and charts can be viewed per scenario.',
    example: 'Conservative: −15% sales volume, +10% direct costs, +30 collection days. Optimistic: +20% volume.',
    mistakes: ['Using extreme, indefensible swings that make the scenarios meaningless.'],
    investor: 'Investors use scenarios to judge downside risk — a plan that still survives the Conservative case is far more credible.',
  },
  {
    id: 'pg-kpis', icon: '⊡', title: 'KPIs & Targets',
    purpose: 'The targets management is steering toward and that investors benchmark against — they are goals, not drivers of the projection.',
    fields: [
      ['Margin targets', 'Target gross / EBITDA / net profit margins.'],
      ['Break-even target date', 'When the business expects to stop losing money.'],
      ['Min. monthly revenue / cash targets', 'Floors to track against.'],
      ['Investor metrics', 'CAC, LTV, payback period, ROI, DSCR, current ratio.'],
      ['Target minimum cash balance (reporting)', 'A reporting benchmark — distinct from the operating cash reserve in Working Capital, which affects funding.'],
    ],
    model: 'KPIs are compared against the computed results; they do not change the projection. They appear in the analysis and reports as targets.',
    example: 'Target gross margin 65%, break-even by Q3 2027, target minimum cash AED 150,000.',
    mistakes: ['Confusing the KPI “target minimum cash” (reporting) with the Working-Capital “operating minimum cash reserve” (drives funding).'],
  },
  {
    id: 'pg-review', icon: '✓', title: 'Review & Completion',
    purpose: 'A final check before generating statements and reports — what is filled, what is missing, and any validation warnings.',
    fields: [
      ['Completion percentage', 'How much of the plan is filled in (also shown in the sidebar and top bar).'],
      ['Missing fields & warnings', 'Sections that still need attention before the model is trustworthy.'],
    ],
    model: 'Review reads the same assumptions the engine uses, so fixing warnings here directly improves the statements.',
    example: 'Completion 86% with warnings: “2 direct costs unassigned”, “revenue stream has no projection values”.',
    mistakes: ['Generating an investor report while important warnings are still open.'],
    tip: 'Clear the warnings before exporting — they usually point to a number that will look wrong to a reader.',
  },
  {
    id: 'pg-text', icon: '✎', title: 'Text Builder (Narrative)',
    purpose: 'Write the written business plan that sits alongside the numbers, in a rich-text editor with an outline and autosave.',
    fields: [
      ['Narrative sections', 'Executive Summary, Company Overview, Problem & Solution, Market Opportunity, Products & Services, Business Model, Sales & Marketing, Operations Plan, Management Team, Financial Plan, Risks, Funding Request.'],
    ],
    model: 'The narrative does not feed the calculations — it explains and justifies the assumptions so a reader understands the story behind the numbers.',
    example: 'Use the Financial Plan section to summarise the projection in words; use Funding Request to state the amount and use of funds that match the Financing page.',
    mistakes: ['Writing a narrative that contradicts the numbers (e.g. claiming a market size the revenue assumptions ignore).'],
    tip: 'Keep the Executive Summary last — write it once the rest of the plan and the numbers are settled.',
  },
  {
    id: 'pg-statements', icon: '⚖', title: 'Financial Statements',
    purpose: 'The three generated IFRS statements — produced from one shared model so they reconcile against each other.',
    fields: [
      ['Income Statement', 'Revenue − COGS = Gross profit; − operating expenses = EBITDA; − depreciation − interest − tax = Net profit.'],
      ['Balance Sheet', 'Assets (cash, receivables, inventory, fixed assets) = Equity + Liabilities (loans, payables, tax/VAT).'],
      ['Cash Flow', 'Operating + Investing (CapEx) + Financing (loans, equity, repayments) = the change in cash; ending cash ties to the Balance Sheet.'],
    ],
    model: 'Cash is derived so that Assets = Equity + Liabilities by construction, which guarantees the Balance Sheet balances and the Cash Flow’s closing cash matches the Balance Sheet’s cash line.',
    example: 'Profit can be positive while cash falls — e.g. when receivables grow or a loan is repaid. The three statements together show why.',
    mistakes: ['Reading only the Income Statement — a profitable plan can still run out of cash.'],
    investor: 'The reconciliation panels prove the model is internally consistent; a balance sheet that does not balance is an instant red flag.',
  },
  {
    id: 'pg-analysis', icon: '◑', title: 'Financial Analysis',
    purpose: 'Investor-grade charts, KPIs and ratios that summarise the plan and highlight strengths and risks.',
    fields: [
      ['Charts', 'Revenue & profit trend, margins, cash-flow by activity, closing-cash trend, assets composition, debt vs equity.'],
      ['KPIs & ratios', 'Margins, liquidity (current ratio), leverage, DSCR, break-even.'],
    ],
    model: 'Analysis reads the generated statements — it does not change them. It is the lens investors use to interpret the model quickly.',
    example: 'A rising revenue trend with falling closing cash signals a working-capital or funding problem worth explaining.',
    mistakes: ['Ignoring warning signs (negative cash, thin margins, high leverage) because the headline revenue looks good.'],
    investor: 'Warning signs investors watch: negative or near-zero cash, gross margin too low to cover overheads, DSCR below 1, and growth that depends on unrealistic assumptions.',
  },
  {
    id: 'pg-reports', icon: '⎙', title: 'Business Plan Report & Exports',
    purpose: 'Package the plan into shareable deliverables.',
    fields: [
      ['Word report', 'A formatted business-plan document (narrative + tables) for editing and sharing.'],
      ['PDF report', 'A polished, fixed-layout investor report.'],
      ['Excel model', 'A fully-linked financial model with formulas — for analysts who want to inspect or extend the numbers.'],
      ['JSON assumptions', 'The raw inputs, for backup or transfer between plans.'],
    ],
    model: 'All exports are generated from the same report data source, so they show consistent figures — including the timing/recurrence assumptions.',
    example: 'Send the PDF to investors, the Word doc to a partner who will edit it, the Excel model to a bank analyst, and keep the JSON as a backup.',
    mistakes: ['Exporting before clearing Review warnings, so the shared report contains obviously-wrong numbers.'],
    tip: 'Choose the export for the audience: PDF to read, Word to edit, Excel to analyse, JSON to back up.',
  },
]

// -- glossary ---------------------------------------------------------------
const GLOSSARY: [string, string][] = [
  ['Revenue', 'The money earned from selling products or services, before any costs.'],
  ['Revenue stream', 'One product or service that generates revenue, with its own pricing and timing.'],
  ['COGS (Cost of Goods Sold)', 'Costs caused directly by making/delivering what you sell — they scale with sales.'],
  ['Gross profit', 'Revenue minus COGS — what is left to cover overheads.'],
  ['EBITDA', 'Earnings Before Interest, Tax, Depreciation and Amortisation — operating profitability before financing and non-cash items.'],
  ['Net profit', 'The bottom line — what remains after all costs, interest and tax.'],
  ['CapEx', 'Capital expenditure — buying long-term assets (machinery, vehicles) that are used over many years.'],
  ['Depreciation', 'Spreading an asset’s cost over its useful life as a non-cash expense.'],
  ['Working capital', 'Cash tied up in day-to-day operations — receivables + inventory − payables.'],
  ['Accounts receivable (AR)', 'Money customers owe you for sales already made.'],
  ['Accounts payable (AP)', 'Money you owe suppliers for costs already incurred.'],
  ['Cash flow', 'The actual movement of cash in and out — different from profit.'],
  ['Break-even', 'The point where revenue covers all costs and profit is zero.'],
  ['Scenario', 'A version of the plan with adjusted assumptions (Base / Conservative / Optimistic).'],
  ['KPI', 'Key Performance Indicator — a metric you track against a target.'],
  ['VAT', 'Value Added Tax — a consumption tax collected on sales and reclaimed on purchases.'],
  ['Corporate tax', 'Tax charged on company profits.'],
  ['Equity', 'Money owners/investors put into the business; their stake in it.'],
  ['Loan', 'Borrowed money repaid over time with interest — a liability, not revenue.'],
  ['Grant', 'Funding that does not have to be repaid and does not dilute ownership.'],
  ['Recognition method', 'Whether a periodic amount is spread evenly across the period (smoothed) or lands in a single month (lump/cash timing).'],
  ['Recurring revenue', 'Revenue that repeats — monthly or annually (subscriptions, retainers, renewals).'],
  ['One-time revenue', 'Revenue earned once, in a single month (e.g. an equipment sale).'],
  ['Direct cost', 'A cost tied to a product that scales with sales (see COGS).'],
  ['Operating expense', 'An overhead that runs regardless of sales (rent, admin, marketing).'],
]

// -- common mistakes --------------------------------------------------------
const MISTAKES: [string, string][] = [
  ['Entering the same revenue twice', 'Set the price once on the product; only use a Revenue Assumptions override when the model truly charges differently.'],
  ['Treating a loan as revenue', 'A loan is borrowed money (a liability). It belongs on Financing, not as a sale.'],
  ['Treating CapEx as an operating expense', 'Long-term assets are capitalised and depreciated, not expensed in one month.'],
  ['Forgetting payment terms', 'Without collection days, cash appears the instant a sale is booked — which is rarely true.'],
  ['Using annual recurring for monthly revenue', 'If you bill every month, use Monthly recurring / Continuous — not Annual recurring / yearly renewal.'],
  ['Forgetting direct costs', 'No COGS means an impossibly high gross margin; add the cost of what you sell.'],
  ['Confusing direct costs with operating expenses', 'Direct costs scale with sales; operating expenses are independent overheads.'],
  ['Forgetting VAT / tax assumptions', 'Skipping tax overstates net profit and the cash you will actually keep.'],
  ['Forgetting working capital', 'Ignoring receivables/payables/inventory makes cash look healthier than reality.'],
  ['Using unrealistic growth rates', 'Hockey-stick growth with no basis is the fastest way to lose investor trust.'],
  ['Not checking cash flow when profit looks positive', 'A profitable plan can still run out of cash — always read the Cash Flow.'],
]

// -- worked examples --------------------------------------------------------
const EXAMPLES: [string, ReactNode][] = [
  ['Manufacturing business', 'Product “Bottled Water” priced per Bottle; Revenue Assumptions = Continuous monthly, 50,000 bottles/month with 3% annual growth; Direct cost = $0.10 packaging per bottle + raw material per litre; Operating expenses = rent (monthly), utilities (monthly); Fixed assets = bottling line (CapEx, depreciated).'],
  ['Service contract business', 'Product “Implementation Project” priced per Contract; Revenue Assumptions = Contract/project, duration 12 months, Spread recognition; Direct cost = subcontractor per contract; Staffing = consultants; Payment terms = net 30.'],
  ['Subscription / SaaS', 'Product “Pro Plan” priced per Subscription; Revenue Assumptions = Monthly recurring with monthly churn and growth; Direct cost = hosting as % of revenue + payment-gateway %; Operating expenses = software, marketing.'],
  ['One-time project revenue', 'Product “Equipment Sale” priced per Unit; Revenue Assumptions = One-time on a Revenue Date; Direct cost = one-time cost of the equipment; cash collected per payment terms.'],
  ['Seasonal business', 'Product “Tour Package” priced per Booking; Revenue Assumptions = Seasonal with higher multipliers in peak months; Operating expenses = mostly fixed year-round; Working capital tuned for the off-season cash gap.'],
]

// -- table of contents ------------------------------------------------------
const TOC: [string, string][] = [
  ['intro', '1 · Introduction'],
  ['getting-started', '2 · Getting Started'],
  ['workflow', '3 · Full Workflow'],
  ['page-by-page', '4 · Page-by-Page Guide'],
  ['glossary', '5 · Concepts Glossary'],
  ['mistakes', '6 · Common Mistakes'],
  ['examples', '7 · Worked Examples'],
]

const PIPELINE = [
  { icon: '◧', title: '1 · Capture assumptions', body: 'You fill in structured inputs — products, pricing, costs, staffing, financing, tax and more. Every number you enter is an assumption the model will use.' },
  { icon: '∑', title: '2 · Build the projection', body: 'The engine turns those assumptions into a month-by-month time series: revenue build-up, COGS, payroll, operating costs, depreciation, loan amortisation and working-capital timing.' },
  { icon: '⚖', title: '3 · Generate statements', body: 'From the time series it produces three IFRS financial statements — Income Statement, Balance Sheet and Cash Flow — that reconcile against each other.' },
  { icon: '◑', title: '4 · Analyse & report', body: 'Investor-grade charts and KPIs summarise the plan, and a Word / PDF report plus an Excel model can be generated for sharing.' },
]

const GROUP_BLURB: Record<string, string> = {
  Foundation: 'Identity and the shape of the projection — currency, period length and frequency.',
  'Revenue & Costs': 'What you sell, how revenue is forecast, and the costs tied directly to delivery.',
  'People & Operations': 'Your team and the recurring costs of running the business.',
  'Capital & Compliance': 'One-off and capital spend, cash timing, funding sources, and tax rules.',
  Planning: 'Scenarios, target KPIs, and a final review before generating statements.',
  'Written Plan': 'The narrative document that sits alongside the numbers.',
  'Financial Statements': 'The generated outputs — statements and investor analysis.',
  Reporting: 'Shareable deliverables for investors, banks and stakeholders.',
}

export function GuidePage() {
  const navigate = useNavigate()

  return (
    <div className="landing">
      <header className="landing__header">
        <div className="landing__brand">
          <div className="sidebar__logo">B</div>
          <div>
            <div className="landing__title">Business Plan Studio</div>
            <div className="muted" style={{ fontSize: 13 }}>User Guide &amp; Manual</div>
          </div>
        </div>
        <div className="row" style={{ gap: 12, alignItems: 'center' }}>
          <UserMenu />
          <button className="btn btn--secondary btn--lg" onClick={() => navigate('/projects')}>
            ← Back to Projects
          </button>
        </div>
      </header>

      <div className="landing__body">
        {/* Hero */}
        <section className="guide-hero">
          <span className="badge badge--blue">Manual</span>
          <h1 className="guide-hero__title">The complete guide to Business Plan Studio</h1>
          <p className="guide-hero__lead">
            This manual teaches you how to use the app page by page — what every field means, how it
            feeds the financial model, worked examples, and the mistakes to avoid. Read it top to
            bottom, or jump to a section below.
          </p>
        </section>

        {/* Table of contents */}
        <div className="card" style={{ marginBottom: 8 }}>
          <div className="card__body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
              {TOC.map(([id, label]) => (
                <a key={id} href={`#${id}`} className="btn btn--secondary" style={{ justifyContent: 'flex-start' }}>{label}</a>
              ))}
            </div>
          </div>
        </div>

        {/* 1. Introduction */}
        <H2 id="intro">1 · Introduction</H2>
        <p className="guide-section-lead">
          Business Plan Studio turns the assumptions behind a business into a complete,
          investor-grade financial projection — three reconciling IFRS statements, analysis and a
          shareable report.
        </p>
        <div className="card"><div className="card__body">
          <H4>What it does</H4>
          <p>You capture structured assumptions across a guided workflow; the app builds a month-by-month model and produces an Income Statement, Balance Sheet and Cash Flow that tie together, plus charts and exports.</p>
          <H4>Who should use it</H4>
          <p>Founders, finance teams, consultants, accelerators, and anyone preparing a plan for investors, banks or internal decision-making.</p>
          <H4>What kinds of plan it supports</H4>
          <Bullets items={[
            'Manufacturing (sell by Kg, litre, bottle, carton, metric ton, piece…)',
            'Services and consulting (per contract, hour, retainer)',
            'Subscription / SaaS (recurring revenue with churn)',
            'Project-based businesses (contract spread over a fixed period)',
            'Seasonal businesses, and one-off / project revenue',
          ]} />
          <H4>How assumptions flow into statements</H4>
          <p>Everything is a pipeline: your inputs → a month-by-month projection → the three statements → analysis and reports.</p>
          <div className="guide-pipeline" style={{ marginTop: 14 }}>
            {PIPELINE.map((s, i) => (
              <div className="guide-stage" key={s.title}>
                <div className="card guide-stage__card">
                  <div className="card__icon guide-stage__icon">{s.icon}</div>
                  <div className="guide-stage__title">{s.title}</div>
                  <div className="guide-stage__body">{s.body}</div>
                </div>
                {i < PIPELINE.length - 1 && <div className="guide-stage__arrow" aria-hidden>→</div>}
              </div>
            ))}
          </div>
          <H4>Assumptions vs projections vs statements vs reports vs exports</H4>
          <FieldTable rows={[
            ['Assumptions', 'The inputs you type — prices, quantities, costs, salaries, loans, tax. Editable.'],
            ['Projection', 'The month-by-month time series the engine computes from the assumptions.'],
            ['Statements', 'The Income Statement, Balance Sheet and Cash Flow derived from the projection.'],
            ['Reports', 'A formatted business-plan document (Word/PDF) combining numbers and narrative.'],
            ['Exports', 'The deliverable files — Word, PDF, Excel model, or raw JSON assumptions.'],
          ]} />
        </div></div>

        {/* 2. Getting started */}
        <H2 id="getting-started">2 · Getting Started</H2>
        <div className="card"><div className="card__body">
          <ol className="guide-ol">
            <li><strong>Create a company (or load the demo).</strong> Plans are grouped under a company. On the Projects page you can load the AquaPure demo to explore a fully worked example, or create your own company.</li>
            <li><strong>Create a project / business plan.</strong> Give the plan a name; you’ll set identity and projection settings next.</li>
            <li><strong>Set the foundation in Project Setup.</strong> Choose the reporting currency, the projection start date, the length (3/5/10 years) and the frequency (monthly is most detailed). Everything else builds on these.</li>
            <li><strong>Work through the sections.</strong> Add products, revenue and cost assumptions, staffing, capital, financing and tax. Your work saves per section as you go.</li>
            <li><strong>Watch completion tracking.</strong> The sidebar and top bar show a live completion percentage so you always know how much is filled in before generating statements.</li>
          </ol>
          <Callout kind="tip">Fill <strong>Project Setup</strong> first, then <strong>Products &amp; Services</strong>, then <strong>Revenue Assumptions</strong> — the rest of the model depends on these three.</Callout>
          <div className="row" style={{ gap: 12, marginTop: 18 }}>
            <button className="btn btn--primary btn--lg" onClick={() => navigate('/projects')}>Go to Projects</button>
            <button className="btn btn--secondary btn--lg" onClick={() => navigate('/projects/new')}>+ New Business Plan</button>
          </div>
        </div></div>

        {/* 3. Full workflow — driven by the real nav model */}
        <H2 id="workflow">3 · Full Workflow Overview</H2>
        <p className="guide-section-lead">
          Open a project and you’ll find these pages in the sidebar, grouped in the order you’ll
          usually work through them. You don’t have to complete them strictly in order — the
          completion tracker shows what’s still missing.
        </p>
        <div className="guide-groups">
          {NAV_GROUPS.map((group) => {
            const pages = NAV_PAGES.filter((p) => p.group === group)
            return (
              <div className="card guide-group" key={group}>
                <div className="card__header">
                  <div className="card__header-main">
                    <div className="card__icon">{pages[0]?.icon ?? '◦'}</div>
                    <div>
                      <div className="card__title">{group}</div>
                      <div className="card__subtitle">{GROUP_BLURB[group]}</div>
                    </div>
                  </div>
                </div>
                <div className="card__body" style={{ paddingTop: 8, paddingBottom: 8 }}>
                  <ul className="guide-steplist">
                    {pages.map((p) => {
                      const n = NAV_PAGES.indexOf(p) + 1
                      return (
                        <li className="guide-step" key={p.slug}>
                          <span className="guide-step__num">{n}</span>
                          <span className="guide-step__text">
                            <span className="guide-step__label">{p.label}</span>
                            <span className="guide-step__sub">{p.subtitle}</span>
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </div>
            )
          })}
        </div>

        {/* 4. Page-by-page guide */}
        <H2 id="page-by-page">4 · Page-by-Page Guide</H2>
        <p className="guide-section-lead">
          A dedicated section for every page: its purpose, the fields and what they mean, how it
          affects the model, an example, and the mistakes to avoid.
        </p>
        <div className="stack">
          {PAGE_GUIDES.map((g) => (
            <div className="card" id={g.id} key={g.id} style={{ scrollMarginTop: 24 }}>
              <div className="card__header">
                <div className="card__header-main">
                  <div className="card__icon">{g.icon}</div>
                  <div>
                    <div className="card__title">{g.title}</div>
                    <div className="card__subtitle">{g.purpose}</div>
                  </div>
                </div>
              </div>
              <div className="card__body">
                <H4>Fields &amp; what they mean</H4>
                <FieldTable rows={g.fields} />
                <H4>How it affects the model</H4>
                <p>{g.model}</p>
                <H4>Example</H4>
                <p className="muted">{g.example}</p>
                {g.tip && <Callout kind="tip">{g.tip}</Callout>}
                {g.investor && <Callout kind="investor">{g.investor}</Callout>}
                <H4>Common mistakes</H4>
                <Bullets items={g.mistakes} />
              </div>
            </div>
          ))}
        </div>

        {/* 5. Glossary */}
        <H2 id="glossary">5 · Business-Plan Concepts Glossary</H2>
        <div className="card"><div className="card__body">
          <FieldTable rows={GLOSSARY.map(([t, d]) => [t, d] as [string, ReactNode])} />
        </div></div>

        {/* 6. Common mistakes */}
        <H2 id="mistakes">6 · Common Mistakes to Avoid</H2>
        <div className="stack--sm">
          {MISTAKES.map(([title, body]) => (
            <Callout kind="mistake" title={title} key={title}>{body}</Callout>
          ))}
        </div>

        {/* 7. Examples */}
        <H2 id="examples">7 · Worked Examples</H2>
        <div className="guide-concepts">
          {EXAMPLES.map(([title, body]) => (
            <div className="card guide-concept" key={title}>
              <div className="card__body">
                <div className="card__icon" style={{ marginBottom: 12 }}>◴</div>
                <div className="guide-concept__title">{title}</div>
                <div className="guide-concept__body">{body}</div>
              </div>
            </div>
          ))}
        </div>

        <p className="muted" style={{ marginTop: 32, fontSize: 12.5, textAlign: 'center' }}>
          Business Plan Studio — Financial Projection Suite · User Guide &amp; Manual
        </p>
      </div>
    </div>
  )
}
