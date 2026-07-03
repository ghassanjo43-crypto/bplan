import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { RevenueStreamForecast } from '@/types'

/** Computed per-stream + total revenue (monthly or annual) for the wizard preview. */
export function useRevenueStreamsForecast(projectId: string | undefined, view: 'monthly' | 'yearly') {
  return useQuery({
    queryKey: ['revenue-streams-forecast', projectId, view],
    enabled: !!projectId,
    queryFn: () => api.get<RevenueStreamForecast>(`/projects/${projectId}/revenue-streams-forecast?view=${view}`),
  })
}

/**
 * Returns a function that refreshes everything a revenue-stream change affects:
 * the forecast totals and the downstream financial statements (income
 * statement, cash flow, balance sheet, analysis). The generic section write
 * only invalidates the section list, so these computed views need an explicit
 * nudge to update automatically after create / edit / delete.
 */
export function useRefreshRevenueDependents(projectId: string | undefined) {
  const qc = useQueryClient()
  return () => {
    if (!projectId) return
    for (const key of [
      'revenue-streams-forecast',
      'income-statement',
      'income-statement-summary',
      'income-statement-recon',
      'cash-flow',
      'balance-sheet',
      'financial-analysis',
    ]) {
      qc.invalidateQueries({ queryKey: [key, projectId] })
    }
  }
}
