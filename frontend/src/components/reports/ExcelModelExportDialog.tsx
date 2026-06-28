import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { downloadFile } from '@/api/client'
import {
  useDeleteExcel,
  useExcelExports,
  useExcelPreview,
  useGenerateExcel,
} from '@/api/excelExportApi'
import type { ExcelExportRequest, ExcelScenario, WorkbookType } from '@/types/excelExport'

const DEFAULT: ExcelExportRequest = {
  scenario: 'base',
  projection_detail: 'annual',
  workbook_type: 'editable',
  include_assumptions: true,
  include_schedules: true,
  include_statements: true,
  include_ratios: true,
  include_scenarios: true,
  include_charts: true,
  include_checks: true,
  include_text_summary: false,
  protect_formulas: true,
}

const SCENARIOS: { value: ExcelScenario; label: string }[] = [
  { value: 'base', label: 'Base Case' },
  { value: 'conservative', label: 'Conservative' },
  { value: 'optimistic', label: 'Optimistic' },
]

const WORKBOOKS: { value: WorkbookType; label: string }[] = [
  { value: 'editable', label: 'Editable Financial Model' },
  { value: 'presentation', label: 'Presentation Workbook' },
  { value: 'full', label: 'Full Detailed Workbook' },
]

function fmtSize(b: number) {
  return b >= 1_000_000 ? `${(b / 1_000_000).toFixed(1)} MB` : `${Math.round(b / 1000)} KB`
}

export function ExcelModelExportDialog({
  projectId,
  open,
  onClose,
}: {
  projectId: string
  open: boolean
  onClose: () => void
}) {
  const { notify } = useToast()
  const [opt, setOpt] = useState<ExcelExportRequest>(DEFAULT)
  const previewQ = useExcelPreview(open ? projectId : undefined, opt.scenario, opt.protect_formulas)
  const exportsQ = useExcelExports(open ? projectId : undefined)
  const generate = useGenerateExcel(projectId)
  const remove = useDeleteExcel(projectId)

  const set = (p: Partial<ExcelExportRequest>) => setOpt((o) => ({ ...o, ...p }))
  const preview = previewQ.data
  const canGenerate = preview?.can_generate ?? false

  const run = () =>
    generate.mutate(opt, {
      onSuccess: (f) => notify(`Excel model generated (${fmtSize(f.file_size)}).`, 'success'),
      onError: (e) => notify((e as Error).message ?? 'Excel generation failed.', 'error'),
    })

  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const download = async (exportId: string, url: string, fileName: string) => {
    setDownloadingId(exportId)
    try {
      await downloadFile(url, fileName)
    } catch (e) {
      notify((e as Error).message || 'Download failed', 'error')
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <Modal
      title="Generate Excel Financial Model"
      open={open}
      onClose={onClose}
      wide
      footer={
        <div className="row" style={{ gap: 8, justifyContent: 'flex-end', width: '100%' }}>
          <button className="btn btn--secondary" onClick={onClose}>Close</button>
          <button className="btn btn--primary" disabled={!canGenerate || generate.isPending} onClick={run}>
            {generate.isPending ? 'Generating…' : '⤓ Generate Excel Model'}
          </button>
        </div>
      }
    >
      <div className="stack--sm">
        <div className="row row--wrap" style={{ gap: 24, alignItems: 'flex-end' }}>
          <div className="field" style={{ minWidth: 180 }}>
            <span className="field__label">Scenario</span>
            <select className="input" value={opt.scenario} onChange={(e) => set({ scenario: e.target.value as ExcelScenario })}>
              {SCENARIOS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 220 }}>
            <span className="field__label">Workbook type</span>
            <select className="input" value={opt.workbook_type} onChange={(e) => set({ workbook_type: e.target.value as WorkbookType })}>
              {WORKBOOKS.map((w) => <option key={w.value} value={w.value}>{w.label}</option>)}
            </select>
          </div>
          <label className="row" style={{ gap: 8, alignItems: 'center', cursor: 'pointer' }}>
            <input type="checkbox" checked={opt.protect_formulas} onChange={(e) => set({ protect_formulas: e.target.checked })} />
            <span style={{ fontSize: 13.5 }}>Protect formula cells</span>
          </label>
        </div>

        <div className="field">
          <span className="field__label">Include</span>
          <div className="row row--wrap" style={{ gap: 16 }}>
            {([
              ['include_schedules', 'Schedules'],
              ['include_statements', 'Statements'],
              ['include_ratios', 'Ratios'],
              ['include_scenarios', 'Scenario comparison'],
              ['include_charts', 'Charts'],
              ['include_checks', 'Validation checks'],
            ] as [keyof ExcelExportRequest, string][]).map(([k, label]) => (
              <label key={k} className="row" style={{ gap: 8, alignItems: 'center', cursor: 'pointer' }}>
                <input type="checkbox" checked={opt[k] as boolean} onChange={(e) => set({ [k]: e.target.checked } as Partial<ExcelExportRequest>)} />
                <span style={{ fontSize: 13.5 }}>{label}</span>
              </label>
            ))}
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
            Detail level: <b>Annual</b> (formula-linked). Monthly detail is on the roadmap.
          </p>
        </div>

        {preview && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, padding: '10px 14px' }}>
            <div style={{ fontSize: 13.5 }}>
              <b>{preview.company_name}</b> — {preview.project_name || 'Untitled project'} · {preview.period_range} · {preview.currency}
            </div>
            <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
              {preview.sheets.length} sheets · live Excel formulas · ~{preview.estimated_size_kb} KB
            </div>
          </div>
        )}
        {preview?.blocking?.map((b) => (
          <div key={b} style={{ background: '#fef2f2', borderLeft: '3px solid #dc2626', color: '#991b1b', padding: '8px 12px', borderRadius: 6, fontSize: 13 }}>{b}</div>
        ))}
        {preview?.warnings?.map((w) => (
          <div key={w} className="muted" style={{ fontSize: 12 }}>⚠ {w}</div>
        ))}

        <div>
          <div className="field__label">Generated workbooks</div>
          {(exportsQ.data ?? []).length === 0 ? (
            <p className="muted" style={{ fontSize: 13 }}>None yet.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>File</th><th>Scenario</th><th style={{ textAlign: 'right' }}>Size</th><th style={{ textAlign: 'right' }}>Actions</th></tr></thead>
                <tbody>
                  {(exportsQ.data ?? []).map((e) => (
                    <tr key={e.export_id}>
                      <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={e.file_name}>
                        {e.file_name}
                      </td>
                      <td><Badge tone="blue">{e.scenario}</Badge></td>
                      <td style={{ textAlign: 'right' }}>{fmtSize(e.file_size)}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="row" style={{ gap: 6, justifyContent: 'flex-end' }}>
                          <button
                            className="btn btn--secondary btn--sm"
                            onClick={() => download(e.export_id, e.download_url, e.file_name)}
                            disabled={downloadingId === e.export_id}
                          >
                            {downloadingId === e.export_id ? '…' : '⤓ Download'}
                          </button>
                          <button className="btn btn--ghost btn--sm" onClick={() => remove.mutate(e.export_id)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <button className="btn btn--ghost btn--sm" disabled title="Coming soon — import revised assumptions from an exported workbook.">
            ⤒ Import Updated Excel Model
          </button>
          <span className="muted" style={{ fontSize: 11.5 }}>Coming soon</span>
        </div>
      </div>
    </Modal>
  )
}
