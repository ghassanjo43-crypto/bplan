import { useEffect, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useForm, type FieldValues, type Path } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { PageHeader } from '@/components/PageHeader'
import { SaveBar } from '@/components/SaveBar'
import { LoadingScreen } from '@/components/ui/Spinner'
import { SchemaFields } from '@/components/form/SchemaFields'
import { buildZodSchema, defaultsFromConfig } from '@/components/form/schema'
import type { FormConfig } from '@/components/form/types'
import { useSaveSingletonSection, useSingletonSection } from '@/api/hooks'
import { useProjectContext } from '@/layouts/ProjectContext'
import { useToast } from '@/components/ui/Toast'
import { timeAgo } from '@/utils/format'
import { pageBySlug } from '@/routes/nav'

interface Props<T> {
  slug: string
  sectionKey: string
  config: FormConfig
  /** Extra UI rendered between the header and the form (e.g. summary cards). */
  renderTop?: (values: FieldValues) => ReactNode
  /** Extra UI rendered after the form (e.g. live preview cards). */
  renderBottom?: (values: FieldValues) => ReactNode
  /** Map raw stored record -> form values (defaults to identity). */
  toForm?: (data: T | null) => Partial<FieldValues>
}

export function SingletonFormPage<T extends object>({
  slug,
  sectionKey,
  config,
  renderTop,
  renderBottom,
  toForm,
}: Props<T>) {
  const { projectId, currency } = useProjectContext()
  const page = pageBySlug(slug)
  const { data, isLoading } = useSingletonSection<T>(projectId, sectionKey)
  const save = useSaveSingletonSection<Record<string, unknown>>(projectId, sectionKey)
  const { notify } = useToast()

  const [searchParams] = useSearchParams()
  const form = useForm<FieldValues>({
    resolver: zodResolver(buildZodSchema(config)),
    defaultValues: defaultsFromConfig(config),
  })
  const { control, handleSubmit, reset, watch, formState, setFocus } = form

  // Populate the form when data arrives — but never clobber unsaved edits.
  // Background refetches (e.g. on window focus) must not reset what the user is
  // currently typing, otherwise the edit is lost and the stale value is saved.
  useEffect(() => {
    if (data === undefined) return
    if (formState.isDirty) return
    const base = defaultsFromConfig(config)
    const mapped = toForm ? toForm(data) : (data as unknown as FieldValues | null)
    reset({ ...base, ...(mapped ?? {}) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  // Focus a specific field when navigated to with ?focus=<field> (e.g. the
  // pencil next to the company name in the workspace header).
  useEffect(() => {
    if (isLoading) return
    const focus = searchParams.get('focus')
    if (!focus) return
    const field = focus === 'company_name' ? 'business_name' : focus
    const exists = config.some((s) => s.fields.some((f) => f.name === field))
    if (exists) setTimeout(() => setFocus(field as Path<FieldValues>), 50)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, searchParams])

  const onSubmit = handleSubmit(
    (values) => {
      // Empty optional <select> fields submit as "" which fail backend enum
      // validation (422). Drop empty-string / undefined values so optional enums
      // become null and defaulted enums fall back to their server default.
      const cleaned = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v !== '' && v !== undefined),
      )
      save.mutate(cleaned, {
        onSuccess: () => {
          notify('Changes saved')
          reset(values) // clears dirty state
        },
        onError: (e) => notify((e as Error).message || 'Save failed', 'error'),
      })
    },
    () => notify('Please fix the highlighted fields', 'error'),
  )

  if (isLoading) return <LoadingScreen />

  const values = watch()
  const lastSaved = (data as { updated_at?: string } | null)?.updated_at

  return (
    <>
      <PageHeader
        breadcrumb={`Business Plan · ${page?.group ?? ''}`}
        title={page?.label ?? ''}
        subtitle={page?.subtitle}
        helpKey={slug === 'setup' ? 'project.setup' : undefined}
      />
      <div className="stack">
        {renderTop?.(values)}
        <SchemaFields config={config} control={control} currency={currency} />
        {renderBottom?.(values)}
      </div>
      <SaveBar
        slug={slug}
        onSave={onSubmit}
        saving={save.isPending}
        dirty={formState.isDirty}
        lastSavedLabel={lastSaved ? timeAgo(lastSaved) : undefined}
      />
    </>
  )
}
