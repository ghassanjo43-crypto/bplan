import { NavLink, useParams } from 'react-router-dom'
import { NAV_GROUPS, NAV_PAGES } from '@/routes/nav'
import { useProjectContext } from './ProjectContext'

export function Sidebar() {
  const { projectId } = useParams()
  const { isSectionComplete, completion } = useProjectContext()

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">B</div>
        <div>
          <div className="sidebar__title">Business Plan Studio</div>
          <div className="sidebar__subtitle">Financial Projection Suite</div>
        </div>
      </div>

      {NAV_GROUPS.map((group) => {
        const pages = NAV_PAGES.filter((p) => p.group === group)
        return (
          <div className="sidebar__section" key={group}>
            <div className="sidebar__section-label">{group}</div>
            <nav className="sidebar__nav">
              {pages.map((page) => {
                const done = page.sectionKey ? isSectionComplete(page.sectionKey) : false
                const index = NAV_PAGES.indexOf(page) + 1
                return (
                  <NavLink
                    key={page.slug}
                    to={`/projects/${projectId}/${page.slug}`}
                    className={({ isActive }) =>
                      `nav-item${isActive ? ' nav-item--active' : ''}${done ? ' nav-item--done' : ''}`
                    }
                  >
                    <span className="nav-item__index">{done ? '✓' : index}</span>
                    <span className="nav-item__label">{page.label}</span>
                  </NavLink>
                )
              })}
            </nav>
          </div>
        )
      })}

      <div className="sidebar__footer">
        <NavLink to="/projects" className="nav-item">
          <span className="nav-item__index">←</span>
          <span className="nav-item__label">All Projects</span>
        </NavLink>
        <NavLink to="/guide" className="nav-item">
          <span className="nav-item__index">?</span>
          <span className="nav-item__label">User Guide</span>
        </NavLink>
        {completion && (
          <div className="muted" style={{ fontSize: 11.5, padding: '8px 11px 0', color: 'var(--slate-500)' }}>
            {completion.completed_sections} of {completion.total_sections} sections complete
          </div>
        )}
      </div>
    </aside>
  )
}
