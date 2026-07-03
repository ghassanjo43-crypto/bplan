/* Financial Analysis API hooks. */
import { useQuery } from '@tanstack/react-query'
import { api } from './client'
import type {
  FinancialAnalysisResponse,
  ScenarioComparisonResponse,
  ScenarioKey,
  FAView,
} from '@/types/financialAnalysis'

export function useFinancialAnalysis(projectId: string | undefined, scenario: ScenarioKey, view: FAView) {
  return useQuery({
    queryKey: ['financial-analysis', projectId, scenario, view],
    queryFn: () => api.get<FinancialAnalysisResponse>(`/projects/${projectId}/financial-analysis?scenario=${scenario}&view=${view}`),
    enabled: !!projectId,
    retry: 2,
  })
}

export function useScenarioComparison(
  projectId: string | undefined,
  view: FAView,
  scenarioIds?: string[],
) {
  const ids = scenarioIds?.filter(Boolean) ?? []
  const idsParam = ids.length ? `&scenarios=${ids.join(',')}` : ''
  return useQuery({
    queryKey: ['scenario-comparison', projectId, view, ids.join(',')],
    queryFn: () => api.get<ScenarioComparisonResponse>(
      `/projects/${projectId}/financial-analysis/scenario-comparison?view=${view}${idsParam}`),
    enabled: !!projectId,
    retry: 2,
  })
}
