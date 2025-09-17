# backend/auth/sentry_utils.py

from backend.core.sentry_init import capture_exception_with_context, capture_message_with_context
from .models import User
from typing import Optional, Dict, Any


def capture_auth_error(
    exception: Exception,
    user: Optional[User] = None,
    operation: str = "unknown",
    extra_data: Optional[Dict[str, Any]] = None
):
    """Capture authentication-related errors with proper context."""
    context = {
        "operation": operation,
        "user_role": user.role if user else None,
        "user_verified": user.is_verified if user else None,
    }

    if extra_data:
        context.update(extra_data)

    capture_exception_with_context(
        exception=exception,
        user_id=str(user.id) if user else None,
        extra_context=context
    )


def capture_auth_event(
    message: str,
    level: str = "info",
    user: Optional[User] = None,
    operation: str = "unknown",
    extra_data: Optional[Dict[str, Any]] = None
):
    """Capture authentication events with proper context."""
    context = {
        "operation": operation,
        "user_role": user.role if user else None,
    }

    if extra_data:
        context.update(extra_data)

    capture_message_with_context(
        message=message,
        level=level,
        user_id=str(user.id) if user else None,
        extra_context=context
    )


def capture_failed_login(email: str, reason: str, ip_address: str = None):
    """Capture failed login attempts for security monitoring."""
    context = {
        "operation": "login_failed",
        "failure_reason": reason,
        "email": email,  # Consider hashing in production
        "ip_address": ip_address,
    }

    capture_message_with_context(
        message=f"Failed login attempt for {email}: {reason}",
        level="warning",
        extra_context=context
    )


def capture_password_reset_request(email: str, ip_address: str = None):
    """Capture password reset requests for security monitoring."""
    context = {
        "operation": "password_reset_request",
        "email": email,
        "ip_address": ip_address,
    }

    capture_message_with_context(
        message=f"Password reset requested for {email}",
        level="info",
        extra_context=context
    )


def capture_token_refresh(user: User, old_token_id: str = None):
    """Capture token refresh events."""
    context = {
        "operation": "token_refresh",
        "old_token_id": old_token_id,
    }

    capture_message_with_context(
        message="Access token refreshed",
        level="info",
        user_id=str(user.id),
        extra_context=context
    )