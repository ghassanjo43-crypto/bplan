import { useMemo } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '@/components/ui/Modal'
import { SectionCard } from '@/components/SectionCard'
import { FormField } from '@/components/form/FormField'
import {
  CurrencyInput,
  DateInput,
  NumberInput,
  PercentageInput,
  SelectInput,
  Switch,
  TextAreaInput,
  TextInput,
} from '@/components/form/inputs'
import {
  costAllocationMethodOptions,
  costBehaviorOptions,
  costCalculationMethodOptions,
  currencyOptions,
  directCostCategoryOptions,
  paymentTermsOptions,
  PERCENT_METHODS,
} from '@/utils/options'
import type {
  CostCalculationMethod,
  DirectCostItem,
} from '@/types'
import { deriveMode, type Associable, type AssociationMode } from '@/utils/directCosts'
import { formatPercent } from '@/utils/format'

type Form = {
  name: string
  category: string
  cost_behavior: string
  association_mode: AssociationMode
  product_ids: string[]
  calculation_method: string
  amount: number | null
  percent: number | null
  allocation_method: string | null
  manual_allocations: { product_id: string; percent: number }[]
  supplier_name: string | null
  supplier_payment_terms: string
  cost_inflation_rate: number | null
  waste_defect_rate_percent: number | null
  minimum_order_quantity: number | null
  currency_override: string | null
  vat_applicable: boolean
  start_date: string | null
  end_date: string | null
  active: boolean
  notes: string | null
}

const schema = z
  .object({
    name: z.string().trim().min(1, 'Cost item name is required'),
    category: z.string().min(1, 'Category is required'),
    cost_behavior: z.string(),
    association_mode: z.enum(['one', 'multiple', 'all', 'unassigned']),
    product_ids: z.array(z.string()),
    calculation_method: z.string().min(1, 'Calculation method is required'),
    amount: z.number().nullable(),
    percent: z.number().nullable(),
    allocation_method: z.string().nullable(),
    manual_allocations: z.array(z.object({ product_id: z.string(), percent: z.number() })),
    supplier_name: z.string().nullish(),
    supplier_payment_terms: z.string(),
    cost_inflation_rate: z.number().nullable(),
    waste_defect_rate_percent: z.number().nullable(),
    minimum_order_quantity: z.number().nullable(),
    currency_override: z.string().nullish(),
    vat_applicable: z.boolean(),
    // Optional — blank means "follow the linked product's launch date".
    start_date: z.string().nullish(),
    end_date: z.string().nullish(),
    active: z.boolean(),
    notes: z.string().nullish(),
  })
  .superRefine((v, ctx) => {
    const isPercent = PERCENT_METHODS.includes(v.calculation_method as CostCalculationMethod)
    const isManual = v.calculation_method === 'manual_by_period'
    if (isPercent) {
      if (v.percent == null) ctx.addIssue({ code: 'custom', path: ['percent'], message: 'Enter a percentage' })
      else if (v.percent < 0 || v.percent > 100)
        ctx.addIssue({ code: 'custom', path: ['percent'], message: 'Must be between 0 and 100' })
    } else if (!isManual) {
      // Manual-by-period amounts are entered per month in the projection grid,
      // so no single amount is required here.
      if (v.amount == null) ctx.addIssue({ code: 'custom', path: ['amount'], message: 'Enter an amount' })
      else if (v.amount < 0) ctx.addIssue({ code: 'custom', path: ['amount'], message: 'Must be 0 or positive' })
    }
    if (v.association_mode === 'one' && v.product_ids.length !== 1)
      ctx.addIssue({ code: 'custom', path: ['product_ids'], message: 'Select a revenue stream' })
    if (v.association_mode === 'multiple' && v.product_ids.length < 1)
      ctx.addIssue({ code: 'custom', path: ['product_ids'], message: 'Select at least one revenue stream' })

    const spans = v.association_mode === 'all' || (v.association_mode === 'multiple' && v.product_ids.length > 1)
    if (spans && !v.allocation_method)
      ctx.addIssue({ code: 'custom', path: ['allocation_method'], message: 'Allocation method is required' })
    if (v.allocation_method === 'manual') {
      const sum = v.manual_allocations.reduce((s, a) => s + (a.percent || 0), 0)
      if (Math.abs(sum - 100) > 0.01)
        ctx.addIssue({ code: 'custom', path: ['manual_allocations'], message: `Allocations must total 100% (now ${sum}%)` })
    }
    // One-time direct costs land in a single month, so they need a date.
    if (v.calculation_method === 'one_time' && !v.start_date)
      ctx.addIssue({ code: 'custom', path: ['start_date'], message: 'One-time direct costs need a start date (the month they are incurred).' })
  })

export type DirectCostPrefill = Partial<Pick<Form, 'name' | 'category' | 'calculation_method' | 'cost_behavior'>>

function toForm(item: DirectCostItem | null, prefill?: DirectCostPrefill): Form {
  if (item) {
    return {
      name: item.name,
      category: item.category,
      cost_behavior: item.cost_behavior,
      association_mode: deriveMode(item),
      product_ids: item.product_ids,
      calculation_method: item.calculation_method,
      amount: item.amount,
      percent: item.percent,
      allocation_method: item.allocation_method ?? null,
      manual_allocations: item.manual_allocations ?? [],
      supplier_name: item.supplier_name ?? null,
      supplier_payment_terms: item.supplier_payment_terms,
      cost_inflation_rate: item.cost_inflation_rate,
      waste_defect_rate_percent: item.waste_defect_rate_percent,
      minimum_order_quantity: item.minimum_order_quantity ?? null,
      currency_override: item.currency_override ?? null,
      vat_applicable: item.vat_applicable,
      start_date: item.start_date ?? '',
      end_date: item.end_date ?? null,
      active: item.active,
      notes: item.notes ?? null,
    }
  }
  return {
    name: '',
    category: 'other',
    cost_behavior: 'variable',
    association_mode: 'one',
    product_ids: [],
    calculation_method: 'fixed_per_unit',
    amount: null,
    percent: null,
    allocation_method: null,
    manual_allocations: [],
    supplier_name: null,
    supplier_payment_terms: 'net_30',
    cost_inflation_rate: 0,
    waste_defect_rate_percent: 0,
    minimum_order_quantity: null,
    currency_override: null,
    vat_applicable: false,
    start_date: '',
    end_date: null,
    active: true,
    notes: null,
    ...prefill,
  }
}

const MODE_OPTIONS: { value: AssociationMode; label: string }[] = [
  { value: 'one', label: 'One revenue stream' },
  { value: 'multiple', label: 'Multiple' },
  { value: 'all', label: 'All revenue streams' },
  { value: 'unassigned', label: 'Independent / unassigned' },
]

export function DirectCostModal({
  open,
  item,
  prefill,
  associations,
  currency,
  onClose,
  onSubmit,
  saving,
}: {
  open: boolean
  item: DirectCostItem | null
  prefill?: DirectCostPrefill
  associations: Associable[]
  currency: string
  onClose: () => void
  onSubmit: (payload: Partial<DirectCostItem>) => void
  saving?: boolean
}) {
  const form = useForm<Form>({
    resolver: zodResolver(schema) as never,
    defaultValues: toForm(item, prefill),
  })
  const { control, handleSubmit, watch, setValue, formState } = form

  const mode = watch('association_mode')
  const productIds = watch('product_ids')
  const method = watch('calculation_method') as CostCalculationMethod
  const allocationMethod = watch('allocation_method')
  const manual = watch('manual_allocations')
  const isPercent = PERCENT_METHODS.includes(method)
  const spans = mode === 'all' || (mode === 'multiple' && productIds.length > 1)

  const targetAssoc = useMemo(
    () => (mode === 'all' ? associations : associations.filter((a) => productIds.includes(a.id))),
    [mode, productIds, associations],
  )

  if (!open) return null

  const setManual = (assocId: string, percent: number) => {
    const next = targetAssoc.map((a) => ({
      product_id: a.id,
      percent: a.id === assocId ? percent : manual.find((m) => m.product_id === a.id)?.percent ?? 0,
    }))
    setValue('manual_allocations', next, { shouldValidate: true })
  }
  const distributeEvenly = () => {
    const each = targetAssoc.length ? Math.round((100 / targetAssoc.length) * 100) / 100 : 0
    setValue(
      'manual_allocations',
      targetAssoc.map((a) => ({ product_id: a.id, percent: each })),
      { shouldValidate: true },
    )
  }
  const manualSum = manual.reduce((s, a) => s + (a.percent || 0), 0)

  const submit = handleSubmit((v) => {
    const apply_to_all = v.association_mode === 'all'
    const product_ids = apply_to_all || v.association_mode === 'unassigned' ? [] : v.product_ids
    const payload: Partial<DirectCostItem> = {
      name: v.name.trim(),
      category: v.category as DirectCostItem['category'],
      apply_to_all,
      product_ids,
      cost_behavior: v.cost_behavior as DirectCostItem['cost_behavior'],
      calculation_method: v.calculation_method as CostCalculationMethod,
      amount: isPercent ? 0 : v.amount ?? 0,
      percent: isPercent ? v.percent ?? 0 : 0,
      allocation_method: spans ? (v.allocation_method as DirectCostItem['allocation_method']) : null,
      manual_allocations:
        spans && v.allocation_method === 'manual'
          ? targetAssoc.map((a) => ({
              product_id: a.id,
              percent: v.manual_allocations.find((m) => m.product_id === a.id)?.percent ?? 0,
            }))
          : [],
      supplier_name: v.supplier_name || null,
      supplier_payment_terms: v.supplier_payment_terms as DirectCostItem['supplier_payment_terms'],
      cost_inflation_rate: v.cost_inflation_rate ?? 0,
      waste_defect_rate_percent: v.waste_defect_rate_percent ?? 0,
      minimum_order_quantity: v.minimum_order_quantity,
      currency_override: v.currency_override || null,
      vat_applicable: v.vat_applicable,
      start_date: v.start_date || null,
      end_date: v.end_date || null,
      active: v.active,
      notes: v.notes || null,
    }
    onSubmit(payload)
  })

  const err = formState.errors

  return (
    <Modal
      open={open}
      wide
      title={item ? 'Edit Direct Cost Item' : 'Add Direct Cost Item'}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn--ghost" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="btn btn--primary" type="button" onClick={submit} disabled={saving}>
            {saving ? 'Saving…' : 'Save Cost Item'}
          </button>
        </>
      }
    >
      <div className="stack">
        {/* Details */}
        <SectionCard title="Item Details" icon="◵">
          <div className="form-grid">
            <Controller control={control} name="name" render={({ field }) => (
              <FormField label="Direct Cost Item Name" required span={2} error={err.name?.message}>
                <TextInput value={field.value} onChange={field.onChange} placeholder="e.g. Raw material — steel" error={!!err.name} />
              </FormField>
            )} />
            <Controller control={control} name="category" render={({ field }) => (
              <FormField label="Cost Category" required error={err.category?.message}>
                <SelectInput value={field.value} onChange={field.onChange} options={directCostCategoryOptions} error={!!err.category} />
              </FormField>
            )} />
            <Controller control={control} name="cost_behavior" render={({ field }) => (
              <FormField label="Cost Behavior" help="Variable scales with volume; direct-fixed stays constant per period.">
                <SelectInput value={field.value} onChange={field.onChange} options={costBehaviorOptions} />
              </FormField>
            )} />
          </div>
        </SectionCard>

        {/* Association */}
        <SectionCard title="Associated Revenue Stream" subtitle="Linked direct costs are driven by their revenue stream’s forecast quantity or revenue. Choose “Independent / unassigned” for a cost that isn’t tied to a specific stream (it stays out of cost of sales until assigned)." icon="◫">
          <Controller control={control} name="association_mode" render={({ field }) => (
            <div className="segmented" style={{ marginBottom: targetAssoc.length || mode === 'multiple' || mode === 'one' ? 16 : 0 }}>
              {MODE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  className={`segmented__btn${field.value === o.value ? ' segmented__btn--active' : ''}`}
                  onClick={() => {
                    field.onChange(o.value)
                    setValue('product_ids', [])
                    setValue('allocation_method', null)
                    setValue('manual_allocations', [])
                  }}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )} />

          {mode === 'one' && (
            <Controller control={control} name="product_ids" render={({ field }) => (
              <FormField label="Revenue Stream" required error={err.product_ids?.message as string | undefined}>
                <SelectInput
                  value={field.value[0] ?? null}
                  onChange={(v) => field.onChange(v ? [v] : [])}
                  options={associations.map((a) => ({ value: a.id, label: a.name }))}
                  error={!!err.product_ids}
                  placeholder={associations.length ? 'Select a revenue stream' : 'Add a revenue stream first'}
                />
              </FormField>
            )} />
          )}

          {mode === 'multiple' && (
            <Controller control={control} name="product_ids" render={({ field }) => (
              <FormField label="Revenue Streams" required error={err.product_ids?.message as string | undefined}>
                <div className="check-list">
                  {associations.length === 0 && <span className="muted">Add a revenue stream first.</span>}
                  {associations.map((a) => {
                    const checked = field.value.includes(a.id)
                    return (
                      <label key={a.id} className="check-list__item">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) =>
                            field.onChange(
                              e.target.checked ? [...field.value, a.id] : field.value.filter((id) => id !== a.id),
                            )
                          }
                        />
                        {a.name}
                      </label>
                    )
                  })}
                </div>
              </FormField>
            )} />
          )}

          {mode === 'unassigned' && (
            <div className="banner banner--warning">
              <span className="banner__icon">⚠</span>
              <div>This cost is <strong>independent / unassigned</strong> — not linked to any revenue stream, so it is excluded from cost of sales until you assign it. For a general overhead, consider Operating Expenses instead.</div>
            </div>
          )}
        </SectionCard>

        {/* Method & value */}
        <SectionCard title="Cost Calculation" icon="◷">
          <div className="form-grid">
            <Controller control={control} name="calculation_method" render={({ field }) => (
              <FormField label="Calculation Method" required span={2} error={err.calculation_method?.message}>
                <SelectInput value={field.value} onChange={field.onChange} options={costCalculationMethodOptions} error={!!err.calculation_method} />
              </FormField>
            )} />
            {isPercent ? (
              <Controller control={control} name="percent" render={({ field }) => (
                <FormField label="Cost Percentage" required error={err.percent?.message} help="Percentage applied to revenue or selling price.">
                  <PercentageInput value={field.value} onChange={field.onChange} error={!!err.percent} />
                </FormField>
              )} />
            ) : method === 'manual_by_period' ? null : (
              <Controller control={control} name="amount" render={({ field }) => (
                <FormField label="Cost Amount" required error={err.amount?.message}>
                  <CurrencyInput value={field.value} onChange={field.onChange} currency={watch('currency_override') || currency} error={!!err.amount} />
                </FormField>
              )} />
            )}
          </div>
          {method === 'manual_by_period' && (
            <div className="banner banner--info" style={{ marginTop: 8 }}>
              <span className="banner__icon">ℹ</span>
              <div>Manual by period: enter the cost for each month directly in the Direct Costs projection grid. At least one month must have an amount for this cost to appear.</div>
            </div>
          )}
        </SectionCard>

        {/* Allocation */}
        {spans && (
          <SectionCard title="Allocation" subtitle="How a shared cost is split across the selected products/services." icon="⊟">
            <div className="form-grid">
              <Controller control={control} name="allocation_method" render={({ field }) => (
                <FormField label="Allocation Method" required span={2} error={err.allocation_method?.message as string | undefined}>
                  <SelectInput value={field.value} onChange={field.onChange} options={costAllocationMethodOptions} error={!!err.allocation_method} placeholder="Select allocation method" />
                </FormField>
              )} />
            </div>

            {allocationMethod === 'manual' && (
              <div style={{ marginTop: 8 }}>
                <div className="row row--between" style={{ marginBottom: 10 }}>
                  <span className="field__label">Manual allocation by product</span>
                  <button type="button" className="btn btn--ghost btn--sm" onClick={distributeEvenly}>
                    Distribute evenly
                  </button>
                </div>
                <div className="stack--sm">
                  {targetAssoc.map((a) => (
                    <div key={a.id} className="alloc-row">
                      <span>{a.name}</span>
                      <div style={{ width: 130 }}>
                        <div className="field__control">
                          <PercentageInput
                            value={manual.find((m) => m.product_id === a.id)?.percent ?? 0}
                            onChange={(v) => setManual(a.id, v ?? 0)}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="row row--between" style={{ marginTop: 10 }}>
                  <span className={`badge ${Math.abs(manualSum - 100) < 0.01 ? 'badge--green' : 'badge--amber'}`}>
                    Total: {formatPercent(manualSum)}
                  </span>
                  {err.manual_allocations && (
                    <span className="field__error">⚠ {err.manual_allocations.message as string}</span>
                  )}
                </div>
              </div>
            )}
          </SectionCard>
        )}

        {/* Advanced */}
        <SectionCard title="Supplier, Tax & Lifecycle" icon="⊞">
          <div className="form-grid">
            <Controller control={control} name="supplier_name" render={({ field }) => (
              <FormField label="Supplier (optional)">
                <TextInput value={field.value ?? ''} onChange={(v) => field.onChange(v || null)} placeholder="e.g. Acme Supplies" />
              </FormField>
            )} />
            <Controller control={control} name="supplier_payment_terms" render={({ field }) => (
              <FormField label="Supplier Payment Terms" help="Drives when this cost is paid (payables). Overrides the Working Capital default supplier payment days.">
                <SelectInput value={field.value} onChange={field.onChange} options={paymentTermsOptions} />
              </FormField>
            )} />
            <Controller control={control} name="cost_inflation_rate" render={({ field }) => (
              <FormField label="Cost Inflation Rate" help="Annual increase applied to this cost.">
                <PercentageInput value={field.value} onChange={field.onChange} allowNegative />
              </FormField>
            )} />
            <Controller control={control} name="waste_defect_rate_percent" render={({ field }) => (
              <FormField label="Waste / Defect Rate (optional)">
                <PercentageInput value={field.value} onChange={field.onChange} />
              </FormField>
            )} />
            <Controller control={control} name="minimum_order_quantity" render={({ field }) => (
              <FormField label="Minimum Order Quantity (optional)">
                <NumberInput value={field.value} onChange={field.onChange} unit="units" />
              </FormField>
            )} />
            <Controller control={control} name="currency_override" render={({ field }) => (
              <FormField label="Currency Override (optional)" help={`Defaults to the project currency (${currency}).`}>
                <SelectInput value={field.value} onChange={(v) => field.onChange(v)} options={currencyOptions} placeholder={currency} />
              </FormField>
            )} />
            <Controller control={control} name="start_date" render={({ field }) => (
              <FormField label={method === 'one_time' ? 'Start Date' : 'Start Date (optional)'}
                required={method === 'one_time'} error={err.start_date?.message}
                help={method === 'one_time'
                  ? 'Required for one-time costs — the month the cost is incurred.'
                  : "Leave blank to follow the linked product's launch date. Set a date only to override when the cost starts."}>
                <DateInput value={field.value ?? null} onChange={(v) => field.onChange(v ?? '')} error={!!err.start_date} />
              </FormField>
            )} />
            <Controller control={control} name="end_date" render={({ field }) => (
              <FormField label="End Date (optional)">
                <DateInput value={field.value ?? null} onChange={(v) => field.onChange(v)} />
              </FormField>
            )} />
            <Controller control={control} name="vat_applicable" render={({ field }) => (
              <FormField label="This item is VAT-applicable" help="Marks whether this cost is subject to VAT at the project default rate (set on the Tax page). It does not set the rate.">
                <div className="row" style={{ gap: 10 }}>
                  <Switch checked={field.value} onChange={field.onChange} />
                  <span className="muted" style={{ fontSize: 13 }}>{field.value ? 'Yes' : 'No'}</span>
                </div>
              </FormField>
            )} />
            <Controller control={control} name="active" render={({ field }) => (
              <FormField label="Active">
                <div className="row" style={{ gap: 10 }}>
                  <Switch checked={field.value} onChange={field.onChange} />
                  <span className="muted" style={{ fontSize: 13 }}>{field.value ? 'Active' : 'Archived'}</span>
                </div>
              </FormField>
            )} />
            <Controller control={control} name="notes" render={({ field }) => (
              <FormField label="Notes" span={2}>
                <TextAreaInput value={field.value ?? ''} onChange={(v) => field.onChange(v || null)} />
              </FormField>
            )} />
          </div>
        </SectionCard>
      </div>
    </Modal>
  )
}
