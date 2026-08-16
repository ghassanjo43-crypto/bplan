import { api, setTokens, clearTokens } from './client'
import type { AuthUser } from '@/types/auth'

export async function loginRequest(email: string, password: string) {
  const data = await api.post<{ user: AuthUser; access_token?: string; refresh_token?: string }>(
    '/auth/login',
    { email, password },
  )
  setTokens(data.access_token, data.refresh_token)
  return data
}

export async function logoutRequest() {
  try {
    return await api.post<{ message: string }>('/auth/logout')
  } finally {
    clearTokens()
  }
}

export function meRequest() {
  return api.get<AuthUser>('/auth/me')
}

export async function changePasswordRequest(current_password: string, new_password: string) {
  const data = await api.post<{ user: AuthUser; access_token?: string; refresh_token?: string }>(
    '/auth/change-password', { current_password, new_password },
  )
  setTokens(data.access_token, data.refresh_token)
  return data
}
