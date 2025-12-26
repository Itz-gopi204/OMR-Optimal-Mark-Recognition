from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import logging
import csv
import io

from beanie import PydanticObjectId
from beanie.operators import In

from app.models.user import User, UserProfile, UserRole, UserStatus
from app.models.institution import Institution
from app.core.security import get_password_hash
from app.core.exceptions import (
    NotFoundError,
    AlreadyExistsError,
    ForbiddenError,
    TenantAccessError,
    BadRequestError,
)
from .schemas import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserProfileResponse,
    UserListResponse,
    BulkImportResult,
    UserStatsResponse,
)

logger = logging.getLogger(__name__)


class UserService:
    """User management service."""

    @staticmethod
    async def get_user_by_id(
        user_id: str,
        current_user: User,
        institution_id: Optional[str] = None
    ) -> User:
        """Get user by ID with tenant check."""
        user = await User.get(PydanticObjectId(user_id))

        if not user:
            raise NotFoundError("User", user_id)

        # Tenant check
        if not current_user.is_super_admin():
            if str(user.institution_id) != str(current_user.institution_id):
                raise TenantAccessError()

        return user

    @staticmethod
    async def list_users(
        current_user: User,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None,
        department: Optional[str] = None,
    ) -> UserListResponse:
        """List users with pagination and filters."""

        # Build query
        query = {}

        # Tenant filtering
        if not current_user.is_super_admin():
            query["institution_id"] = current_user.institution_id

        if role:
            query["role"] = role.value

        if status:
            query["status"] = status.value

        if department:
            query["department"] = department

        # Build aggregation pipeline
        pipeline = [{"$match": query}]

        # Search filter
        if search:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"email": {"$regex": search, "$options": "i"}},
                        {"profile.first_name": {"$regex": search, "$options": "i"}},
                        {"profile.last_name": {"$regex": search, "$options": "i"}},
                        {"profile.student_id": {"$regex": search, "$options": "i"}},
                    ]
                }
            })

        # Get total count
        count_pipeline = pipeline + [{"$count": "total"}]
        count_result = await User.aggregate(count_pipeline).to_list()
        total = count_result[0]["total"] if count_result else 0

        # Pagination
        skip = (page - 1) * page_size
        pipeline.extend([
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": page_size}
        ])

        # Execute query
        users = await User.aggregate(pipeline).to_list()

        # Convert to response
        items = []
        for user_data in users:
            items.append(UserResponse(
                id=str(user_data["_id"]),
                email=user_data["email"],
                profile=UserProfileResponse(
                    first_name=user_data["profile"]["first_name"],
                    last_name=user_data["profile"]["last_name"],
                    avatar=user_data["profile"].get("avatar"),
                    phone=user_data["profile"].get("phone"),
                    student_id=user_data["profile"].get("student_id"),
                    employee_id=user_data["profile"].get("employee_id"),
                ),
                role=user_data["role"],
                department=user_data.get("department"),
                institution_id=str(user_data.get("institution_id")) if user_data.get("institution_id") else None,
                status=user_data["status"],
                email_verified=user_data.get("email_verified", False),
                last_login_at=user_data.get("last_login_at"),
                created_at=user_data["created_at"],
                updated_at=user_data["updated_at"],
            ))

        total_pages = (total + page_size - 1) // page_size

        return UserListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    async def create_user(
        request: UserCreateRequest,
        current_user: User
    ) -> User:
        """Create a new user."""

        # Check email uniqueness
        existing = await User.find_one(User.email == request.email.lower())
        if existing:
            raise AlreadyExistsError("User", "email", request.email)

        # Determine institution
        institution_id = current_user.institution_id

        # Validate role assignment
        if request.role == UserRole.SUPER_ADMIN:
            if not current_user.is_super_admin():
                raise ForbiddenError("Only super admins can create super admin users")
            institution_id = None

        if request.role == UserRole.INSTITUTION_ADMIN:
            if not (current_user.is_super_admin() or current_user.is_institution_admin()):
                raise ForbiddenError("Only admins can create admin users")

        # Create user
        user = User(
            email=request.email.lower(),
            password_hash=get_password_hash(request.password),
            institution_id=institution_id,
            profile=UserProfile(
                first_name=request.profile.first_name,
                last_name=request.profile.last_name,
                phone=request.profile.phone,
                student_id=request.profile.student_id,
                employee_id=request.profile.employee_id,
                date_of_birth=request.profile.date_of_birth,
                gender=request.profile.gender,
            ),
            role=request.role,
            department=request.department,
            status=UserStatus.ACTIVE,  # Admin-created users are active by default
            email_verified=True,  # Skip verification for admin-created users
        )

        await user.insert()
        logger.info(f"User created by {current_user.email}: {user.email}")
        return user

    @staticmethod
    async def update_user(
        user_id: str,
        request: UserUpdateRequest,
        current_user: User
    ) -> User:
        """Update user."""
        user = await UserService.get_user_by_id(user_id, current_user)

        # Role change validation
        if request.role:
            if request.role == UserRole.SUPER_ADMIN:
                if not current_user.is_super_admin():
                    raise ForbiddenError("Cannot assign super admin role")
            if user.role == UserRole.SUPER_ADMIN and not current_user.is_super_admin():
                raise ForbiddenError("Cannot modify super admin users")

        # Update fields
        if request.profile:
            if request.profile.first_name:
                user.profile.first_name = request.profile.first_name
            if request.profile.last_name:
                user.profile.last_name = request.profile.last_name
            if request.profile.phone is not None:
                user.profile.phone = request.profile.phone
            if request.profile.student_id is not None:
                user.profile.student_id = request.profile.student_id
            if request.profile.employee_id is not None:
                user.profile.employee_id = request.profile.employee_id
            if request.profile.date_of_birth is not None:
                user.profile.date_of_birth = request.profile.date_of_birth
            if request.profile.gender is not None:
                user.profile.gender = request.profile.gender

        if request.role:
            user.role = request.role

        if request.department is not None:
            user.department = request.department

        if request.status:
            user.status = request.status

        await user.save_with_timestamp()
        logger.info(f"User updated by {current_user.email}: {user.email}")
        return user

    @staticmethod
    async def delete_user(user_id: str, current_user: User) -> bool:
        """Delete user."""
        user = await UserService.get_user_by_id(user_id, current_user)

        # Cannot delete self
        if str(user.id) == str(current_user.id):
            raise BadRequestError("Cannot delete your own account")

        # Cannot delete super admins unless you're a super admin
        if user.role == UserRole.SUPER_ADMIN and not current_user.is_super_admin():
            raise ForbiddenError("Cannot delete super admin users")

        await user.delete()
        logger.info(f"User deleted by {current_user.email}: {user.email}")
        return True

    @staticmethod
    async def update_status(
        user_id: str,
        status: UserStatus,
        current_user: User
    ) -> User:
        """Update user status."""
        user = await UserService.get_user_by_id(user_id, current_user)

        if str(user.id) == str(current_user.id):
            raise BadRequestError("Cannot change your own status")

        user.status = status
        await user.save_with_timestamp()
        logger.info(f"User status changed by {current_user.email}: {user.email} -> {status.value}")
        return user

    @staticmethod
    async def bulk_import(
        csv_data: str,
        current_user: User,
        default_role: UserRole = UserRole.STUDENT
    ) -> BulkImportResult:
        """Bulk import users from CSV."""
        reader = csv.DictReader(io.StringIO(csv_data))

        total = 0
        successful = 0
        failed = 0
        errors = []

        for row in reader:
            total += 1
            try:
                email = row.get("email", "").strip().lower()
                first_name = row.get("first_name", "").strip()
                last_name = row.get("last_name", "").strip()
                password = row.get("password", "").strip() or "TempPass123!"
                role_str = row.get("role", "").strip().lower()
                student_id = row.get("student_id", "").strip()

                if not email or not first_name or not last_name:
                    raise ValueError("Missing required fields")

                # Check if exists
                existing = await User.find_one(User.email == email)
                if existing:
                    raise ValueError(f"Email already exists")

                # Determine role
                role = default_role
                if role_str:
                    try:
                        role = UserRole(role_str)
                    except ValueError:
                        role = default_role

                # Create user
                user = User(
                    email=email,
                    password_hash=get_password_hash(password),
                    institution_id=current_user.institution_id,
                    profile=UserProfile(
                        first_name=first_name,
                        last_name=last_name,
                        student_id=student_id if student_id else None,
                    ),
                    role=role,
                    status=UserStatus.ACTIVE,
                    email_verified=True,
                )
                await user.insert()
                successful += 1

            except Exception as e:
                failed += 1
                errors.append({
                    "row": total,
                    "email": row.get("email", "unknown"),
                    "error": str(e)
                })

        logger.info(f"Bulk import by {current_user.email}: {successful}/{total} successful")
        return BulkImportResult(
            total=total,
            successful=successful,
            failed=failed,
            errors=errors
        )

    @staticmethod
    async def get_stats(current_user: User) -> UserStatsResponse:
        """Get user statistics."""
        # Build query
        query = {}
        if not current_user.is_super_admin():
            query["institution_id"] = current_user.institution_id

        # Total users
        total_users = await User.find(query).count()

        # Active users
        active_query = {**query, "status": UserStatus.ACTIVE.value}
        active_users = await User.find(active_query).count()

        # By role
        by_role = {}
        for role in UserRole:
            role_query = {**query, "role": role.value}
            count = await User.find(role_query).count()
            by_role[role.value] = count

        # Recent signups (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_query = {**query, "created_at": {"$gte": week_ago}}
        recent_signups = await User.find(recent_query).count()

        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            by_role=by_role,
            recent_signups=recent_signups
        )
