import { PageHeader } from '@/components/PageHeader'
import { useProjectContext } from '@/layouts/ProjectContext'
import { ReportGeneratorPanel } from '@/components/reports/ReportGeneratorPanel'
import { ExcelModelButton } from '@/components/reports/ExcelModelButton'

export function ReportsPage() {
  const { projectId } = useProjectContext()
  return (
    <>
      <PageHeader
        breadcrumb="Reporting"
        title="Business Plan Report"
        helpKey="reports"
        subtitle="Generate a complete, investor-ready business plan document (Word, PDF) or a live Excel financial model."
        actions={<ExcelModelButton projectId={projectId} className="btn btn--primary" />}
      />
      <ReportGeneratorPanel projectId={projectId} />
    </>
  )
}
