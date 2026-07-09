"""AI narrative generation route.

POST /api/projects/{project_id}/ai/generate-section

Generates professional business-plan narrative text. It reads project data to
enrich the prompt but never mutates the project or its financial model.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas.ai import AiGenerateRequest, AiGenerateResponse
from ..services import ai_service
from ..storage import get_storage
from ..storage.base import NotFoundError, StorageBackend

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["ai"])


@router.post("/generate-section", response_model=AiGenerateResponse)
def generate_section(
    project_id: str,
    body: AiGenerateRequest,
    storage: StorageBackend = Depends(get_storage),
):
    try:
        project = storage.get_project(project_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")

    try:
        return ai_service.generate(project, body)
    except ai_service.AiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ai_service.AiProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
