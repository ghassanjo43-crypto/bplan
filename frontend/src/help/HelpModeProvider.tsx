import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { readHelpMode, writeHelpMode } from './helpMode'

interface HelpModeValue {
  helpMode: boolean
  setHelpMode: (on: boolean) => void
  toggleHelpMode: () => void
}

const HelpModeContext = createContext<HelpModeValue | null>(null)

export function HelpModeProvider({ children }: { children: ReactNode }) {
  // Initialise from localStorage (defaults to OFF when unset).
  const [helpMode, setHelpModeState] = useState<boolean>(() => readHelpMode())

  const setHelpMode = useCallback((on: boolean) => {
    writeHelpMode(on)
    setHelpModeState(on)
  }, [])

  const toggleHelpMode = useCallback(() => {
    setHelpModeState((prev) => {
      const next = !prev
      writeHelpMode(next)
      return next
    })
  }, [])

  return (
    <HelpModeContext.Provider value={{ helpMode, setHelpMode, toggleHelpMode }}>
      {children}
    </HelpModeContext.Provider>
  )
}

/** Access help mode. Safe to call without a provider (defaults to OFF, no-ops). */
export function useHelpMode(): HelpModeValue {
  const ctx = useContext(HelpModeContext)
  if (!ctx) {
    return { helpMode: false, setHelpMode: () => {}, toggleHelpMode: () => {} }
  }
  return ctx
}
