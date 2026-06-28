import { useNavigate } from 'react-router-dom'
import { NAV_GROUPS, NAV_PAGES } from '@/routes/nav'
import { UserMenu } from '@/components/auth/UserMenu'

/**
 * Standalone, top-level user guide that explains what Business Plan Studio does
 * and how the workflow fits together. It is intentionally project-independent so
 * it is reachable before a project is selected. The "workflow" section is driven
 * by the same NAV model as the sidebar, so it can never drift out of date.
 */

interface Stage {
  icon: string
  title: string
  body: string
}

const PIPELINE: Stage[] = [
  {
    icon: '◧',
    title: '1 · Capture assumptions',
    body: 'You fill in structured inputs — products, pricing, costs, staffing, financing, tax and more. Every number you enter is an assumption the model will use.',
  },
  {
    icon: '∑',
    title: '2 · Build the projection',
    body: 'The engine turns those assumptions into a month-by-month time series: revenue build-up, COGS, payroll, operating costs, depreciation, loan amortisation and working-capital timing.',
  },
  {
    icon: '⚖',
    title: '3 · Generate statements',
    body: 'From the time series it produces three IFRS financial statements — Income Statement, Balance Sheet and Cash Flow — that reconcile against each other.',
  },
  {
    icon: '◑',
    title: '4 · Analyse & report',
    body: 'Investor-grade charts and KPIs summarise the plan, and a Word / PDF report plus an Excel model can be generated for sharing.',
  },
]

interface Concept {
  icon: string
  title: string
  body: string
}

const CONCEPTS: Concept[] = [
  {
    icon: '✓',
    title: 'Completion tracking',
    body: 'Each input section reports whether it is complete. The sidebar and top bar show a live percentage so you always know how much of the plan is filled in before generating statements.',
  },
  {
    icon: '⊟',
    title: 'Scenarios',
    body: 'Beyond the Base case you can define Conservative and Optimistic scenarios with adjustment sliders. Statements and charts can be viewed per scenario to stress-test the plan.',
  },
  {
    icon: '⚖',
    title: 'IFRS statements that reconcile',
    body: 'The Income Statement, Balance Sheet and Cash Flow are derived from one shared model, so the balance sheet balances and cash ties out — with reconciliation panels that show the bridge.',
  },
  {
    icon: '✎',
    title: 'Written plan (Text Builder)',
    body: 'A rich-text editor lets you write the narrative business plan — executive summary, market, strategy — alongside the numbers, with an outline and autosave.',
  },
  {
    icon: '⎙',
    title: 'Exports',
    body: 'Produce a polished investor report in Word or PDF, export a fully-linked Excel financial model, or download the raw assumptions as JSON.',
  },
  {
    icon: '👤',
    title: 'Companies, projects & roles',
    body: 'Plans are grouped under companies. Admins manage users and can see an audit log; standard users work on their own company’s business plans.',
  },
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
            <div className="muted" style={{ fontSize: 13 }}>User Guide</div>
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
        {/* Intro */}
        <section className="guide-hero">
          <span className="badge badge--blue">Guide</span>
          <h1 className="guide-hero__title">What this app does, and how to use it</h1>
          <p className="guide-hero__lead">
            Business Plan Studio turns the assumptions behind a business into a complete,
            investor-grade financial projection. You enter structured inputs across a guided
            workflow; the app builds a month-by-month model, produces three reconciling IFRS
            financial statements, and packages everything into charts and a shareable report.
          </p>
        </section>

        {/* How it works — the pipeline */}
        <h2 className="guide-h2">How it works</h2>
        <p className="guide-section-lead">
          The app is a pipeline. Everything flows from the assumptions you enter on the left to
          the statements and reports on the right.
        </p>
        <div className="guide-pipeline">
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

        {/* The workflow, step by step — driven by the real nav model */}
        <h2 className="guide-h2">The workflow, step by step</h2>
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

        {/* Key concepts */}
        <h2 className="guide-h2">Key concepts</h2>
        <div className="guide-concepts">
          {CONCEPTS.map((c) => (
            <div className="card guide-concept" key={c.title}>
              <div className="card__body">
                <div className="card__icon" style={{ marginBottom: 12 }}>{c.icon}</div>
                <div className="guide-concept__title">{c.title}</div>
                <div className="guide-concept__body">{c.body}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Getting started */}
        <h2 className="guide-h2">Getting started</h2>
        <div className="card">
          <div className="card__body">
            <ol className="guide-ol">
              <li>
                <strong>Load the demo, or create a plan.</strong> On the Projects page you can load
                the AquaPure demo company to explore a fully worked example, or start a new business
                plan from scratch.
              </li>
              <li>
                <strong>Fill in the Foundation first.</strong> Project Setup defines your currency
                and the projection period and frequency — everything else builds on it.
              </li>
              <li>
                <strong>Work through the sections.</strong> Add products, revenue and cost
                assumptions, staffing, capital and financing. Watch the completion percentage climb.
              </li>
              <li>
                <strong>Review, then generate.</strong> The Review page summarises and validates your
                inputs. Once you’re happy, open the Income Statement, Balance Sheet, Cash Flow and
                Financial Analysis pages to see the generated model.
              </li>
              <li>
                <strong>Write and export.</strong> Use the Text Builder for the narrative, then
                generate the Word / PDF report or the Excel model from the Reporting page.
              </li>
            </ol>
            <div className="row" style={{ gap: 12, marginTop: 20 }}>
              <button className="btn btn--primary btn--lg" onClick={() => navigate('/projects')}>
                Go to Projects
              </button>
              <button className="btn btn--secondary btn--lg" onClick={() => navigate('/projects/new')}>
                + New Business Plan
              </button>
            </div>
          </div>
        </div>

        <p className="muted" style={{ marginTop: 32, fontSize: 12.5, textAlign: 'center' }}>
          Business Plan Studio — Financial Projection Suite
        </p>
      </div>
    </div>
  )
}
