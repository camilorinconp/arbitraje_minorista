# backend/tests/test_auth_critical.py

import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from fastapi import status
import tempfile
import os

from backend.main import app
from backend.auth.models import Base, User, RefreshToken
from backend.auth.service import auth_service
from backend.auth.schemas import UserCreate, UserLogin
from backend.services.database import get_db_session
from backend.core.config import Settings

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_auth.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()
    try:
        os.remove("./test_auth.db")
    except FileNotFoundError:
        pass


@pytest.fixture
async def db_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency for testing."""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def test_user_data():
    """Test user data."""
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="TestPassword123!",
        password_confirm="TestPassword123!",
        full_name="Test User"
    )


@pytest.fixture
async def created_user(db_session, test_user_data):
    """Create a test user in the database."""
    user = await auth_service.create_user(test_user_data, db_session)
    return user


class TestUserRegistration:
    """Test user registration functionality."""

    async def test_user_registration_success(self, client, test_user_data):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json=test_user_data.model_dump()
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == test_user_data.email
        assert data["username"] == test_user_data.username
        assert data["full_name"] == test_user_data.full_name
        assert "id" in data
        assert "hashed_password" not in data  # Password should not be returned

    async def test_user_registration_duplicate_email(self, client, test_user_data, created_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/auth/register",
            json=test_user_data.model_dump()
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    async def test_user_registration_weak_password(self, client):
        """Test registration with weak password."""
        weak_password_data = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",  # Too weak
            "password_confirm": "123",
            "full_name": "Weak User"
        }

        response = client.post("/auth/register", json=weak_password_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_user_registration_password_mismatch(self, client):
        """Test registration with password confirmation mismatch."""
        mismatch_data = {
            "email": "mismatch@example.com",
            "username": "mismatchuser",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
            "full_name": "Mismatch User"
        }

        response = client.post("/auth/register", json=mismatch_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login functionality."""

    async def test_login_success(self, client, created_user):
        """Test successful login."""
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_invalid_credentials(self, client, created_user):
        """Test login with invalid credentials."""
        login_data = {
            "email": created_user.email,
            "password": "WrongPassword123!"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "incorrect" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_inactive_user(self, client, db_session, created_user):
        """Test login with inactive user."""
        # Deactivate user
        created_user.is_active = False
        await db_session.commit()

        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenOperations:
    """Test JWT token operations."""

    async def test_token_refresh_success(self, client, created_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Refresh token
        refresh_data = {
            "refresh_token": tokens["refresh_token"]
        }

        response = client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_token_refresh_invalid_token(self, client):
        """Test token refresh with invalid token."""
        refresh_data = {
            "refresh_token": "invalid_token_here"
        }

        response = client.post("/auth/refresh", json=refresh_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_protected_endpoint_with_valid_token(self, client, created_user):
        """Test accessing protected endpoint with valid token."""
        # Login to get token
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Access protected endpoint
        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.get("/auth/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == created_user.email

    async def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {
            "Authorization": "Bearer invalid_token_here"
        }

        response = client.get("/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRoleBasedAccess:
    """Test role-based access control."""

    async def test_admin_only_endpoint_as_admin(self, client, db_session):
        """Test admin endpoint access as admin user."""
        # Create admin user
        admin_data = UserCreate(
            email="admin@example.com",
            username="admin",
            password="AdminPassword123!",
            password_confirm="AdminPassword123!",
            full_name="Admin User"
        )

        admin_user = await auth_service.create_user(admin_data, db_session)
        admin_user.role = "admin"
        await db_session.commit()

        # Login as admin
        login_data = {
            "email": admin_user.email,
            "password": "AdminPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Access admin endpoint
        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.get("/auth/users", headers=headers)

        assert response.status_code == status.HTTP_200_OK

    async def test_admin_only_endpoint_as_regular_user(self, client, created_user):
        """Test admin endpoint access as regular user."""
        # Login as regular user
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Try to access admin endpoint
        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.get("/auth/users", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPasswordOperations:
    """Test password-related operations."""

    async def test_password_change_success(self, client, created_user):
        """Test successful password change."""
        # Login to get token
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Change password
        password_change_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!"
        }

        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.post("/auth/change-password", json=password_change_data, headers=headers)

        assert response.status_code == status.HTTP_200_OK

    async def test_password_change_wrong_current_password(self, client, created_user):
        """Test password change with wrong current password."""
        # Login to get token
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Try to change password with wrong current password
        password_change_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!"
        }

        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.post("/auth/change-password", json=password_change_data, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSecurityFeatures:
    """Test security features."""

    async def test_logout_invalidates_refresh_token(self, client, created_user):
        """Test that logout invalidates refresh tokens."""
        # Login to get tokens
        login_data = {
            "email": created_user.email,
            "password": "TestPassword123!"
        }

        login_response = client.post("/auth/login", json=login_data)
        tokens = login_response.json()

        # Logout
        headers = {
            "Authorization": f"Bearer {tokens['access_token']}"
        }

        response = client.post("/auth/logout", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Try to use refresh token after logout
        refresh_data = {
            "refresh_token": tokens["refresh_token"]
        }

        response = client.post("/auth/refresh", json=refresh_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])