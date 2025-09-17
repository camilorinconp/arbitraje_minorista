# backend/auth/jwt_handler.py

import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
from pydantic import ValidationError

from ..core.config import settings

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    Manejador de tokens JWT para autenticación.
    """

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crear token de acceso JWT.
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })

        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crear token de refresh JWT.
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })

        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for user: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create refresh token"
            )

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verificar y decodificar token JWT.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verificar tipo de token
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Verificar expiración
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
                if datetime.now(timezone.utc) >= exp_datetime:
                    logger.warning("Token has expired")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )

            logger.debug(f"Successfully verified {token_type} token for user: {payload.get('sub')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not verify token"
            )

    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Crear par de tokens (access + refresh).
        """
        access_token = self.create_access_token(data=user_data)
        refresh_token = self.create_refresh_token(data=user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Crear nuevo token de acceso usando refresh token.
        """
        try:
            # Verificar refresh token
            payload = self.verify_token(refresh_token, token_type="refresh")

            # Crear nuevo token de acceso con los mismos datos de usuario
            user_data = {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "user_id": payload.get("user_id")
            }

            new_access_token = self.create_access_token(data=user_data)
            logger.info(f"Refreshed access token for user: {payload.get('sub')}")

            return new_access_token

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not refresh token"
            )

    def get_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Obtener payload del token sin verificar expiración (para debugging).
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except Exception as e:
            logger.error(f"Error getting token payload: {e}")
            return None

    def is_token_expired(self, token: str) -> bool:
        """
        Verificar si un token está expirado.
        """
        payload = self.get_token_payload(token)
        if not payload:
            return True

        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True

        exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
        return datetime.now(timezone.utc) >= exp_datetime

    def create_verification_token(self, email: str) -> str:
        """
        Crear token para verificación de email.
        """
        data = {
            "sub": email,
            "purpose": "email_verification"
        }

        # Token de verificación válido por 24 horas
        expires_delta = timedelta(hours=24)

        return self.create_access_token(data=data, expires_delta=expires_delta)

    def verify_email_token(self, token: str) -> str:
        """
        Verificar token de verificación de email.
        """
        try:
            payload = self.verify_token(token, token_type="access")

            if payload.get("purpose") != "email_verification":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid verification token"
                )

            return payload.get("sub")  # email

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying email token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification token"
            )

    def create_password_reset_token(self, email: str) -> str:
        """
        Crear token para reset de password.
        """
        data = {
            "sub": email,
            "purpose": "password_reset"
        }

        # Token de reset válido por 1 hora
        expires_delta = timedelta(hours=1)

        return self.create_access_token(data=data, expires_delta=expires_delta)

    def verify_password_reset_token(self, token: str) -> str:
        """
        Verificar token de reset de password.
        """
        try:
            payload = self.verify_token(token, token_type="access")

            if payload.get("purpose") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid reset token"
                )

            return payload.get("sub")  # email

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying reset token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid reset token"
            )


# Instancia global del manejador JWT
jwt_handler = JWTHandler()