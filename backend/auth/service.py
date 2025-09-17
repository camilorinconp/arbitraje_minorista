# backend/auth/service.py

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from .models import User, RefreshToken
from .jwt_handler import jwt_handler
from .schemas import UserCreate, UserLogin, TokenResponse, PasswordChange, PasswordReset
from ..services.metrics import metrics_collector
from ..services.event_bus import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class AuthService:
    """
    Servicio de autenticación que maneja usuarios, login, y tokens.
    """

    def __init__(self):
        self.jwt_handler = jwt_handler

    async def create_user(self, user_data: UserCreate, db: AsyncSession) -> User:
        """
        Crear nuevo usuario.
        """
        try:
            # Verificar si el usuario ya existe
            existing_user = await self.get_user_by_email(user_data.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )

            existing_username = await self.get_user_by_username(user_data.username, db)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username already exists"
                )

            # Crear nuevo usuario
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                role="user"  # Rol por defecto
            )

            # Hash de la password
            db_user.set_password(user_data.password)

            # Generar token de verificación
            verification_token = db_user.generate_verification_token()

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            # Registrar métricas
            metrics_collector.increment_counter(
                "users_created_total",
                tags={"role": db_user.role}
            )

            # Publicar evento
            event = Event(
                type=EventType.RETAILER_CREATED,  # Reutilizamos este evento
                data={
                    "user_id": db_user.id,
                    "email": db_user.email,
                    "username": db_user.username,
                    "verification_token": verification_token
                },
                timestamp=datetime.now(timezone.utc),
                source="auth_service"
            )
            await event_bus.publish(event)

            logger.info(f"Created new user: {db_user.email}")
            return db_user

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Database integrity error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User creation failed due to data conflict"
            )
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Unexpected error creating user: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )

    async def authenticate_user(self, login_data: UserLogin, db: AsyncSession) -> Optional[User]:
        """
        Autenticar usuario con email y password.
        """
        try:
            user = await self.get_user_by_email(login_data.email, db)
            if not user:
                # Registrar intento de login con email inexistente
                metrics_collector.increment_counter(
                    "login_attempts_total",
                    tags={"result": "user_not_found"}
                )
                return None

            if not user.verify_password(login_data.password):
                # Registrar intento de login con password incorrecta
                metrics_collector.increment_counter(
                    "login_attempts_total",
                    tags={"result": "invalid_password", "user_id": str(user.id)}
                )
                return None

            if not user.is_active:
                # Usuario inactivo
                metrics_collector.increment_counter(
                    "login_attempts_total",
                    tags={"result": "user_inactive", "user_id": str(user.id)}
                )
                return None

            # Login exitoso
            user.update_last_login()
            await db.commit()

            metrics_collector.increment_counter(
                "login_success_total",
                tags={"user_id": str(user.id), "role": user.role}
            )

            logger.info(f"Successful login for user: {user.email}")
            return user

        except Exception as e:
            logger.error(f"Error authenticating user: {e}", exc_info=True)
            metrics_collector.increment_counter(
                "login_errors_total",
                tags={"error_type": type(e).__name__}
            )
            return None

    async def create_user_tokens(self, user: User, db: AsyncSession, **metadata) -> TokenResponse:
        """
        Crear tokens JWT para usuario.
        """
        try:
            # Datos para el token
            token_data = {
                "sub": user.email,
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "is_superuser": user.is_superuser,
                "is_verified": user.is_verified
            }

            # Crear tokens
            token_pair = self.jwt_handler.create_token_pair(token_data)

            # Guardar refresh token en la base de datos
            refresh_token_record = RefreshToken(
                token=token_pair["refresh_token"],
                user_id=user.id,
                expires_at=datetime.now(timezone.utc).replace(
                    hour=23, minute=59, second=59
                ) + jwt_handler.refresh_token_expire_days,
                user_agent=metadata.get("user_agent"),
                ip_address=metadata.get("ip_address")
            )

            db.add(refresh_token_record)
            await db.commit()

            # Crear respuesta
            response = TokenResponse(
                access_token=token_pair["access_token"],
                refresh_token=token_pair["refresh_token"],
                token_type="bearer",
                expires_in=jwt_handler.access_token_expire_minutes * 60  # En segundos
            )

            metrics_collector.increment_counter(
                "tokens_created_total",
                tags={"user_id": str(user.id)}
            )

            return response

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating tokens for user {user.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token creation failed"
            )

    async def refresh_user_token(self, refresh_token: str, db: AsyncSession) -> str:
        """
        Renovar token de acceso usando refresh token.
        """
        try:
            # Verificar refresh token en la base de datos
            stmt = select(RefreshToken).where(
                RefreshToken.token == refresh_token,
                RefreshToken.revoked == False
            )
            result = await db.execute(stmt)
            token_record = result.scalar_one_or_none()

            if not token_record or not token_record.is_valid():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            # Crear nuevo access token
            new_access_token = self.jwt_handler.refresh_access_token(refresh_token)

            metrics_collector.increment_counter(
                "tokens_refreshed_total",
                tags={"user_id": str(token_record.user_id)}
            )

            return new_access_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )

    async def revoke_refresh_token(self, refresh_token: str, db: AsyncSession) -> bool:
        """
        Revocar refresh token.
        """
        try:
            stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
            result = await db.execute(stmt)
            token_record = result.scalar_one_or_none()

            if token_record:
                token_record.revoke()
                await db.commit()

                metrics_collector.increment_counter(
                    "tokens_revoked_total",
                    tags={"user_id": str(token_record.user_id)}
                )

                return True

            return False

        except Exception as e:
            await db.rollback()
            logger.error(f"Error revoking token: {e}", exc_info=True)
            return False

    async def change_password(self, user: User, password_data: PasswordChange, db: AsyncSession) -> bool:
        """
        Cambiar password de usuario.
        """
        try:
            # Verificar password actual
            if not user.verify_password(password_data.current_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )

            # Establecer nueva password
            user.set_password(password_data.new_password)
            await db.commit()

            # Revocar todos los refresh tokens del usuario por seguridad
            await self.revoke_all_user_tokens(user.id, db)

            metrics_collector.increment_counter(
                "password_changes_total",
                tags={"user_id": str(user.id)}
            )

            logger.info(f"Password changed for user: {user.email}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error changing password for user {user.id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password change failed"
            )

    async def revoke_all_user_tokens(self, user_id: int, db: AsyncSession) -> int:
        """
        Revocar todos los refresh tokens de un usuario.
        """
        try:
            stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            )
            result = await db.execute(stmt)
            tokens = result.scalars().all()

            revoked_count = 0
            for token in tokens:
                token.revoke()
                revoked_count += 1

            await db.commit()

            metrics_collector.increment_counter(
                "tokens_revoked_total",
                tags={"user_id": str(user_id), "reason": "logout_all"},
                value=revoked_count
            )

            return revoked_count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error revoking all tokens for user {user_id}: {e}", exc_info=True)
            return 0

    async def get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """
        Obtener usuario por email.
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email: {e}", exc_info=True)
            return None

    async def get_user_by_username(self, username: str, db: AsyncSession) -> Optional[User]:
        """
        Obtener usuario por username.
        """
        try:
            stmt = select(User).where(User.username == username)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username: {e}", exc_info=True)
            return None

    async def get_user_by_id(self, user_id: int, db: AsyncSession) -> Optional[User]:
        """
        Obtener usuario por ID.
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}", exc_info=True)
            return None

    async def verify_user_email(self, verification_token: str, db: AsyncSession) -> bool:
        """
        Verificar email de usuario usando token.
        """
        try:
            stmt = select(User).where(User.verification_token == verification_token)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return False

            user.is_verified = True
            user.verification_token = None
            await db.commit()

            metrics_collector.increment_counter(
                "email_verifications_total",
                tags={"user_id": str(user.id)}
            )

            logger.info(f"Email verified for user: {user.email}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error verifying email: {e}", exc_info=True)
            return False

    async def get_user_stats(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Obtener estadísticas de usuario.
        """
        try:
            user = await self.get_user_by_id(user_id, db)
            if not user:
                return {}

            # Contar refresh tokens activos
            stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False
            )
            result = await db.execute(stmt)
            active_sessions = len(result.scalars().all())

            return {
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at,
                "last_login": user.last_login,
                "active_sessions": active_sessions,
                "is_verified": user.is_verified,
                "is_active": user.is_active
            }

        except Exception as e:
            logger.error(f"Error getting user stats: {e}", exc_info=True)
            return {}


# Instancia global del servicio
auth_service = AuthService()