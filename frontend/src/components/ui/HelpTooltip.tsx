import type { ReactNode } from 'react'
import { Tooltip } from './Tooltip'
import { useHelpMode } from '@/help/HelpModeProvider'
import { resolveHelpText } from '@/help/helpMode'

/**
 * Wraps a title/label/button so that — only when Guided Help mode is ON — a
 * short contextual explanation appears on hover or keyboard focus. When help
 * mode is OFF, or the key is unknown, the children render unchanged.
 */
export function HelpTooltip({
  helpKey,
  children,
}: {
  helpKey: string
  /** The title/label/button being explained. */
  children: ReactNode
}) {
  const { helpMode } = useHelpMode()
  const text = resolveHelpText(helpKey, helpMode)
  if (!text) return <>{children}</>
  return (
    <Tooltip text={text}>
      <span className="help-target">
        {children}
        <span className="help-target__badge" aria-hidden="true">
          ⓘ
        </span>
      </span>
    </Tooltip>
  )
}
