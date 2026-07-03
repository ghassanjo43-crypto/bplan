"""Revenue Stream forecast endpoint.

CRUD for revenue streams is auto-generated from the section registry
(``/projects/{id}/revenue-streams``). This adds the computed forecast — the
per-stream monthly/annual revenue and the automatic totals by period — which the
wizard's preview and the revenue list use.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services import ProjectService
from ..services import revenue_stream_service as rss
from .deps import get_service, project_or_404

router = APIRouter(prefix="/projects/{project_id}", tags=["Revenue Streams"])


@router.get("/revenue-streams-forecast")
def revenue_streams_forecast(project_id: str, view: str = "yearly",
                             service: ProjectService = Depends(get_service)) -> dict:
    project = project_or_404(project_id, service)
    return rss.build_forecast(project, view)
