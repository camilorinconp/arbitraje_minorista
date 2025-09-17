# backend/auth/middleware.py

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from .jwt_handler import jwt_handler
from .models import User
from ..services.database import get_db_session
from ..services.metrics import metrics_collector

logger = logging.getLogger(__name__)

# Configuración del esquema de autenticación
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """
    Middleware de autenticación para validar tokens JWT.
    """

    def __init__(self):
        self.jwt_handler = jwt_handler

    async def __call__(self, request: Request, call_next):
        """
        Procesar request de autenticación.
        """
        # Extraer token del header Authorization
        authorization = request.headers.get("Authorization")
        token = None

        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]

        # Agregar información de autenticación al request state
        request.state.authenticated = False
        request.state.current_user = None
        request.state.token_payload = None

        if token:
            try:
                # Verificar token
                payload = self.jwt_handler.verify_token(token)
                request.state.authenticated = True
                request.state.token_payload = payload

                # Registrar métricas de autenticación exitosa
                metrics_collector.increment_counter(
                    "auth_success_total",
                    tags={
                        "user_id": str(payload.get("user_id", "unknown")),
                        "endpoint": request.url.path
                    }
                )

                logger.debug(f"Successfully authenticated user: {payload.get('sub')}")

            except HTTPException as e:
                # Registrar métricas de autenticación fallida
                metrics_collector.increment_counter(
                    "auth_failure_total",
                    tags={
                        "reason": "invalid_token",
                        "endpoint": request.url.path
                    }
                )

                logger.warning(f"Authentication failed for endpoint {request.url.path}: {e.detail}")

            except Exception as e:
                # Error inesperado en autenticación
                metrics_collector.increment_counter(
                    "auth_error_total",
                    tags={
                        "error_type": type(e).__name__,
                        "endpoint": request.url.path
                    }
                )

                logger.error(f"Unexpected auth error: {e}", exc_info=True)

        response = await call_next(request)
        return response


# Dependencias de autenticación

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Obtener usuario actual (opcional - no falla si no está autenticado).
    """
    if not credentials:
        return None

    try:
        payload = jwt_handler.verify_token(credentials.credentials)
        user_id = payload.get("user_id")

        if not user_id:
            return None

        # Buscar usuario en la base de datos
        from sqlalchemy.future import select
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Actualizar última actividad (sin commit para evitar overhead)
            user.update_last_login()

        return user

    except HTTPException:
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {e}", exc_info=True)
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Obtener usuario actual (requerido - falla si no está autenticado).
    """
    if not credentials:
        logger.warning("No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt_handler.verify_token(credentials.credentials)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )

        # Buscar usuario en la base de datos
        from sqlalchemy.future import select
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found or inactive: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Actualizar última actividad
        user.update_last_login()

        # Registrar métrica de acceso de usuario
        metrics_collector.increment_counter(
            "user_access_total",
            tags={
                "user_id": str(user.id),
                "role": user.role
            }
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Obtener usuario activo actual.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Obtener usuario verificado actual.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Obtener usuario admin actual.
    """
    if not current_user.has_permission("manage_users"):
        logger.warning(f"User {current_user.id} attempted admin access without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Obtener superusuario actual.
    """
    if not current_user.is_superuser:
        logger.warning(f"User {current_user.id} attempted superuser access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


# Decoradores de permisos

def require_permission(permission: str):
    """
    Decorador para requerir un permiso específico.
    """
    async def permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(permission):
            logger.warning(f"User {current_user.id} lacks permission: {permission}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user

    return permission_dependency


def require_role(role: str):
    """
    Decorador para requerir un rol específico.
    """
    async def role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != role and not current_user.is_superuser:
            logger.warning(f"User {current_user.id} lacks role: {role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        return current_user

    return role_dependency


# Funciones de utilidad

async def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extraer token JWT del request.
    """
    # Intentar desde Authorization header
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]

    # Intentar desde query parameter (para debugging)
    token = request.query_params.get("token")
    if token:
        return token

    return None


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    Obtener usuario desde un token JWT.
    """
    try:
        payload = jwt_handler.verify_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            return None

        from sqlalchemy.future import select
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None


# Instancia del middleware
auth_middleware = AuthMiddleware()