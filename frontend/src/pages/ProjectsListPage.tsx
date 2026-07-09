import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDeleteProject, useDemoPreview, useLoadDemo, useProjects } from '@/api/hooks'
import { useCompanies, useCreateCompanyProject } from '@/api/companyApi'
import { LoadingScreen, Spinner } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { DemoCompanyCard } from './DemoCompanyCard'
import { CompanyProfileCard } from '@/components/company/CompanyProfileCard'
import { ProjectCard } from '@/components/company/ProjectCard'
import { EditCompanyModal } from '@/components/company/EditCompanyModal'
import { UserMenu } from '@/components/auth/UserMenu'
import { HelpTooltip } from '@/components/ui/HelpTooltip'
import type { ProjectSummary } from '@/types'

export function ProjectsListPage() {
  const navigate = useNavigate()
  const { data: projects, isLoading } = useProjects()
  const { data: companies, isLoading: companiesLoading } = useCompanies()
  const demoPreview = useDemoPreview()
  const loadDemo = useLoadDemo()
  const del = useDeleteProject()
  const createProject = useCreateCompanyProject()
  const { notify } = useToast()
  const [editCompanyId, setEditCompanyId] = useState<string | null>(null)

  const handleLoadDemo = (confirmFirst = false) => {
    if (confirmFirst && !window.confirm(
      'Reloading the demo company will overwrite changes to the company profile and its demo projects. Continue?',
    )) return
    loadDemo.mutate(undefined, {
      onSuccess: (project) => {
        notify('AquaPure demo company loaded')
        navigate(`/projects/${project.id}/setup`)
      },
      onError: (e) => notify((e as Error).message || 'Failed to load demo', 'error'),
    })
  }

  const openProject = (id: string) => navigate(`/projects/${id}/setup`)
  const deleteProject = (p: ProjectSummary) => {
    if (!window.confirm(`Delete project "${p.project_name || p.name}"? This cannot be undone.`)) return
    del.mutate(p.id, { onSuccess: () => notify('Project deleted') })
  }
  const addProject = (companyId: string) =>
    createProject.mutate(
      { companyId, name: 'New Business Plan' },
      {
        onSuccess: (proj) => { notify('Project created'); navigate(`/projects/${proj.id}/setup`) },
        onError: (e) => notify((e as Error).message || 'Failed to create project', 'error'),
      },
    )

  if (isLoading || companiesLoading) return <LoadingScreen label="Loading companies…" />

  const companyList = companies ?? []
  const allProjects = projects ?? []
  const demoLoaded = companyList.some((c) => c.status === 'demo')
  const ungrouped = allProjects.filter((p) => !p.company_id || !companyList.some((c) => c.id === p.company_id))

  return (
    <div className="landing">
      <header className="landing__header">
        <div className="landing__brand">
          <div className="sidebar__logo">B</div>
          <div>
            <div className="landing__title">Business Plan Studio</div>
            <div className="muted" style={{ fontSize: 13 }}>Companies and their business plans</div>
          </div>
        </div>
        <div className="row" style={{ gap: 12, alignItems: 'center' }}>
          <button className="btn btn--ghost btn--sm" onClick={() => navigate('/guide')} title="How this app works">
            ? Guide
          </button>
          <UserMenu />
          <button className="btn btn--primary btn--lg" onClick={() => navigate('/projects/new')}>
            + New Business Plan
          </button>
        </div>
      </header>

      <div className="landing__body">
        {/* Load-demo CTA only until the demo company exists */}
        {!demoLoaded && (
          <DemoCompanyCard
            preview={demoPreview.data}
            loading={demoPreview.isLoading}
            onLoad={() => handleLoadDemo(false)}
            isLoading={loadDemo.isPending}
            spinner={<Spinner />}
          />
        )}

        {companyList.length === 0 && ungrouped.length === 0 ? (
          <div className="card" style={{ marginTop: 18 }}>
            <EmptyState
              icon="🏢"
              title="No companies yet"
              description="Load the demo company, or create a business plan to get started."
              action={<button className="btn btn--primary" onClick={() => navigate('/projects/new')}>+ New Business Plan</button>}
            />
          </div>
        ) : (
          companyList.map((company) => {
            const owned = allProjects.filter((p) => p.company_id === company.id)
            return (
              <div key={company.id} className="company-block">
                <CompanyProfileCard
                  company={company}
                  onEdit={() => setEditCompanyId(company.id)}
                  onReloadDemo={company.status === 'demo' ? () => handleLoadDemo(true) : undefined}
                  reloadDisabled={loadDemo.isPending}
                />
                <div className="row row--between" style={{ margin: '22px 2px 12px' }}>
                  <h2 style={{ fontSize: 17 }}><HelpTooltip helpKey="dashboard.overview">Projects</HelpTooltip></h2>
                  <button className="btn btn--secondary btn--sm" onClick={() => addProject(company.id)} disabled={createProject.isPending}>
                    + Create New Project
                  </button>
                </div>
                {owned.length === 0 ? (
                  <div className="card"><EmptyState icon="◫" title="No projects yet"
                    description="Create the first business plan for this company." /></div>
                ) : (
                  <div className="project-grid">
                    {owned.map((p) => (
                      <ProjectCard key={p.id} project={p} onOpen={() => openProject(p.id)} onDelete={() => deleteProject(p)} />
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}

        {ungrouped.length > 0 && (
          <div className="company-block">
            <div className="row row--between" style={{ margin: '28px 2px 12px' }}>
              <h2 style={{ fontSize: 17 }}>Other Plans</h2>
              <span className="muted">{ungrouped.length}</span>
            </div>
            <div className="project-grid">
              {ungrouped.map((p) => (
                <ProjectCard key={p.id} project={p} onOpen={() => openProject(p.id)} onDelete={() => deleteProject(p)} />
              ))}
            </div>
          </div>
        )}
      </div>

      <EditCompanyModal companyId={editCompanyId} open={!!editCompanyId} onClose={() => setEditCompanyId(null)} />
    </div>
  )
}
