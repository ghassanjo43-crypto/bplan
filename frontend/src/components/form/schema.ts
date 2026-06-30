import { z } from 'zod'
import type { FieldConfig, FormConfig } from './types'
import { allFields } from './types'

/** Build a Zod schema from a form config so validation lives next to the UI. */
export function buildZodSchema(config: FormConfig): z.ZodTypeAny {
  const shape: Record<string, z.ZodTypeAny> = {}

  for (const f of allFields(config)) {
    if (f.kind === 'computed') continue // display-only, not a form value
    shape[f.name] = fieldSchema(f)
  }
  const base = z.object(shape)

  // Conditionally-required (requiredWhen) and cross-field (validateWith) checks
  // run at submit time against the current values, so the rules and the
  // asterisks always agree.
  const fields = allFields(config)
  const conditional = fields.filter((f) => f.requiredWhen)
  const crossField = fields.filter((f) => f.validateWith)
  if (conditional.length === 0 && crossField.length === 0) return base
  return base.superRefine((values: Record<string, unknown>, ctx) => {
    for (const f of conditional) {
      if (!f.requiredWhen!(values)) continue
      const v = values[f.name]
      const empty =
        v === null || v === undefined || v === '' || (typeof v === 'number' && Number.isNaN(v))
      if (empty) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: [f.name], message: 'This field is required' })
      }
    }
    for (const f of crossField) {
      const message = f.validateWith!(values[f.name], values)
      if (message) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: [f.name], message })
      }
    }
  })
}

function fieldSchema(f: FieldConfig): z.ZodTypeAny {
  switch (f.kind) {
    case 'text':
    case 'textarea': {
      if (f.required) return z.string().trim().min(1, 'This field is required')
      return z.string().nullish()
    }
    case 'select': {
      if (f.required) return z.string().min(1, 'Please select an option')
      return z.string().nullish()
    }
    case 'date': {
      if (f.required) return z.string().min(1, 'Please choose a date')
      return z.string().nullish()
    }
    case 'switch':
    case 'checkbox':
      return z.boolean()
    case 'number':
    case 'currency':
    case 'percent': {
      let base = z.number({ invalid_type_error: 'Enter a number', required_error: 'Required' })
      const min = f.min ?? (f.allowNegative ? undefined : 0)
      if (min !== undefined) base = base.gte(min, `Must be ${min} or more`)
      const max = f.max ?? (f.kind === 'percent' ? 100 : undefined)
      if (max !== undefined) base = base.lte(max, `Must be ${max} or less`)
      return f.required ? base : base.nullish()
    }
    default:
      return z.any()
  }
}

/** Sensible empty defaults for a config (used when creating new items). */
export function defaultsFromConfig(config: FormConfig): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const f of allFields(config)) {
    if (f.kind === 'computed') continue // display-only, not a form value
    if (f.defaultValue !== undefined) {
      out[f.name] = f.defaultValue
      continue
    }
    switch (f.kind) {
      case 'switch':
      case 'checkbox':
        out[f.name] = false
        break
      case 'number':
      case 'currency':
      case 'percent':
        out[f.name] = f.required ? 0 : null
        break
      default:
        out[f.name] = f.required ? '' : null
    }
  }
  return out
}
