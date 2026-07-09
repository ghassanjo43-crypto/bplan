import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { CompletionRing } from '@/components/ui/Progress'
import { pageBySlug } from '@/routes/nav'
import { useCompany } from '@/api/companyApi'
import { EditCompanyModal } from '@/components/company/EditCompanyModal'
import { UserMenu } from '@/components/auth/UserMenu'
import { HelpModeToggle } from '@/components/HelpModeToggle'
import { useProjectContext } from './ProjectContext'

function PencilIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
    </svg>
  )
}

export function TopBar() {
  const { project, completion } = useProjectContext()
  const location = useLocation()
  const slug = location.pathname.split('/').pop() ?? ''
  const page = pageBySlug(slug)
  const [editOpen, setEditOpen] = useState(false)

  const companyId = project?.company_id ?? null
  const companyQ = useCompany(companyId)

  // The title is the parent company's name (the canonical source). It is never
  // taken from project_name; setup.business_name / project.name are fallbacks
  // only until the company record loads or for legacy projects.
  const companyName =
    companyQ.data?.company_name || project?.setup?.business_name || project?.name || 'Untitled Company'
  const projectName = project?.setup?.project_name ?? ''
  const percent = completion?.completion_percent ?? 0

  return (
    <header className="topbar">
      <div className="topbar__left">
        <div className="topbar__eyebrow">{page?.group ?? 'Business Plan'}</div>
        <div className="topbar__title-row">
          <button
            type="button"
            className="topbar__title-link"
            onClick={() => companyId && setEditOpen(true)}
            title="Edit company profile"
          >
            {companyName}
          </button>
          {companyId && (
            <button
              type="button"
              className="topbar__edit"
              title="Edit company profile"
              aria-label="Edit company profile"
              onClick={() => setEditOpen(true)}
            >
              <PencilIcon />
            </button>
          )}
        </div>
        {projectName && <div className="topbar__project">{projectName}</div>}
      </div>

      <div className="topbar__right" style={{ gap: 18 }}>
        <div className="topbar__completion">
          <div className="topbar__completion-label">
            <small>Plan Completion</small>
            <strong>{percent}%</strong>
          </div>
          <div style={{ position: 'relative', width: 40, height: 40 }}>
            <CompletionRing percent={percent} />
          </div>
        </div>
        <HelpModeToggle />
        <UserMenu />
      </div>

      <EditCompanyModal companyId={companyId} open={editOpen} onClose={() => setEditOpen(false)} />
    </header>
  )
}
