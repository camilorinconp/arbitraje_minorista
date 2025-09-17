# backend/auth/__init__.py

from .models import User, RefreshToken
from .jwt_handler import jwt_handler
from .middleware import (
    get_current_user,
    get_current_active_user,
    get_current_verified_user,
    get_current_admin_user,
    get_current_superuser,
    require_permission,
    require_role,
    auth_middleware
)
from .service import auth_service
from .schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    PasswordChange,
    MessageResponse
)

__all__ = [
    # Models
    "User",
    "RefreshToken",

    # JWT Handler
    "jwt_handler",

    # Middleware & Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_current_admin_user",
    "get_current_superuser",
    "require_permission",
    "require_role",
    "auth_middleware",

    # Service
    "auth_service",

    # Schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "PasswordChange",
    "MessageResponse"
]