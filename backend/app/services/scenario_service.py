"""Named saved scenarios: default handling + backfill.

CRUD for scenarios is the generic collection router (``/projects/{id}/scenarios``).
This adds the two behaviours CRUD alone can't provide: guaranteeing every project
has exactly one *default* scenario (with a name), and back-filling a ``Base Case``
for older projects that predate named scenarios.
"""
from __future__ import annotations

from ..models import BusinessPlanProject, ScenarioAssumption
from ..models.enums import ScenarioType

_TYPE_LABEL = {
    "base": "Base Case",
    "conservative": "Conservative Case",
    "optimistic": "Optimistic Case",
    "custom": "Custom Scenario",
}


def display_name(s: ScenarioAssumption) -> str:
    return s.name or s.label or _TYPE_LABEL.get(s.scenario_type.value, s.scenario_type.value.title())


def ensure_default(project: BusinessPlanProject) -> bool:
    """Guarantee scenarios have names and exactly one default.

    A project with no scenarios gets a ``Base Case`` default. Returns True when
    the project was modified (the caller should persist it).
    """
    scenarios = project.scenarios
    if not scenarios:
        project.scenarios.append(ScenarioAssumption(
            name="Base Case", scenario_type=ScenarioType.BASE, is_default=True,
        ))
        return True

    changed = False
    for s in scenarios:                       # backfill blank names
        if not s.name:
            s.name = display_name(s)
            changed = True

    # Exactly one default: keep an existing one, else the base type, else first.
    defaults = [s for s in scenarios if s.is_default]
    if len(defaults) != 1:
        chosen = defaults[0] if defaults else next(
            (s for s in scenarios if s.scenario_type == ScenarioType.BASE), scenarios[0]
        )
        for s in scenarios:
            want = s is chosen
            if s.is_default != want:
                s.is_default = want
                changed = True
    return changed


def set_default(project: BusinessPlanProject, scenario_id: str) -> ScenarioAssumption | None:
    """Mark one scenario as the default and clear the rest. Returns it, or None."""
    match = next((s for s in project.scenarios if s.id == scenario_id), None)
    if match is None:
        return None
    for s in project.scenarios:
        s.is_default = s is match
    return match


def backfill_all(storage) -> int:
    """Ensure every stored project has a default Base Case. Returns # changed."""
    changed = 0
    for project in storage.list_projects():
        if ensure_default(project):
            project.touch()
            storage.save_project(project)
            changed += 1
    return changed
