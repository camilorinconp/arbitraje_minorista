# backend/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..auth.service import auth_service
from ..auth.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh,
    PasswordChange, PasswordReset, PasswordResetConfirm, EmailVerification,
    MessageResponse, UserPermissions, UserStats
)
from ..auth.middleware import (
    get_current_user, get_current_active_user, get_current_verified_user,
    get_current_admin_user, require_permission
)
from ..auth.models import User
from ..services.database import get_db_session
from ..services.rate_limiter import limiter
from ..services.metrics import metrics_collector
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


# === ENDPOINTS PÚBLICOS ===

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Límite estricto para registro
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Registrar nuevo usuario.
    """
    try:
        user = await auth_service.create_user(user_data, db)
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in user registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # Límite para login
async def login_user(
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Iniciar sesión de usuario.
    """
    try:
        # Autenticar usuario
        user = await auth_service.authenticate_user(login_data, db)
        if not user:
            # Registrar intento de login fallido
            metrics_collector.increment_counter(
                "login_attempts_total",
                tags={"result": "failed", "endpoint": "/auth/login"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Obtener metadatos del request
        metadata = {
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None
        }

        # Crear tokens
        tokens = await auth_service.create_user_tokens(user, db, **metadata)

        logger.info(f"User {user.email} logged in successfully")
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Dict[str, str])
@limiter.limit("20/minute")  # Límite para refresh
async def refresh_token(
    request: Request,
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Renovar token de acceso.
    """
    try:
        new_access_token = await auth_service.refresh_user_token(token_data.refresh_token, db)
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Verificar email de usuario.
    """
    try:
        success = await auth_service.verify_user_email(verification_data.token, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        return MessageResponse(
            message="Email verified successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/password-reset", response_model=MessageResponse)
@limiter.limit("5/minute")  # Muy restrictivo para reset
async def request_password_reset(
    request: Request,
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Solicitar reset de password.
    """
    try:
        user = await auth_service.get_user_by_email(reset_data.email, db)
        if user:
            # Generar token de reset
            reset_token = user.generate_reset_token()
            await db.commit()

            # Aquí enviarías el email con el token
            logger.info(f"Password reset requested for: {reset_data.email}")

        # Siempre retornar éxito para no revelar si el email existe
        return MessageResponse(
            message="If the email exists, a password reset link has been sent",
            success=True
        )
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/password-reset-confirm", response_model=MessageResponse)
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Confirmar reset de password.
    """
    try:
        # Verificar token de reset
        from sqlalchemy.future import select
        stmt = select(User).where(User.reset_token == reset_data.token)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_reset_token_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Cambiar password
        user.set_password(reset_data.new_password)
        user.clear_reset_token()

        # Revocar todos los tokens por seguridad
        await auth_service.revoke_all_user_tokens(user.id, db)

        await db.commit()

        logger.info(f"Password reset completed for user: {user.email}")
        return MessageResponse(
            message="Password reset successfully",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming password reset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset confirmation failed"
        )


# === ENDPOINTS AUTENTICADOS ===

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener información del usuario actual.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Actualizar información del usuario actual.
    """
    try:
        # Campos permitidos para actualización
        allowed_fields = {"full_name", "username"}

        for field, value in user_update.items():
            if field in allowed_fields and hasattr(current_user, field):
                setattr(current_user, field, value)

        await db.commit()
        await db.refresh(current_user)

        return UserResponse.from_orm(current_user)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cambiar password del usuario actual.
    """
    try:
        success = await auth_service.change_password(current_user, password_data, db)
        if success:
            return MessageResponse(
                message="Password changed successfully",
                success=True
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout_user(
    token_data: TokenRefresh,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cerrar sesión (revocar refresh token).
    """
    try:
        success = await auth_service.revoke_refresh_token(token_data.refresh_token, db)
        return MessageResponse(
            message="Logged out successfully" if success else "Token not found",
            success=success
        )
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Cerrar sesión en todos los dispositivos.
    """
    try:
        revoked_count = await auth_service.revoke_all_user_tokens(current_user.id, db)
        return MessageResponse(
            message=f"Logged out from {revoked_count} devices",
            success=True
        )
    except Exception as e:
        logger.error(f"Error during logout all: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        )


@router.get("/permissions", response_model=UserPermissions)
async def get_user_permissions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener permisos del usuario actual.
    """
    # Definir permisos por rol
    role_permissions = {
        "admin": ["read", "write", "delete", "scrape", "manage_users"],
        "scraper": ["read", "write", "scrape"],
        "user": ["read"]
    }

    permissions = role_permissions.get(current_user.role, [])
    if current_user.is_superuser:
        permissions = ["all"]

    return UserPermissions(
        permissions=permissions,
        role=current_user.role,
        is_superuser=current_user.is_superuser
    )


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtener estadísticas del usuario actual.
    """
    try:
        stats_data = await auth_service.get_user_stats(current_user.id, db)
        return UserStats(**stats_data)
    except Exception as e:
        logger.error(f"Error getting user stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user stats"
        )


# === ENDPOINTS DE ADMINISTRACIÓN ===

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Listar usuarios (solo admins).
    """
    try:
        from sqlalchemy.future import select
        stmt = select(User).offset(skip).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()

        return [UserResponse.from_orm(user) for user in users]

    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve users"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtener usuario por ID (solo admins).
    """
    try:
        user = await auth_service.get_user_by_id(user_id, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.from_orm(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user"
        )