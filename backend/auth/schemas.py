# backend/auth/schemas.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """Schema base para usuario."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema para crear usuario."""
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        """Validar username."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()

    @validator('password')
    def validate_password(cls, v):
        """Validar password."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')

        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Verificar que las passwords coincidan."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserUpdate(BaseModel):
    """Schema para actualizar usuario."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    @validator('username')
    def validate_username(cls, v):
        """Validar username."""
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower() if v else v


class UserResponse(UserBase):
    """Schema para respuesta de usuario."""
    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool
    role: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema para login de usuario."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema para respuesta de token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class TokenRefresh(BaseModel):
    """Schema para refresh de token."""
    refresh_token: str


class PasswordChange(BaseModel):
    """Schema para cambio de password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validar nueva password."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')

        return v

    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        """Verificar que las passwords coincidan."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordReset(BaseModel):
    """Schema para reset de password."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema para confirmar reset de password."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validar nueva password."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')

        return v

    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        """Verificar que las passwords coincidan."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class EmailVerification(BaseModel):
    """Schema para verificación de email."""
    token: str


class UserPermissions(BaseModel):
    """Schema para permisos de usuario."""
    permissions: list[str]
    role: str
    is_superuser: bool


class UserStats(BaseModel):
    """Schema para estadísticas de usuario."""
    total_requests: int = 0
    last_activity: Optional[datetime] = None
    created_at: datetime
    login_count: int = 0


class ApiKeyCreate(BaseModel):
    """Schema para crear API key."""
    name: str = Field(..., min_length=3, max_length=100, description="Name for the API key")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (max 365)")
    permissions: list[str] = Field(default=["read"], description="List of permissions for this API key")


class ApiKeyResponse(BaseModel):
    """Schema para respuesta de API key."""
    id: int
    name: str
    key: str = Field(..., description="API key value (only shown once)")
    permissions: list[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class ApiKeyInfo(BaseModel):
    """Schema para información de API key (sin mostrar la key)."""
    id: int
    name: str
    permissions: list[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    last_used: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginHistory(BaseModel):
    """Schema para historial de login."""
    id: int
    user_id: int
    login_time: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool

    class Config:
        from_attributes = True


class SecurityEvent(BaseModel):
    """Schema para eventos de seguridad."""
    event_type: str
    description: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    severity: str = Field(default="info", regex="^(low|medium|high|critical)$")


class MessageResponse(BaseModel):
    """Schema para respuestas simples con mensaje."""
    message: str
    success: bool = True