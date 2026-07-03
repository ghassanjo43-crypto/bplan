import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { ScenarioAssumption } from '@/types'

/** Saved scenarios for a project (named, id-selectable). */
export function useScenarios(projectId: string | undefined) {
  return useQuery({
    queryKey: ['section', projectId, 'scenarios'],
    enabled: !!projectId,
    queryFn: () => api.get<ScenarioAssumption[]>(`/projects/${projectId}/scenarios`),
  })
}

/** Ensure the project has at least a default Base Case; returns the full list. */
export function useEnsureDefaultScenario(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<ScenarioAssumption[]>(`/projects/${projectId}/scenarios/ensure-default`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['section', projectId, 'scenarios'] }),
  })
}

/** Mark one scenario as the project default (clears the others). */
export function useSetDefaultScenario(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scenarioId: string) =>
      api.post<ScenarioAssumption>(`/projects/${projectId}/scenarios/${scenarioId}/default`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['section', projectId, 'scenarios'] }),
  })
}
