import { useState } from 'react'
import { Controller, useWatch, type Control, type FieldValues } from 'react-hook-form'
import { FormField } from './FormField'
import {
  CurrencyInput,
  DateInput,
  NumberInput,
  PercentageInput,
  SelectInput,
  Switch,
  TextAreaInput,
  TextInput,
} from './inputs'
import type { CardConfig, FieldConfig, FormConfig } from './types'
import { SectionCard } from '@/components/SectionCard'

interface Props {
  config: FormConfig
  control: Control<FieldValues>
  currency: string
  /** When true, render bare (no SectionCard wrappers) — used inside modals. */
  bare?: boolean
}

export function SchemaFields({ config, control, currency, bare }: Props) {
  const values = useWatch({ control }) as Record<string, unknown>

  if (bare) {
    return (
      <div className="form-grid">
        {config.flatMap((card) =>
          card.fields.map((f) => (
            <FieldRenderer key={f.name} field={f} control={control} currency={currency} values={values} />
          )),
        )}
      </div>
    )
  }

  return (
    <div className="stack">
      {config.map((card, i) => (
        <CardBlock key={i} card={card} control={control} currency={currency} values={values} />
      ))}
    </div>
  )
}

function CardBlock({
  card,
  control,
  currency,
  values,
}: {
  card: CardConfig
  control: Control<FieldValues>
  currency: string
  values: Record<string, unknown>
}) {
  const [open, setOpen] = useState(!card.advanced)
  const visibleFields = card.fields.filter((f) => !f.visibleWhen || f.visibleWhen(values))

  if (card.advanced) {
    return (
      <SectionCard title={card.title} subtitle={card.subtitle} icon={card.icon}>
        <button
          type="button"
          className="collapsible__trigger"
          onClick={() => setOpen((o) => !o)}
        >
          <span className={`collapsible__chevron${open ? ' collapsible__chevron--open' : ''}`}>▸</span>
          {open ? 'Hide advanced options' : 'Show advanced options'}
        </button>
        {open && (
          <div className="form-grid" style={{ marginTop: 12 }}>
            {visibleFields.map((f) => (
              <FieldRenderer key={f.name} field={f} control={control} currency={currency} values={values} />
            ))}
          </div>
        )}
      </SectionCard>
    )
  }

  return (
    <SectionCard title={card.title} subtitle={card.subtitle} icon={card.icon}>
      <div className="form-grid">
        {visibleFields.map((f) => (
          <FieldRenderer key={f.name} field={f} control={control} currency={currency} values={values} />
        ))}
      </div>
    </SectionCard>
  )
}

function FieldRenderer({
  field,
  control,
  currency,
  values,
}: {
  field: FieldConfig
  control: Control<FieldValues>
  currency: string
  values: Record<string, unknown>
}) {
  if (field.visibleWhen && !field.visibleWhen(values)) return null

  const disabled = field.disabledWhen ? field.disabledWhen(values) : false

  return (
    <Controller
      name={field.name}
      control={control}
      render={({ field: rhf, fieldState }) => {
        const error = fieldState.error?.message
        const span = field.span ?? (field.kind === 'textarea' ? 2 : 1)
        const hint = disabled ? field.disabledHint ?? field.hint : field.hint

        // Switch/checkbox render inline (label beside control).
        if (field.kind === 'switch' || field.kind === 'checkbox') {
          return (
            <FormField
              label={field.label}
              required={field.required}
              help={field.help}
              hint={hint}
              error={error}
              span={span}
            >
              <div className="row" style={{ gap: 10 }}>
                <Switch checked={!!rhf.value} onChange={rhf.onChange} id={field.name} disabled={disabled} />
                <span className="muted" style={{ fontSize: 13 }}>
                  {rhf.value ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </FormField>
          )
        }

        return (
          <FormField
            label={field.label}
            htmlFor={field.name}
            required={field.required}
            help={field.help}
            hint={hint}
            error={error}
            span={span}
          >
            {renderControl(field, rhf, currency, !!error, disabled)}
          </FormField>
        )
      }}
    />
  )
}

function renderControl(
  field: FieldConfig,
  rhf: { value: unknown; onChange: (v: unknown) => void },
  currency: string,
  error: boolean,
  disabled: boolean,
) {
  const num = (rhf.value ?? null) as number | null
  switch (field.kind) {
    case 'text':
      return (
        <TextInput
          id={field.name}
          value={(rhf.value as string) ?? ''}
          onChange={rhf.onChange}
          placeholder={field.placeholder}
          error={error}
          disabled={disabled}
        />
      )
    case 'textarea':
      return (
        <TextAreaInput
          id={field.name}
          value={(rhf.value as string) ?? ''}
          onChange={rhf.onChange}
          placeholder={field.placeholder}
          error={error}
          disabled={disabled}
        />
      )
    case 'number':
      return (
        <NumberInput
          id={field.name}
          value={num}
          onChange={rhf.onChange}
          placeholder={field.placeholder}
          unit={field.unit}
          allowNegative={field.allowNegative}
          error={error}
          disabled={disabled}
        />
      )
    case 'currency':
      return (
        <CurrencyInput
          id={field.name}
          value={num}
          onChange={rhf.onChange}
          currency={currency}
          placeholder={field.placeholder}
          allowNegative={field.allowNegative}
          error={error}
          disabled={disabled}
        />
      )
    case 'percent':
      return (
        <PercentageInput
          id={field.name}
          value={num}
          onChange={rhf.onChange}
          placeholder={field.placeholder}
          allowNegative={field.allowNegative}
          error={error}
          disabled={disabled}
        />
      )
    case 'date':
      return (
        <DateInput
          id={field.name}
          value={(rhf.value as string) ?? null}
          onChange={rhf.onChange}
          error={error}
          disabled={disabled}
        />
      )
    case 'select':
      return (
        <SelectInput
          id={field.name}
          value={(rhf.value as string) ?? null}
          onChange={rhf.onChange}
          options={field.options ?? []}
          placeholder={field.placeholder}
          error={error}
          disabled={disabled}
        />
      )
    default:
      return null
  }
}
