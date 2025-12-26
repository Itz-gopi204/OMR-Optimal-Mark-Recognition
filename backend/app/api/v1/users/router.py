from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, status

from app.models.user import User, UserRole, UserStatus
from app.core.security import get_current_user
from app.core.permissions import Permission, require_permissions
from .schemas import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserProfileResponse,
    UserListResponse,
    BulkImportResult,
    UserStatsResponse,
)
from .service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users"
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    search: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(require_permissions([Permission.READ_USERS]))
):
    """
    List users with pagination and filters.

    - Filtered by current user's institution (except super admin)
    - Can filter by role, status, department
    - Search by email, name, or student ID
    """
    return await UserService.list_users(
        current_user=current_user,
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        search=search,
        department=department,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user"
)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_permissions([Permission.CREATE_USERS]))
):
    """
    Create a new user.

    - Admin can create users for their institution
    - Super admin can create users for any institution
    - Role restrictions apply based on creator's role
    """
    user = await UserService.create_user(request, current_user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=UserProfileResponse(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            avatar=user.profile.avatar,
            phone=user.profile.phone,
            student_id=user.profile.student_id,
            employee_id=user.profile.employee_id,
        ),
        role=user.role.value,
        department=user.department,
        institution_id=str(user.institution_id) if user.institution_id else None,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "/stats",
    response_model=UserStatsResponse,
    summary="Get user statistics"
)
async def get_user_stats(
    current_user: User = Depends(require_permissions([Permission.VIEW_ANALYTICS]))
):
    """
    Get user statistics for the institution.
    """
    return await UserService.get_stats(current_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID"
)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permissions([Permission.READ_USERS]))
):
    """
    Get user details by ID.
    """
    user = await UserService.get_user_by_id(user_id, current_user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=UserProfileResponse(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            avatar=user.profile.avatar,
            phone=user.profile.phone,
            student_id=user.profile.student_id,
            employee_id=user.profile.employee_id,
        ),
        role=user.role.value,
        department=user.department,
        institution_id=str(user.institution_id) if user.institution_id else None,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user"
)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: User = Depends(require_permissions([Permission.UPDATE_USERS]))
):
    """
    Update user details.
    """
    user = await UserService.update_user(user_id, request, current_user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=UserProfileResponse(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            avatar=user.profile.avatar,
            phone=user.profile.phone,
            student_id=user.profile.student_id,
            employee_id=user.profile.employee_id,
        ),
        role=user.role.value,
        department=user.department,
        institution_id=str(user.institution_id) if user.institution_id else None,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user"
)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permissions([Permission.DELETE_USERS]))
):
    """
    Delete a user.
    """
    await UserService.delete_user(user_id, current_user)
    return None


@router.put(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Update user status"
)
async def update_user_status(
    user_id: str,
    status: UserStatus,
    current_user: User = Depends(require_permissions([Permission.UPDATE_USERS]))
):
    """
    Activate or deactivate a user.
    """
    user = await UserService.update_status(user_id, status, current_user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        profile=UserProfileResponse(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            avatar=user.profile.avatar,
            phone=user.profile.phone,
            student_id=user.profile.student_id,
            employee_id=user.profile.employee_id,
        ),
        role=user.role.value,
        department=user.department,
        institution_id=str(user.institution_id) if user.institution_id else None,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/bulk-import",
    response_model=BulkImportResult,
    summary="Bulk import users"
)
async def bulk_import_users(
    file: UploadFile = File(...),
    default_role: UserRole = Query(UserRole.STUDENT),
    current_user: User = Depends(require_permissions([Permission.BULK_IMPORT_USERS]))
):
    """
    Bulk import users from CSV file.

    CSV format:
    - email (required)
    - first_name (required)
    - last_name (required)
    - password (optional, defaults to TempPass123!)
    - role (optional)
    - student_id (optional)
    """
    content = await file.read()
    csv_data = content.decode("utf-8")
    return await UserService.bulk_import(csv_data, current_user, default_role)
