# backend/core/sentry_init.py

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from .config import settings


def init_sentry():
    """Initialize Sentry error monitoring."""
    if not settings.sentry_dsn:
        return

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env.value,
        integrations=[
            FastApiIntegration(auto_enable=True),
            SqlalchemyIntegration(),
            AsyncPGIntegration(),
            HttpxIntegration(),
            logging_integration,
        ],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send PII for privacy
        release=f"{settings.app_name}@{settings.app_version}",
        before_send=before_send_filter,
    )


def before_send_filter(event, hint):
    """Filter sensitive data before sending to Sentry."""
    # Remove sensitive authentication data
    if 'request' in event:
        headers = event['request'].get('headers', {})
        if 'Authorization' in headers:
            headers['Authorization'] = '[Filtered]'
        if 'Cookie' in headers:
            headers['Cookie'] = '[Filtered]'

    # Filter database URLs from exceptions
    if 'exception' in event:
        for exception in event['exception']['values']:
            if 'value' in exception:
                # Replace database URLs in error messages
                if 'postgresql' in exception['value']:
                    exception['value'] = exception['value'].replace(
                        settings.database_url,
                        'postgresql://[filtered]@[filtered]/[database]'
                    )

    return event


def capture_exception_with_context(exception: Exception, user_id: str = None, extra_context: dict = None):
    """Capture exception with additional context."""
    with sentry_sdk.configure_scope() as scope:
        if user_id:
            scope.user = {"id": user_id}

        if extra_context:
            for key, value in extra_context.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_exception(exception)


def capture_message_with_context(message: str, level: str = "info", user_id: str = None, extra_context: dict = None):
    """Capture message with additional context."""
    with sentry_sdk.configure_scope() as scope:
        if user_id:
            scope.user = {"id": user_id}

        if extra_context:
            for key, value in extra_context.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_message(message, level=level)