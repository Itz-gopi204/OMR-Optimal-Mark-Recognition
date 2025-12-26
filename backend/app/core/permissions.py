from enum import Enum
from functools import wraps
from typing import List, Callable
from fastapi import HTTPException, status, Depends

from app.models.user import User, UserRole


class Permission(str, Enum):
    """Fine-grained permissions for the system."""

    # Institution management (Super Admin only)
    MANAGE_INSTITUTIONS = "manage:institutions"
    VIEW_ALL_INSTITUTIONS = "view:all_institutions"

    # User management
    CREATE_USERS = "create:users"
    READ_USERS = "read:users"
    UPDATE_USERS = "update:users"
    DELETE_USERS = "delete:users"
    BULK_IMPORT_USERS = "bulk_import:users"

    # OMR Template management
    CREATE_TEMPLATES = "create:templates"
    READ_TEMPLATES = "read:templates"
    UPDATE_TEMPLATES = "update:templates"
    DELETE_TEMPLATES = "delete:templates"
    PUBLISH_TEMPLATES = "publish:templates"

    # Test/Exam management
    CREATE_TESTS = "create:tests"
    READ_TESTS = "read:tests"
    UPDATE_TESTS = "update:tests"
    DELETE_TESTS = "delete:tests"
    PUBLISH_RESULTS = "publish:results"

    # OMR Sheet management
    UPLOAD_SHEETS = "upload:sheets"
    PROCESS_SHEETS = "process:sheets"
    REVIEW_SHEETS = "review:sheets"
    DELETE_SHEETS = "delete:sheets"
    OVERRIDE_ANSWERS = "override:answers"

    # Results
    VIEW_ALL_RESULTS = "view:all_results"
    VIEW_OWN_RESULTS = "view:own_results"
    EXPORT_RESULTS = "export:results"

    # Analytics
    VIEW_ANALYTICS = "view:analytics"
    VIEW_INSTITUTION_ANALYTICS = "view:institution_analytics"

    # Survey management
    CREATE_SURVEYS = "create:surveys"
    READ_SURVEYS = "read:surveys"
    UPDATE_SURVEYS = "update:surveys"
    DELETE_SURVEYS = "delete:surveys"

    # Attendance management
    CREATE_ATTENDANCE = "create:attendance"
    READ_ATTENDANCE = "read:attendance"
    UPDATE_ATTENDANCE = "update:attendance"

    # Settings
    MANAGE_SETTINGS = "manage:settings"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, List[Permission]] = {
    UserRole.SUPER_ADMIN: list(Permission),  # Super admin has all permissions

    UserRole.INSTITUTION_ADMIN: [
        # User management
        Permission.CREATE_USERS,
        Permission.READ_USERS,
        Permission.UPDATE_USERS,
        Permission.DELETE_USERS,
        Permission.BULK_IMPORT_USERS,

        # Templates
        Permission.CREATE_TEMPLATES,
        Permission.READ_TEMPLATES,
        Permission.UPDATE_TEMPLATES,
        Permission.DELETE_TEMPLATES,
        Permission.PUBLISH_TEMPLATES,

        # Tests
        Permission.CREATE_TESTS,
        Permission.READ_TESTS,
        Permission.UPDATE_TESTS,
        Permission.DELETE_TESTS,
        Permission.PUBLISH_RESULTS,

        # Sheets
        Permission.UPLOAD_SHEETS,
        Permission.PROCESS_SHEETS,
        Permission.REVIEW_SHEETS,
        Permission.DELETE_SHEETS,
        Permission.OVERRIDE_ANSWERS,

        # Results
        Permission.VIEW_ALL_RESULTS,
        Permission.EXPORT_RESULTS,

        # Analytics
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_INSTITUTION_ANALYTICS,

        # Surveys
        Permission.CREATE_SURVEYS,
        Permission.READ_SURVEYS,
        Permission.UPDATE_SURVEYS,
        Permission.DELETE_SURVEYS,

        # Attendance
        Permission.CREATE_ATTENDANCE,
        Permission.READ_ATTENDANCE,
        Permission.UPDATE_ATTENDANCE,

        # Settings
        Permission.MANAGE_SETTINGS,
    ],

    UserRole.TEACHER: [
        # Users (read only)
        Permission.READ_USERS,

        # Templates
        Permission.CREATE_TEMPLATES,
        Permission.READ_TEMPLATES,
        Permission.UPDATE_TEMPLATES,

        # Tests
        Permission.CREATE_TESTS,
        Permission.READ_TESTS,
        Permission.UPDATE_TESTS,
        Permission.PUBLISH_RESULTS,

        # Sheets
        Permission.UPLOAD_SHEETS,
        Permission.PROCESS_SHEETS,
        Permission.REVIEW_SHEETS,
        Permission.OVERRIDE_ANSWERS,

        # Results
        Permission.VIEW_ALL_RESULTS,
        Permission.EXPORT_RESULTS,

        # Analytics
        Permission.VIEW_ANALYTICS,

        # Surveys
        Permission.CREATE_SURVEYS,
        Permission.READ_SURVEYS,
        Permission.UPDATE_SURVEYS,

        # Attendance
        Permission.CREATE_ATTENDANCE,
        Permission.READ_ATTENDANCE,
        Permission.UPDATE_ATTENDANCE,
    ],

    UserRole.STUDENT: [
        Permission.VIEW_OWN_RESULTS,
        Permission.READ_ATTENDANCE,
    ],

    UserRole.PARENT: [
        Permission.VIEW_OWN_RESULTS,  # View linked student's results
        Permission.READ_ATTENDANCE,
    ],
}


def get_user_permissions(user: User) -> List[Permission]:
    """Get all permissions for a user based on their role."""
    role_perms = ROLE_PERMISSIONS.get(user.role, [])
    # Add any custom permissions assigned to the user
    custom_perms = [Permission(p) for p in user.permissions if p in Permission._value2member_map_]
    return list(set(role_perms + custom_perms))


def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has a specific permission."""
    user_permissions = get_user_permissions(user)
    return permission in user_permissions


def require_permissions(permissions: List[Permission]):
    """Dependency to require specific permissions."""
    from app.core.security import get_current_user

    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = get_user_permissions(current_user)

        for perm in permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {perm.value}"
                )

        return current_user

    return permission_checker


def require_any_permission(permissions: List[Permission]):
    """Dependency to require at least one of the specified permissions."""
    from app.core.security import get_current_user

    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_permissions = get_user_permissions(current_user)

        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least one of: {[p.value for p in permissions]}"
            )

        return current_user

    return permission_checker


def require_role(roles: List[UserRole]):
    """Dependency to require specific roles."""
    from app.core.security import get_current_user

    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {[r.value for r in roles]}"
            )
        return current_user

    return role_checker


class PermissionChecker:
    """Class-based permission checker for more complex scenarios."""

    def __init__(self, required_permissions: List[Permission], require_all: bool = True):
        self.required_permissions = required_permissions
        self.require_all = require_all

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_permissions = get_user_permissions(current_user)

        if self.require_all:
            missing = [p for p in self.required_permissions if p not in user_permissions]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {[p.value for p in missing]}"
                )
        else:
            if not any(p in user_permissions for p in self.required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

        return current_user
