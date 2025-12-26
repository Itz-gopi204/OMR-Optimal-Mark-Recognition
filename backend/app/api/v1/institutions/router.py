from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User
from app.core.security import get_current_superuser
from .schemas import (
    InstitutionCreateRequest,
    InstitutionUpdateRequest,
    InstitutionResponse,
    InstitutionListResponse,
    InstitutionStatsResponse,
)
from .service import InstitutionService

router = APIRouter()


@router.get(
    "",
    response_model=InstitutionListResponse,
    summary="List all institutions"
)
async def list_institutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_superuser)
):
    """
    List all institutions (Super Admin only).

    - Can filter by status, type
    - Search by name, code, or slug
    """
    return await InstitutionService.list_institutions(
        page=page,
        page_size=page_size,
        status=status,
        type=type,
        search=search,
    )


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create institution"
)
async def create_institution(
    request: InstitutionCreateRequest,
    current_user: User = Depends(get_current_superuser)
):
    """
    Create a new institution (Super Admin only).

    - **name**: Institution display name
    - **slug**: URL-friendly identifier (lowercase, alphanumeric, hyphens)
    - **code**: Unique institution code (uppercase)
    - **type**: Institution type (school, university, coaching)
    - **contact**: Contact information including email
    """
    institution = await InstitutionService.create(request, current_user)
    return InstitutionService._to_response(institution)


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution"
)
async def get_institution(
    institution_id: str,
    current_user: User = Depends(get_current_superuser)
):
    """
    Get institution details by ID (Super Admin only).
    """
    institution = await InstitutionService.get_by_id(institution_id)
    return InstitutionService._to_response(institution)


@router.put(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update institution"
)
async def update_institution(
    institution_id: str,
    request: InstitutionUpdateRequest,
    current_user: User = Depends(get_current_superuser)
):
    """
    Update institution details (Super Admin only).
    """
    institution = await InstitutionService.update(institution_id, request)
    return InstitutionService._to_response(institution)


@router.delete(
    "/{institution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete institution"
)
async def delete_institution(
    institution_id: str,
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete an institution (Super Admin only).

    Cannot delete institutions with existing users.
    """
    await InstitutionService.delete(institution_id)
    return None


@router.put(
    "/{institution_id}/status",
    response_model=InstitutionResponse,
    summary="Update institution status"
)
async def update_institution_status(
    institution_id: str,
    status: str = Query(..., description="New status: active, suspended, trial, pending"),
    current_user: User = Depends(get_current_superuser)
):
    """
    Activate or suspend an institution (Super Admin only).
    """
    institution = await InstitutionService.update_status(institution_id, status)
    return InstitutionService._to_response(institution)


@router.get(
    "/{institution_id}/stats",
    response_model=InstitutionStatsResponse,
    summary="Get institution statistics"
)
async def get_institution_stats(
    institution_id: str,
    current_user: User = Depends(get_current_superuser)
):
    """
    Get statistics for an institution (Super Admin only).
    """
    return await InstitutionService.get_stats(institution_id)
