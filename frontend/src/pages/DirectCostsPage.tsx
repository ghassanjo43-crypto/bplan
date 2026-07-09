import { useMemo, useState } from 'react'
import { PageHeader } from '@/components/PageHeader'
import { SaveBar } from '@/components/SaveBar'
import { SectionCard } from '@/components/SectionCard'
import { SummaryCard } from '@/components/SummaryCard'
import { DataTable, type Column } from '@/components/DataTable'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingScreen } from '@/components/ui/Spinner'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import {
  useCollectionSection,
  useDeleteCollectionItem,
  useSaveCollectionItem,
} from '@/api/hooks'
import { useProjectContext } from '@/layouts/ProjectContext'
import type { DirectCostItem, ProductService, RevenueStream } from '@/types'
import { formatCurrency, formatDate, formatPercent } from '@/utils/format'
import {
  costCalculationMethodOptions,
  directCostCategoryOptions,
  labelFor,
} from '@/utils/options'
import {
  associationLabel,
  type Associable,
  COST_TEMPLATES,
  isUnassigned,
  marginByProduct,
  methodValueLabel,
  usesPercent,
} from '@/utils/directCosts'
import { DirectCostModal, type DirectCostPrefill } from './directCosts/DirectCostModal'

type Tab = { key: string; label: string }

export function DirectCostsPage({ embedded }: { embedded?: boolean } = {}) {
  const { projectId, currency } = useProjectContext()
  const productsQ = useCollectionSection<ProductService>(projectId, 'products')
  const streamsQ = useCollectionSection<RevenueStream>(projectId, 'revenue-streams')
  const itemsQ = useCollectionSection<DirectCostItem>(projectId, 'direct-costs')
  const saveItem = useSaveCollectionItem<DirectCostItem>(projectId, 'direct-costs')
  const deleteItem = useDeleteCollectionItem(projectId, 'direct-costs')
  const { notify } = useToast()

  const [tab, setTab] = useState('all')
  const [modal, setModal] = useState<{ open: boolean; item: DirectCostItem | null; prefill?: DirectCostPrefill }>(
    { open: false, item: null },
  )

  const products = productsQ.data ?? []
  const items = itemsQ.data ?? []
  // Revenue streams are the primary association source; fall back to legacy
  // products only for old projects that have no revenue streams. Hidden products
  // are never surfaced in the association UI once streams exist.
  const activeStreams = (streamsQ.data ?? []).filter((s) => s.active)
  const hasStreams = activeStreams.length > 0
  const associations: Associable[] = hasStreams
    ? activeStreams.map((s) => ({ id: s.id, name: s.name }))
    : products.map((p) => ({ id: p.id, name: p.name }))

  const tabs: Tab[] = useMemo(
    () => [
      { key: 'all', label: 'All' },
      { key: 'shared', label: 'Shared' },
      { key: 'unassigned', label: 'Unassigned' },
      ...associations.map((a) => ({ key: `p:${a.id}`, label: a.name })),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(associations)],
  )

  const filtered = useMemo(() => {
    if (tab === 'all') return items
    if (tab === 'shared') return items.filter((i) => i.apply_to_all)
    if (tab === 'unassigned') return items.filter(isUnassigned)
    const pid = tab.slice(2)
    return items.filter((i) => i.apply_to_all || i.product_ids.includes(pid))
  }, [tab, items])

  // Gross-margin preview is inherently product-based (selling price vs unit
  // cost); it is only shown for legacy product-only projects so hidden products
  // are never exposed once revenue streams are the primary workflow.
  const margins = useMemo(
    () => (hasStreams ? [] : marginByProduct(products, items)),
    [hasStreams, products, items],
  )

  if (productsQ.isLoading || streamsQ.isLoading || itemsQ.isLoading) return <LoadingScreen />

  // -- summary metrics ------------------------------------------------------
  const activeItems = items.filter((i) => i.active)
  const unassignedCount = items.filter(isUnassigned).length
  const amountTotal = activeItems
    .filter((i) => !usesPercent(i.calculation_method))
    .reduce((s, i) => s + i.amount, 0)
  const avgMargin = margins.length ? margins.reduce((s, m) => s + m.marginPct, 0) / margins.length : 0

  // -- warnings -------------------------------------------------------------
  const warnings: string[] = []
  margins.filter((m) => m.negative).forEach((m) =>
    warnings.push(`“${m.product.name}” has a negative estimated gross margin.`),
  )
  if (unassignedCount > 0) warnings.push(`${unassignedCount} direct cost item${unassignedCount > 1 ? 's are' : ' is'} unassigned.`)
  items
    .filter((i) => !usesPercent(i.calculation_method) && i.amount === 0)
    .forEach((i) => warnings.push(`“${i.name}” has no cost amount set.`))

  // -- actions --------------------------------------------------------------
  const handleSubmit = (payload: Partial<DirectCostItem>) => {
    const merged = modal.item ? { ...modal.item, ...payload } : payload
    saveItem.mutate(merged as DirectCostItem, {
      onSuccess: () => {
        notify(modal.item ? 'Cost item updated' : 'Cost item added')
        setModal({ open: false, item: null })
      },
      onError: (e) => notify((e as Error).message || 'Save failed', 'error'),
    })
  }

  const duplicate = (item: DirectCostItem) => {
    const { id: _id, created_at: _c, updated_at: _u, ...rest } = item
    void _id; void _c; void _u
    saveItem.mutate({ ...rest, name: `${item.name} (copy)` } as DirectCostItem, {
      onSuccess: () => notify('Cost item duplicated'),
      onError: (e) => notify((e as Error).message || 'Duplicate failed', 'error'),
    })
  }

  const remove = (item: DirectCostItem) => {
    if (!window.confirm(`Delete “${item.name}”? This cannot be undone.`)) return
    deleteItem.mutate(item.id, { onSuccess: () => notify('Cost item deleted') })
  }

  const columns: Column<DirectCostItem>[] = [
    { header: 'Cost Item', cell: (r) => <strong>{r.name}</strong> },
    { header: 'Category', cell: (r) => labelFor(directCostCategoryOptions, r.category) },
    {
      header: 'Revenue Stream',
      cell: (r) =>
        isUnassigned(r) ? (
          <Badge tone="amber" dot>Unassigned</Badge>
        ) : r.apply_to_all ? (
          <Badge tone="blue">All revenue streams</Badge>
        ) : (
          associationLabel(r, associations)
        ),
    },
    { header: 'Method', cell: (r) => <Badge tone="neutral">{labelFor(costCalculationMethodOptions, r.calculation_method)}</Badge> },
    { header: 'Amount / %', align: 'right', cell: (r) => methodValueLabel(r, currency) },
    { header: 'Allocation', cell: (r) => (r.allocation_method ? r.allocation_method.replace(/_/g, ' ') : '—') },
    { header: 'Start', cell: (r) => formatDate(r.start_date) },
    { header: 'Status', cell: (r) => <ActiveBadge active={r.active} /> },
    {
      header: '',
      cell: (r) => (
        <button className="icon-btn" title="Duplicate" onClick={() => duplicate(r)}>⧉</button>
      ),
    },
  ]

  const openTemplate = (tplKey: string) => {
    const tpl = COST_TEMPLATES.find((t) => t.key === tplKey)
    if (!tpl) return
    setModal({
      open: true,
      item: null,
      prefill: {
        name: tpl.label,
        category: tpl.category,
        calculation_method: tpl.method,
        cost_behavior: tpl.behavior,
      },
    })
  }

  return (
    <>
      {!embedded ? (
        <PageHeader
          breadcrumb="Business Plan · Revenue & Costs"
          title="Direct Costs / Cost of Goods Sold"
          helpKey="direct.costs"
          subtitle="Build flexible direct-cost items and associate each with one, many, all, or no revenue streams."
          actions={
            <button className="btn btn--primary" onClick={() => setModal({ open: true, item: null })}>
              + Add Direct Cost
            </button>
          }
        />
      ) : (
        <div className="row row--between" style={{ marginBottom: 16 }}>
          <span className="muted">Define direct-cost items and associate them with revenue streams.</span>
          <button className="btn btn--primary btn--sm" onClick={() => setModal({ open: true, item: null })}>+ Add Direct Cost</button>
        </div>
      )}

      <div className="stack">
        {/* Summary */}
        <div className="stat-grid">
          <SummaryCard label="Direct Cost Items" value={items.length} accent="blue" hint={`${activeItems.length} active`} />
          <SummaryCard label="Amount-based Total" value={formatCurrency(amountTotal, currency)} accent="amber" help="Sum of fixed/per-unit amounts (excludes % methods)." />
          <SummaryCard label="Avg. Gross Margin" value={!hasStreams && products.length ? formatPercent(avgMargin) : '—'} accent={avgMargin < 0 ? 'amber' : 'green'} help="Average estimated gross margin across products (legacy product projects)." />
          <SummaryCard label="Unassigned" value={unassignedCount} accent={unassignedCount ? 'amber' : 'slate'} />
        </div>

        {/* Warnings */}
        {warnings.length > 0 && (
          <SectionCard title="Warnings" icon="⚠" subtitle="Items that need attention before projection.">
            <div className="stack--sm">
              {warnings.map((w, i) => (
                <div className="banner banner--warning" key={i}>
                  <span className="banner__icon">⚠</span>
                  <div>{w}</div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* Quick-add templates */}
        <SectionCard title="Quick-add Templates" subtitle="Start from a common direct-cost type." icon="✦">
          <div className="row row--wrap" style={{ gap: 8 }}>
            {COST_TEMPLATES.map((t) => (
              <button key={t.key} className="chip" onClick={() => openTemplate(t.key)}>
                + {t.label}
              </button>
            ))}
          </div>
        </SectionCard>

        {/* Table with tabs */}
        <SectionCard
          title="Direct Cost Items"
          subtitle={`${filtered.length} shown`}
          icon="◵"
          actions={
            items.length > 0 ? (
              <button className="btn btn--secondary btn--sm" onClick={() => setModal({ open: true, item: null })}>
                + Add
              </button>
            ) : undefined
          }
        >
          {items.length === 0 ? (
            <EmptyState
              icon="◵"
              title="No direct cost items yet"
              description="Add a direct cost item or pick a quick-add template above to get started."
              action={
                <button className="btn btn--primary" onClick={() => setModal({ open: true, item: null })}>
                  + Add Direct Cost
                </button>
              }
            />
          ) : (
            <>
              <div className="tabs" style={{ marginBottom: 16 }}>
                {tabs.map((t) => (
                  <button key={t.key} className={`tab${tab === t.key ? ' tab--active' : ''}`} onClick={() => setTab(t.key)}>
                    {t.label}
                    {t.key === 'unassigned' && unassignedCount > 0 && (
                      <span style={{ marginLeft: 6, color: 'var(--amber-600)' }}>({unassignedCount})</span>
                    )}
                  </button>
                ))}
              </div>
              {filtered.length === 0 ? (
                <EmptyState icon="◇" title="Nothing here" description="No cost items match this filter." />
              ) : (
                <DataTable columns={columns} rows={filtered} onEdit={(r) => setModal({ open: true, item: r })} onDelete={remove} />
              )}
            </>
          )}
        </SectionCard>

        {/* Gross margin preview — legacy product projects only */}
        {!hasStreams && products.length > 0 && (
          <SectionCard title="Gross Margin Preview" subtitle="Estimated from per-unit and percentage direct costs." icon="◴">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product / Service</th>
                    <th style={{ textAlign: 'right' }}>Selling Price</th>
                    <th style={{ textAlign: 'right' }}>Est. Unit Direct Cost</th>
                    <th style={{ textAlign: 'right' }}>Gross Margin</th>
                    <th style={{ textAlign: 'right' }}>Margin %</th>
                  </tr>
                </thead>
                <tbody>
                  {margins.map((m) => (
                    <tr key={m.product.id}>
                      <td><strong>{m.product.name}</strong></td>
                      <td className="table__num">{formatCurrency(m.product.selling_price, currency)}</td>
                      <td className="table__num">{formatCurrency(m.unitCost, currency)}</td>
                      <td className="table__num">{formatCurrency(m.margin, currency)}</td>
                      <td className="table__num">
                        <Badge tone={m.negative ? 'amber' : 'green'}>{formatPercent(m.marginPct)}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        )}
      </div>

      <DirectCostModal
        key={modal.item?.id ?? JSON.stringify(modal.prefill) ?? 'new'}
        open={modal.open}
        item={modal.item}
        prefill={modal.prefill}
        associations={associations}
        currency={currency}
        onClose={() => setModal({ open: false, item: null })}
        onSubmit={handleSubmit}
        saving={saveItem.isPending}
      />

      {!embedded && <SaveBar slug="direct-costs" />}
    </>
  )
}
