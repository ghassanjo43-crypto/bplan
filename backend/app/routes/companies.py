"""Company routes: company CRUD + a company's projects."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..models import BusinessPlanProject, Company, CompanySummary, ProjectSummary
from ..services.companies import CompanyService
from ..storage import get_company_storage, get_storage
from ..storage.base import NotFoundError, StorageBackend
from ..storage.company_storage import CompanyStorage

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(
    storage: StorageBackend = Depends(get_storage),
    companies: CompanyStorage = Depends(get_company_storage),
) -> CompanyService:
    return CompanyService(storage, companies)


class CompanyCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    industry_sector: str | None = None
    business_description: str | None = None
    country: str | None = None
    city: str | None = None
    status: str = "active"


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    trading_name: str | None = None
    legal_name: str | None = None
    industry_sector: str | None = None
    business_description: str | None = None
    country: str | None = None
    city: str | None = None
    website: str | None = None
    status: str | None = None
    notes: str | None = None


class ProjectCreateForCompany(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


@router.get("", response_model=list[CompanySummary])
def list_companies(request: Request, svc: CompanyService = Depends(get_company_service)):
    svc.migrate_all()  # ensure legacy projects are linked before listing
    summaries = svc.list_summaries()
    ids = _authorized_company_ids(request)
    if ids is None:
        return summaries
    return [s for s in summaries if s.id in ids]


@router.get("/my-company", response_model=CompanySummary)
def my_company(request: Request, svc: CompanyService = Depends(get_company_service)):
    user = getattr(request.state, "user", None)
    if user is None or not getattr(user, "company_id", None):
        raise HTTPException(404, "No company assigned")
    svc.migrate_all()
    summary = next((s for s in svc.list_summaries() if s.id == user.company_id), None)
    if not summary:
        raise HTTPException(404, "No company assigned")
    return summary


def _authorized_company_ids(request: Request):
    """None = all (admin); else set of allowed company ids (own + granted demo)."""
    user = getattr(request.state, "user", None)
    if user is None or getattr(user, "role", None) == "admin":
        return None
    from ..dependencies.auth import authorized_company_ids
    return set(authorized_company_ids(user) or [])


@router.post("", response_model=Company, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, svc: CompanyService = Depends(get_company_service)):
    return svc.create(Company(**payload.model_dump()))


@router.get("/{company_id}", response_model=Company)
def get_company(company_id: str, svc: CompanyService = Depends(get_company_service)):
    try:
        return svc.get(company_id)
    except NotFoundError:
        raise HTTPException(404, f"Company {company_id!r} not found")


@router.put("/{company_id}", response_model=Company)
def update_company(company_id: str, payload: CompanyUpdate, svc: CompanyService = Depends(get_company_service)):
    try:
        return svc.update(company_id, payload.model_dump(exclude_unset=True))
    except NotFoundError:
        raise HTTPException(404, f"Company {company_id!r} not found")


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: str, delete_projects: bool = False,
                   svc: CompanyService = Depends(get_company_service)):
    svc.delete(company_id, delete_projects=delete_projects)


@router.get("/{company_id}/projects", response_model=list[ProjectSummary])
def list_company_projects(company_id: str, svc: CompanyService = Depends(get_company_service)):
    return svc.list_projects(company_id)


@router.post("/{company_id}/projects", response_model=BusinessPlanProject,
             status_code=status.HTTP_201_CREATED)
def create_company_project(company_id: str, payload: ProjectCreateForCompany,
                           svc: CompanyService = Depends(get_company_service)):
    try:
        return svc.create_project(company_id, payload.name)
    except NotFoundError:
        raise HTTPException(404, f"Company {company_id!r} not found")
