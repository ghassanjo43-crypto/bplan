import { useCallback, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface Pos {
  top: number
  left: number
  placement: 'top' | 'bottom'
}

/* Estimated bubble height used to decide whether there is room above the
   trigger. If not, the bubble flips below so it is never clipped by a
   scrolling container or the top of a card. */
const FLIP_THRESHOLD = 120

function useFloatingBubble() {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [pos, setPos] = useState<Pos | null>(null)

  const show = useCallback(() => {
    const el = triggerRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const placement: Pos['placement'] = r.top < FLIP_THRESHOLD ? 'bottom' : 'top'
    // Keep the (center-anchored) bubble within the viewport horizontally.
    const left = Math.min(Math.max(r.left + r.width / 2, 140), window.innerWidth - 140)
    setPos({
      top: placement === 'top' ? r.top : r.bottom,
      left,
      placement,
    })
  }, [])

  const hide = useCallback(() => setPos(null), [])

  return { triggerRef, pos, show, hide }
}

function Bubble({ pos, text }: { pos: Pos; text: string }) {
  const style: React.CSSProperties = {
    position: 'fixed',
    top: pos.top,
    left: pos.left,
    transform:
      pos.placement === 'top'
        ? 'translate(-50%, calc(-100% - 9px))'
        : 'translate(-50%, 9px)',
  }
  return createPortal(
    <span
      className={`tooltip__bubble tooltip__bubble--floating tooltip__bubble--${pos.placement}`}
      role="tooltip"
      style={style}
    >
      {text}
    </span>,
    document.body,
  )
}

/** Inline "?" info bubble used next to financial-term labels. */
export function TooltipInfo({ text }: { text: string }) {
  const { triggerRef, pos, show, hide } = useFloatingBubble()
  return (
    <span
      ref={triggerRef}
      className="tooltip"
      aria-label={text}
      tabIndex={0}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <span className="tooltip__icon">?</span>
      {pos && <Bubble pos={pos} text={text} />}
    </span>
  )
}

/** Generic hover tooltip wrapper for arbitrary trigger content. */
export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  const { triggerRef, pos, show, hide } = useFloatingBubble()
  return (
    <span
      ref={triggerRef}
      className="tooltip"
      tabIndex={0}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {pos && <Bubble pos={pos} text={text} />}
    </span>
  )
}
