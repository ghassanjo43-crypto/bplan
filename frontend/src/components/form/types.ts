import type { Option } from '@/utils/options'

export type FieldKind =
  | 'text'
  | 'textarea'
  | 'number'
  | 'currency'
  | 'percent'
  | 'date'
  | 'select'
  | 'switch'
  | 'checkbox'
  | 'computed'

export interface FieldConfig {
  name: string
  label: string
  kind: FieldKind
  /** Plain-English tooltip explaining a financial term. */
  help?: string
  placeholder?: string
  /** Required for `select`. */
  options?: Option[]
  min?: number
  max?: number
  step?: number
  /** Pre-filled value for new items (and for legacy rows missing this field). */
  defaultValue?: string | number | boolean
  required?: boolean
  /** Conditionally required based on current form values (e.g. custom payment
   *  days only when payment terms = custom). Drives both the asterisk and the
   *  validation rule. */
  requiredWhen?: (values: Record<string, unknown>) => boolean
  /** Cross-field validation. Return an error message to fail, or undefined to
   *  pass (e.g. end date must not precede start date). */
  validateWith?: (value: unknown, values: Record<string, unknown>) => string | undefined
  /** For kind 'computed': derive a read-only display value from current values
   *  (e.g. contract end date = start + duration). Not stored or submitted. */
  compute?: (values: Record<string, unknown>) => string
  /** Static helper text under the field. */
  hint?: string
  /** Grid span (default 1). */
  span?: 1 | 2
  /** Allow negative numbers (growth/adjustment fields). */
  allowNegative?: boolean
  /** Conditional visibility based on current form values. */
  visibleWhen?: (values: Record<string, unknown>) => boolean
  /** Conditionally disable (grey out) the field based on current form values. */
  disabledWhen?: (values: Record<string, unknown>) => boolean
  /** Helper text shown under the field while it is disabled. */
  disabledHint?: string
  /** Currency-style display unit override (e.g. for "days"). */
  unit?: string
}

export interface CardConfig {
  title: string
  subtitle?: string
  icon?: string
  fields: FieldConfig[]
  /** Render inside a collapsible "Advanced" section, collapsed by default. */
  advanced?: boolean
}

export type FormConfig = CardConfig[]

/** Flatten every field across all cards (used for validation + defaults). */
export function allFields(config: FormConfig): FieldConfig[] {
  return config.flatMap((c) => c.fields)
}
