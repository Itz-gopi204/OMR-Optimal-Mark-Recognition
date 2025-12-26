from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets
import logging

from beanie import PydanticObjectId

from app.config.settings import settings
from app.models.user import User, UserProfile, UserRole, UserStatus
from app.models.institution import Institution
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.exceptions import (
    UnauthorizedError,
    AlreadyExistsError,
    NotFoundError,
    BadRequestError,
    ValidationError,
)
from .schemas import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    @staticmethod
    async def authenticate_user(email: str, password: str) -> User:
        """Authenticate user with email and password."""
        user = await User.find_one(User.email == email.lower())

        if not user:
            raise UnauthorizedError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if user.status == UserStatus.SUSPENDED:
            raise UnauthorizedError("Account has been suspended")

        if user.status == UserStatus.INACTIVE:
            raise UnauthorizedError("Account is inactive")

        return user

    @staticmethod
    async def login(request: LoginRequest) -> Tuple[TokenResponse, User]:
        """Login user and return tokens."""
        user = await AuthService.authenticate_user(request.email, request.password)

        # Update last login
        user.last_login_at = datetime.utcnow()
        await user.save()

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "institution_id": str(user.institution_id) if user.institution_id else None,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        logger.info(f"User logged in: {user.email}")
        return tokens, user

    @staticmethod
    async def register(request: RegisterRequest) -> Tuple[TokenResponse, User]:
        """Register new user."""
        # Check if email already exists
        existing_user = await User.find_one(User.email == request.email.lower())
        if existing_user:
            raise AlreadyExistsError("User", "email", request.email)

        # If institution code provided, validate it
        institution_id = None
        role = UserRole.STUDENT  # Default role for self-registration

        if request.institution_code:
            institution = await Institution.find_one(
                Institution.code == request.institution_code.upper()
            )
            if not institution:
                raise NotFoundError("Institution", request.institution_code)

            if not institution.is_active():
                raise BadRequestError("Institution is not active")

            institution_id = institution.id

        # Create user
        user = User(
            email=request.email.lower(),
            password_hash=get_password_hash(request.password),
            institution_id=institution_id,
            profile=UserProfile(
                first_name=request.first_name,
                last_name=request.last_name
            ),
            role=role,
            status=UserStatus.PENDING_VERIFICATION,
            email_verification_token=secrets.token_urlsafe(32)
        )

        await user.insert()

        # TODO: Send verification email
        # await send_verification_email(user)

        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "institution_id": str(user.institution_id) if user.institution_id else None,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        logger.info(f"New user registered: {user.email}")
        return tokens, user

    @staticmethod
    async def refresh_tokens(refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        try:
            payload = verify_token(refresh_token, "refresh")
            user_id = payload.get("sub")

            if not user_id:
                raise UnauthorizedError("Invalid refresh token")

            user = await User.get(PydanticObjectId(user_id))

            if not user:
                raise UnauthorizedError("User not found")

            if not user.is_active():
                raise UnauthorizedError("User account is not active")

            # Create new tokens
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "institution_id": str(user.institution_id) if user.institution_id else None,
            }

            new_access_token = create_access_token(token_data)
            new_refresh_token = create_refresh_token(token_data)

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

        except Exception as e:
            raise UnauthorizedError(f"Invalid refresh token: {str(e)}")

    @staticmethod
    async def request_password_reset(email: str) -> bool:
        """Request password reset for user."""
        user = await User.find_one(User.email == email.lower())

        if not user:
            # Don't reveal if email exists
            return True

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await user.save()

        # TODO: Send password reset email
        # await send_password_reset_email(user, reset_token)

        logger.info(f"Password reset requested for: {email}")
        return True

    @staticmethod
    async def reset_password(token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        user = await User.find_one(User.password_reset_token == token)

        if not user:
            raise BadRequestError("Invalid or expired reset token")

        if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
            raise BadRequestError("Reset token has expired")

        # Update password
        user.password_hash = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        await user.save()

        logger.info(f"Password reset completed for: {user.email}")
        return True

    @staticmethod
    async def verify_email(token: str) -> bool:
        """Verify user email with token."""
        user = await User.find_one(User.email_verification_token == token)

        if not user:
            raise BadRequestError("Invalid verification token")

        user.email_verified = True
        user.email_verification_token = None

        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE

        await user.save()

        logger.info(f"Email verified for: {user.email}")
        return True

    @staticmethod
    async def change_password(
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Current password is incorrect")

        user.password_hash = get_password_hash(new_password)
        await user.save()

        logger.info(f"Password changed for: {user.email}")
        return True

    @staticmethod
    async def create_super_admin(
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> User:
        """Create a super admin user (for initial setup)."""
        existing = await User.find_one(User.email == email.lower())
        if existing:
            raise AlreadyExistsError("User", "email", email)

        user = User(
            email=email.lower(),
            password_hash=get_password_hash(password),
            institution_id=None,
            profile=UserProfile(
                first_name=first_name,
                last_name=last_name
            ),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )

        await user.insert()
        logger.info(f"Super admin created: {email}")
        return user
