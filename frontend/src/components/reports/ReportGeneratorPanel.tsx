import { useState } from 'react'
import { SectionCard } from '@/components/SectionCard'
import { LoadingScreen } from '@/components/ui/Spinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { ReportOptionsForm } from './ReportOptionsForm'
import { ReportPreviewPanel } from './ReportPreviewPanel'
import { GeneratedReportsTable } from './GeneratedReportsTable'
import {
  useDeleteReport,
  useGenerateReport,
  useGeneratedReports,
  useReportPreview,
} from '@/api/reportsApi'
import type { ReportRequest } from '@/types/reports'

const DEFAULT_REQUEST: ReportRequest = {
  scenario: 'base',
  view: 'yearly',
  report_style: 'investor',
  include_charts: true,
  include_appendices: true,
  include_assumptions: true,
  include_warnings: true,
  output_format: 'docx',
  include_text_plan: true,
  text_plan_include_completed: true,
  text_plan_include_drafts: true,
  text_plan_include_images: true,
  text_plan_include_guidance: false,
}

export function ReportGeneratorPanel({ projectId }: { projectId: string }) {
  const { notify } = useToast()
  const [options, setOptions] = useState<ReportRequest>(DEFAULT_REQUEST)

  const previewQ = useReportPreview(projectId, options.scenario, options.view, options.report_style)
  const reportsQ = useGeneratedReports(projectId)
  const generate = useGenerateReport(projectId)
  const remove = useDeleteReport(projectId)

  const canGenerate = previewQ.data?.can_generate ?? false

  const run = (format: 'docx' | 'pdf') => {
    generate.mutate(
      { ...options, output_format: format },
      {
        onSuccess: (file) => {
          if (file.format === 'html') {
            notify('PDF engine unavailable — a print-ready HTML report was generated instead.', 'success')
          } else {
            notify(`${file.format.toUpperCase()} report generated.`, 'success')
          }
        },
        onError: (e) => notify((e as Error).message ?? 'Report generation failed.', 'error'),
      },
    )
  }

  const onDelete = (reportId: string) =>
    remove.mutate(reportId, {
      onSuccess: () => notify('Report deleted.', 'success'),
      onError: (e) => notify((e as Error).message ?? 'Delete failed.', 'error'),
    })

  return (
    <div className="stack">
      <SectionCard
        title="Report options"
        subtitle="Choose the scenario, level of detail, and audience for the business plan report."
        icon="⚙"
      >
        <ReportOptionsForm value={options} onChange={setOptions} projectId={projectId} />
      </SectionCard>

      <SectionCard title="Report preview" subtitle="What the generated document will contain." icon="◳">
        {previewQ.isLoading ? (
          <LoadingScreen label="Building the report preview…" />
        ) : previewQ.isError || !previewQ.data ? (
          <EmptyState
            icon="⚠"
            title="Could not build the preview"
            description={(previewQ.error as Error)?.message ?? 'Ensure the project setup and products are defined.'}
          />
        ) : (
          <ReportPreviewPanel preview={previewQ.data} />
        )}
      </SectionCard>

      <SectionCard
        title="Generate"
        subtitle="Word uses a fully formatted .docx; PDF is rendered from print CSS (falls back to HTML if the PDF engine is unavailable)."
        icon="⤓"
        actions={
          <div className="row" style={{ gap: 8 }}>
            <button
              className="btn btn--primary"
              disabled={!canGenerate || generate.isPending}
              onClick={() => run('docx')}
            >
              {generate.isPending && generate.variables?.output_format === 'docx' ? 'Generating…' : '⤓ Generate Word'}
            </button>
            <button
              className="btn btn--secondary"
              disabled={!canGenerate || generate.isPending}
              onClick={() => run('pdf')}
            >
              {generate.isPending && generate.variables?.output_format === 'pdf' ? 'Generating…' : '⤓ Generate PDF'}
            </button>
          </div>
        }
      >
        {!canGenerate && (
          <p className="muted" style={{ fontSize: 13.5 }}>
            Complete the blocking items shown in the preview before generating a report.
          </p>
        )}
        {reportsQ.isLoading ? (
          <LoadingScreen label="Loading generated reports…" />
        ) : (
          <GeneratedReportsTable
            reports={reportsQ.data ?? []}
            onDelete={onDelete}
            deletingId={remove.isPending ? (remove.variables as string) : null}
          />
        )}
      </SectionCard>
    </div>
  )
}
