import type { ReactNode } from 'react'
import { HelpTooltip } from '@/components/ui/HelpTooltip'

export function PageHeader({
  breadcrumb,
  title,
  subtitle,
  actions,
  helpKey,
}: {
  breadcrumb?: string
  title: string
  subtitle?: string
  actions?: ReactNode
  /** When set and Guided Help is on, the title shows a contextual tooltip. */
  helpKey?: string
}) {
  return (
    <header className="page-header">
      {breadcrumb && <div className="page-header__breadcrumb">{breadcrumb}</div>}
      <div className="page-header__row">
        <div>
          <h1 className="page-header__title">
            {helpKey ? <HelpTooltip helpKey={helpKey}>{title}</HelpTooltip> : title}
          </h1>
          {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
        </div>
        {actions && <div className="row row--wrap">{actions}</div>}
      </div>
    </header>
  )
}
