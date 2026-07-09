import { useHelpMode } from '@/help/HelpModeProvider'

/** Header switch that turns Guided Help tooltips on or off, app-wide. */
export function HelpModeToggle() {
  const { helpMode, toggleHelpMode } = useHelpMode()
  return (
    <button
      type="button"
      role="switch"
      aria-checked={helpMode}
      className={`help-toggle${helpMode ? ' help-toggle--on' : ''}`}
      onClick={toggleHelpMode}
      title={
        helpMode
          ? 'Guided Help is on — hover a title or label for a tip. Click to turn off.'
          : 'Turn on Guided Help to see contextual tips when hovering titles and labels.'
      }
    >
      <span className="help-toggle__icon" aria-hidden="true">?</span>
      <span className="help-toggle__label">Help</span>
    </button>
  )
}
