export type Role = 'admin' | 'user'
export type AccountStatus = 'active' | 'trial' | 'expired' | 'suspended'

export interface AuthUser {
  id: string
  email: string
  username?: string | null
  full_name: string
  role: Role
  company_id: string | null
  is_active: boolean
  must_change_password: boolean
  last_login_at?: string | null
  created_at: string
  updated_at: string
  // Admin-managed trial period (account_status / days_remaining are derived).
  trial_enabled?: boolean
  trial_start_date?: string | null
  trial_end_date?: string | null
  trial_days?: number | null
  account_status?: AccountStatus
  days_remaining?: number | null
}

export interface ManagedUser extends AuthUser {}

export interface CreateUserInput {
  email: string
  full_name: string
  role: Role
  company_id: string | null
  temporary_password: string
  must_change_password: boolean
  trial_enabled?: boolean
  trial_days?: number | null
  trial_start_date?: string | null
}

export interface TrialSettingsInput {
  enabled: boolean
  trial_days?: number | null
  trial_start_date?: string | null
}
