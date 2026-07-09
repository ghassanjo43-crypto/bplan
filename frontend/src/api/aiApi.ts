/* AI narrative generation API hook. */
import { useMutation } from '@tanstack/react-query'
import { api } from './client'
import type { AiGenerateRequest, AiGenerateResponse } from '@/types/ai'

const base = (projectId: string) => `/projects/${projectId}/ai`

/** Generate narrative text for a section. The API key stays on the backend. */
export function useGenerateSection(projectId: string) {
  return useMutation<AiGenerateResponse, Error, AiGenerateRequest>({
    mutationFn: (body: AiGenerateRequest) =>
      api.post<AiGenerateResponse>(`${base(projectId)}/generate-section`, body),
  })
}
