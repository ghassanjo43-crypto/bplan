import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { CreateUserInput, ManagedUser, TrialSettingsInput, UpdateUserInput } from '@/types/auth'

export function useUsers() {
  return useQuery({ queryKey: ['admin-users'], queryFn: () => api.get<ManagedUser[]>('/admin/users') })
}

function useInvalidate() {
  const qc = useQueryClient()
  return () => qc.invalidateQueries({ queryKey: ['admin-users'] })
}

export function useCreateUser() {
  const invalidate = useInvalidate()
  return useMutation({ mutationFn: (body: CreateUserInput) => api.post<ManagedUser>('/admin/users', body), onSuccess: invalidate })
}

export function useUpdateUser() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateUserInput }) =>
      api.put<ManagedUser>(`/admin/users/${id}`, body),
    onSuccess: invalidate,
  })
}

export function useSetUserActive() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api.post<ManagedUser>(`/admin/users/${id}/${active ? 'enable' : 'disable'}`),
    onSuccess: invalidate,
  })
}

export function useAssignCompany() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, company_id }: { id: string; company_id: string | null }) =>
      api.put<ManagedUser>(`/admin/users/${id}/company-assignment`, { company_id }),
    onSuccess: invalidate,
  })
}

export function useResetUserPassword() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.post<{ user: ManagedUser; temporary_password: string }>(
      `/admin/users/${id}/reset-password`, { confirm: true },
    ),
    onSuccess: invalidate,
  })
}

export function useDeleteUser() {
  const invalidate = useInvalidate()
  return useMutation({ mutationFn: (id: string) => api.delete<void>(`/admin/users/${id}`), onSuccess: invalidate })
}

export function useSetTrial() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TrialSettingsInput }) =>
      api.put<ManagedUser>(`/admin/users/${id}/trial`, body),
    onSuccess: invalidate,
  })
}

export function useExtendTrial() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: ({ id, additional_days }: { id: string; additional_days: number }) =>
      api.post<ManagedUser>(`/admin/users/${id}/trial/extend`, { additional_days }),
    onSuccess: invalidate,
  })
}

export function useEndTrial() {
  const invalidate = useInvalidate()
  return useMutation({
    mutationFn: (id: string) => api.post<ManagedUser>(`/admin/users/${id}/trial/end`),
    onSuccess: invalidate,
  })
}
