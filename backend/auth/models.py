# backend/auth/models.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from passlib.context import CryptContext
import uuid

from ..models.base import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """
    Modelo de usuario para autenticación y autorización.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Estado del usuario
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Roles y permisos
    role = Column(String(50), default="user", nullable=False)  # user, admin, scraper

    # Metadatos
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Para verificación de email
    verification_token = Column(String(255), nullable=True)

    # Para reset de password
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    def verify_password(self, password: str) -> bool:
        """Verificar password."""
        return pwd_context.verify(password, self.hashed_password)

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)

    def set_password(self, password: str) -> None:
        """Establecer password hasheado."""
        self.hashed_password = self.hash_password(password)

    def generate_verification_token(self) -> str:
        """Generar token de verificación."""
        token = str(uuid.uuid4())
        self.verification_token = token
        return token

    def generate_reset_token(self) -> str:
        """Generar token de reset de password."""
        token = str(uuid.uuid4())
        self.reset_token = token
        self.reset_token_expires = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
        return token

    def clear_reset_token(self) -> None:
        """Limpiar token de reset."""
        self.reset_token = None
        self.reset_token_expires = None

    def is_reset_token_valid(self) -> bool:
        """Verificar si el token de reset es válido."""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return datetime.now(timezone.utc) < self.reset_token_expires

    def has_permission(self, permission: str) -> bool:
        """Verificar si el usuario tiene un permiso específico."""
        if self.is_superuser:
            return True

        # Definir permisos por rol
        role_permissions = {
            "admin": ["read", "write", "delete", "scrape", "manage_users"],
            "scraper": ["read", "write", "scrape"],
            "user": ["read"]
        }

        return permission in role_permissions.get(self.role, [])

    def can_access_endpoint(self, endpoint: str) -> bool:
        """Verificar si el usuario puede acceder a un endpoint específico."""
        if self.is_superuser:
            return True

        # Mapeo de endpoints a permisos requeridos
        endpoint_permissions = {
            "/scraper": "scrape",
            "/api/productos": "read",
            "/api/minoristas": "read",
            "/api/admin": "manage_users",
            "/observability": "read"
        }

        required_permission = endpoint_permissions.get(endpoint)
        if not required_permission:
            return True  # Endpoint público

        return self.has_permission(required_permission)

    def update_last_login(self) -> None:
        """Actualizar último login."""
        self.last_login = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class RefreshToken(Base):
    """
    Modelo para tokens de refresh JWT.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)  # Foreign key to users
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked = Column(Boolean, default=False, nullable=False)

    # Metadatos del dispositivo/sesión
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible

    def is_valid(self) -> bool:
        """Verificar si el token es válido."""
        if self.revoked:
            return False
        return datetime.now(timezone.utc) < self.expires_at

    def revoke(self) -> None:
        """Revocar el token."""
        self.revoked = True

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"