/* Pure, framework-free logic for Guided Help mode.
 *
 * Kept separate from the React provider so it is unit-testable under
 * `node --test` (no DOM). Help mode defaults to OFF so the UI stays clean for
 * experienced users. */
import { helpContent, type HelpKey } from './helpContent.ts'

export const HELP_MODE_KEY = 'bplan_help_mode'

/** Minimal storage shape (localStorage-compatible) so tests can inject a mock. */
export interface KVStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

function defaultStorage(): KVStorage | null {
  try {
    if (typeof localStorage !== 'undefined') return localStorage
  } catch {
    /* localStorage can throw in sandboxed / privacy modes */
  }
  return null
}

/** Read the persisted help-mode flag. Defaults to false (OFF) when unset. */
export function readHelpMode(storage: KVStorage | null = defaultStorage()): boolean {
  try {
    return storage?.getItem(HELP_MODE_KEY) === 'on'
  } catch {
    return false
  }
}

/** Persist the help-mode flag. */
export function writeHelpMode(on: boolean, storage: KVStorage | null = defaultStorage()): void {
  try {
    storage?.setItem(HELP_MODE_KEY, on ? 'on' : 'off')
  } catch {
    /* ignore write failures (private mode / quota) */
  }
}

/**
 * Decide what a HelpTooltip should show. Returns the help text when help mode is
 * ON and the key exists, otherwise null. A missing/unknown key resolves to null
 * (graceful) rather than throwing.
 */
export function resolveHelpText(
  helpKey: string,
  helpMode: boolean,
  registry: Record<string, { text: string }> = helpContent,
): string | null {
  if (!helpMode) return null
  const entry = registry[helpKey as HelpKey]
  return entry?.text ?? null
}
