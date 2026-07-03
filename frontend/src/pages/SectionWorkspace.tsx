import { useState, type ReactNode } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SaveBar } from '@/components/SaveBar'
import { ProjectionGrid } from '@/components/projection/ProjectionGrid'
import { useProjectContext } from '@/layouts/ProjectContext'
import { pageBySlug } from '@/routes/nav'
import type { ProjectionSection } from '@/types/projection'
import { DirectCostsPage } from './DirectCostsPage'
import { OperatingExpensesPage } from './OperatingExpensesPage'
import { RevenueStreamsSection } from '@/components/revenueStream/RevenueStreamWizard'

function Workspace({
  slug,
  section,
  setupLabel,
  projectionLabel,
  setup,
}: {
  slug: string
  section: ProjectionSection
  setupLabel: string
  projectionLabel: string
  setup: ReactNode
}) {
  const { projectId } = useProjectContext()
  const page = pageBySlug(slug)
  const [tab, setTab] = useState<'setup' | 'projection'>('setup')

  return (
    <>
      <PageHeader
        breadcrumb={`Business Plan · ${page?.group ?? ''}`}
        title={page?.label ?? ''}
        subtitle={page?.subtitle}
      />

      <div className="tabs">
        <button className={`tab${tab === 'setup' ? ' tab--active' : ''}`} onClick={() => setTab('setup')}>
          {setupLabel}
        </button>
        <button className={`tab${tab === 'projection' ? ' tab--active' : ''}`} onClick={() => setTab('projection')}>
          {projectionLabel}
        </button>
      </div>

      {tab === 'setup' ? setup : <ProjectionGrid projectId={projectId} section={section} />}

      <SaveBar slug={slug} />
    </>
  )
}

export function RevenueWorkspace() {
  return (
    <Workspace
      slug="revenue"
      section="revenue"
      setupLabel="Revenue Setup"
      projectionLabel="Revenue Projection"
      // Revenue Streams is the single primary revenue workflow. The legacy
      // per-product RevenuePage is no longer embedded here (products are hidden);
      // ProductService and its routes remain for backward compatibility.
      setup={<RevenueStreamsSection />}
    />
  )
}

export function DirectCostsWorkspace() {
  return (
    <Workspace
      slug="direct-costs"
      section="direct_costs"
      setupLabel="Direct Cost Setup"
      projectionLabel="Direct Cost Projection"
      setup={<DirectCostsPage embedded />}
    />
  )
}

export function OperatingExpensesWorkspace() {
  return (
    <Workspace
      slug="operating-expenses"
      section="operating_expenses"
      setupLabel="Expense Setup"
      projectionLabel="Expense Projection"
      setup={<OperatingExpensesPage embedded />}
    />
  )
}
