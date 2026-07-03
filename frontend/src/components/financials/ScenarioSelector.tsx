import { useEffect } from 'react'
import type { ScenarioKey } from '@/types/incomeStatement'
import { useScenarios } from '@/api/scenariosApi'

/** Scenario picker driven by the project's saved scenarios (selected by id).
 *  Falls back to the three legacy types until scenarios have loaded. */
export function ScenarioSelector({
  projectId,
  value,
  onChange,
}: {
  projectId?: string
  value: ScenarioKey
  onChange: (v: ScenarioKey) => void
}) {
  const { data } = useScenarios(projectId)
  const scenarios = data ?? []

  // Once scenarios load, snap the selection to a real scenario id (the default)
  // if the current value isn't one of them (e.g. the initial "base").
  useEffect(() => {
    if (!scenarios.length) return
    if (!scenarios.some((s) => s.id === value)) {
      const def = scenarios.find((s) => s.is_default) ?? scenarios[0]
      onChange(def.id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  return (
    <div className="field" style={{ minWidth: 180 }}>
      <span className="field__label">Scenario</span>
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {scenarios.length === 0 && <option value="base">Base Case</option>}
        {scenarios.map((s) => (
          <option key={s.id} value={s.id}>
            {(s.name || s.label || s.scenario_type) + (s.is_default ? ' (default)' : '')}
          </option>
        ))}
      </select>
    </div>
  )
}
