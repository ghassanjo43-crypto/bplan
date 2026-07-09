/* Pure layout helpers for the Text Builder columns.
 *
 * The three-column grid width is driven by CSS variables toggled via these
 * modifier classes (see textBuilder.css). Collapsing a side panel shrinks its
 * column to a thin rail so the center editor expands to fill the space. */

export const HELP_KEYS = {
  left: 'tb.leftCollapsed',
  right: 'tb.rightCollapsed',
} as const

/** Build the `.tb` grid container className from the collapse state. */
export function tbGridClass(leftCollapsed: boolean, rightCollapsed: boolean): string {
  return [
    'tb',
    leftCollapsed ? 'tb--left-collapsed' : '',
    rightCollapsed ? 'tb--right-collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ')
}
