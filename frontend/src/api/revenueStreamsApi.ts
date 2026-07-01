import { useQuery } from '@tanstack/react-query'
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
