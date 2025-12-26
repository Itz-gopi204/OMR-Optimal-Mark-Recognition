from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.models.user import User
from app.core.security import get_current_user
from .schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    ChangePasswordRequest,
    UserResponse,
)
from .service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user"
)
async def register(request: RegisterRequest):
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: Strong password (8+ chars, uppercase, lowercase, digit, special char)
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **institution_code**: Optional institution code to join an organization
    """
    tokens, user = await AuthService.register(request)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user"
)
async def login(request: LoginRequest):
    """
    Authenticate user and get access tokens.

    Returns access token and refresh token for API authentication.
    """
    tokens, user = await AuthService.login(request)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token"
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.

    Use this when access token expires to get a new one.
    """
    tokens = await AuthService.refresh_tokens(request.refresh_token)
    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user"
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout current user.

    Note: This invalidates the session on the client side.
    For full security, implement token blacklisting.
    """
    # TODO: Implement token blacklisting with Redis
    return {"message": "Successfully logged out"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request password reset"
)
async def forgot_password(request: PasswordResetRequest):
    """
    Request a password reset email.

    An email with reset instructions will be sent if the account exists.
    """
    await AuthService.request_password_reset(request.email)
    return {"message": "If an account exists with this email, a reset link has been sent"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password with token"
)
async def reset_password(request: PasswordResetConfirm):
    """
    Reset password using the token from reset email.
    """
    await AuthService.reset_password(request.token, request.new_password)
    return {"message": "Password has been reset successfully"}


@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verify email address"
)
async def verify_email(request: EmailVerificationRequest):
    """
    Verify email address using the token from verification email.
    """
    await AuthService.verify_email(request.token)
    return {"message": "Email verified successfully"}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend verification email"
)
async def resend_verification(current_user: User = Depends(get_current_user)):
    """
    Resend email verification link.
    """
    if current_user.email_verified:
        return {"message": "Email is already verified"}

    # TODO: Implement resend verification email
    return {"message": "Verification email has been resent"}


@router.put(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change password"
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Change current user's password.

    Requires current password for verification.
    """
    await AuthService.change_password(
        current_user,
        request.current_password,
        request.new_password
    )
    return {"message": "Password changed successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user"
)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.profile.first_name,
        last_name=current_user.profile.last_name,
        role=current_user.role.value,
        institution_id=str(current_user.institution_id) if current_user.institution_id else None,
        status=current_user.status.value,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at
    )
