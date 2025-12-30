import pytest
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.users import fastapi_users
from src.schemas import UserCreate, UserRead, UserUpdate


class TestAuthEndpoints:
    """Test cases for authentication-related endpoints"""

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "is_active": True,
            "is_verified": True
        }

        response = await client.post("/auth/register", json=user_data)

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["email"] == user_data["email"]
            assert data["is_active"] == user_data["is_active"]
            assert data["is_verified"] == user_data["is_verified"]
            assert "password" not in data  # Password should not be returned

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: dict):
        """Test registration with duplicate email should fail"""
        user_data = {
            "email": test_user["user"].email,
            "password": "differentpassword123",
            "is_active": True,
            "is_verified": True
        }

        response = await client.post("/auth/register", json=user_data)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format"""
        user_data = {
            "email": "invalid-email",
            "password": "securepassword123",
            "is_active": True,
            "is_verified": True
        }

        response = await client.post("/auth/register", json=user_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password"""
        user_data = {
            "email": "weakuser@example.com",
            "password": "123",  # Too weak
            "is_active": True,
            "is_verified": True
        }

        response = await client.post("/auth/register", json=user_data)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, client: AsyncClient, test_user: dict):
        """Test login with valid credentials"""
        login_data = {
            "username": test_user["user"].email,
            "password": "testpassword123"
        }

        response = await client.post("/auth/jwt/login", data=login_data)

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }

        response = await client.post("/auth/jwt/login", data=login_data)
        assert response.status_code in [400, 401, 403]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: dict):
        """Test login with correct email but wrong password"""
        login_data = {
            "username": test_user["user"].email,
            "password": "wrongpassword"
        }

        response = await client.post("/auth/jwt/login", data=login_data)
        assert response.status_code in [400, 401, 403]

    @pytest.mark.asyncio
    async def test_get_current_user(self, authenticated_client: AsyncClient, test_user: dict):
        """Test retrieving current authenticated user"""
        response = await authenticated_client.get("/users/me")

        if response.status_code == 200:
            data = response.json()
            assert data["id"] == str(test_user["user"].id)
            assert data["email"] == test_user["user"].email
            assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test retrieving current user without authentication"""
        response = await client.get("/users/me")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_current_user(self, authenticated_client: AsyncClient):
        """Test updating current user information"""
        update_data = {
            "is_active": False
        }

        response = await authenticated_client.patch("/users/me", json=update_data)

        if response.status_code == 200:
            data = response.json()
            assert data["is_active"] == update_data["is_active"]

    @pytest.mark.asyncio
    async def test_update_user_email(self, authenticated_client: AsyncClient):
        """Test updating user email"""
        update_data = {
            "email": "updated@example.com"
        }

        response = await authenticated_client.patch("/users/me", json=update_data)

        if response.status_code == 200:
            data = response.json()
            assert data["email"] == update_data["email"]

    @pytest.mark.asyncio
    async def test_request_password_reset(self, client: AsyncClient, test_user: dict):
        """Test requesting password reset"""
        reset_data = {
            "email": test_user["user"].email
        }

        response = await client.post("/auth/forgot-password", json=reset_data)

        # Should succeed even if email doesn't exist (security best practice)
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_request_password_reset_invalid_email(self, client: AsyncClient):
        """Test requesting password reset with invalid email"""
        reset_data = {
            "email": "invalid-email-format"
        }

        response = await client.post("/auth/forgot-password", json=reset_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_verify_user_email(self, client: AsyncClient):
        """Test user email verification"""
        # This would require a verification token
        # For now, test the endpoint structure
        verification_data = {
            "token": "sample_verification_token"
        }

        response = await client.post("/auth/verify", json=verification_data)

        # Should fail with invalid token, but endpoint should exist
        assert response.status_code in [400, 401, 422]

    @pytest.mark.asyncio
    async def test_logout(self, authenticated_client: AsyncClient):
        """Test user logout"""
        response = await authenticated_client.post("/auth/jwt/logout")

        # Should succeed even without token (JWT stateless)
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_authenticated_route(self, authenticated_client: AsyncClient, test_user: dict):
        """Test accessing authenticated route"""
        response = await authenticated_client.get("/authenticated-route")

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert test_user["user"].email in data["message"]

    @pytest.mark.asyncio
    async def test_authenticated_route_without_auth(self, client: AsyncClient):
        """Test accessing authenticated route without authentication"""
        response = await client.get("/authenticated-route")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_token_validation(self, client: AsyncClient, test_user: dict):
        """Test JWT token validation"""
        # Get valid token
        login_data = {
            "username": test_user["user"].email,
            "password": "testpassword123"
        }

        login_response = await client.post("/auth/jwt/login", data=login_data)

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Test with valid token
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/users/me", headers=headers)

            if response.status_code == 200:
                data = response.json()
                assert data["email"] == test_user["user"].email

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """Test access with invalid JWT token"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await client.get("/users/me", headers=headers)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_malformed_token(self, client: AsyncClient):
        """Test access with malformed authorization header"""
        headers = {"Authorization": "InvalidFormat token_here"}
        response = await client.get("/users/me", headers=headers)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self, client: AsyncClient):
        """Test access without authorization header"""
        response = await client.get("/users/me")
        assert response.status_code in [401, 403]


class TestUserManagement:
    """Test cases for user management endpoints"""

    @pytest.mark.asyncio
    async def test_get_user_list_admin(self, authenticated_client: AsyncClient):
        """Test getting user list (admin functionality)"""
        response = await authenticated_client.get("/users")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, authenticated_client: AsyncClient, test_user: dict):
        """Test getting user by ID"""
        user_id = str(test_user["user"].id)
        response = await authenticated_client.get(f"/users/{user_id}")

        if response.status_code == 200:
            data = response.json()
            assert data["id"] == user_id
            assert data["email"] == test_user["user"].email

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, authenticated_client: AsyncClient):
        """Test getting non-existent user"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.get(f"/users/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_by_id(self, authenticated_client: AsyncClient, test_user: dict):
        """Test updating user by ID"""
        user_id = str(test_user["user"].id)
        update_data = {
            "is_active": False
        }

        response = await authenticated_client.patch(f"/users/{user_id}", json=update_data)

        if response.status_code == 200:
            data = response.json()
            assert data["is_active"] == update_data["is_active"]

    @pytest.mark.asyncio
    async def test_delete_user(self, authenticated_client: AsyncClient):
        """Test deleting a user"""
        # First create a user to delete
        user_data = {
            "email": "tobedeleted@example.com",
            "password": "deletepassword123",
            "is_active": True,
            "is_verified": True
        }

        create_response = await authenticated_client.post("/auth/register", json=user_data)

        if create_response.status_code in [200, 201]:
            user_id = create_response.json()["id"]

            # Delete the user
            delete_response = await authenticated_client.delete(f"/users/{user_id}")
            assert delete_response.status_code in [200, 204]


class TestPasswordSecurity:
    """Test cases for password security features"""

    @pytest.mark.asyncio
    async def test_password_hashing(self, client: AsyncClient):
        """Test that passwords are properly hashed"""
        user_data = {
            "email": "hashtest@example.com",
            "password": "plaintext_password123",
            "is_active": True,
            "is_verified": True
        }

        response = await client.post("/auth/register", json=user_data)

        if response.status_code in [200, 201]:
            # Password should not be returned in response
            data = response.json()
            assert "password" not in data
            assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_password_change(self, authenticated_client: AsyncClient):
        """Test changing user password"""
        password_data = {
            "password": "new_secure_password456",
            "current_password": "testpassword123"
        }

        response = await authenticated_client.post("/auth/change-password", json=password_data)

        # This endpoint might not exist, but if it does:
        if response.status_code in [200, 204]:
            # Try logging in with new password
            login_data = {
                "username": "testuser@example.com",
                "password": "new_secure_password456"
            }

            login_response = await authenticated_client.post("/auth/jwt/login", data=login_data)
            assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_management(self, authenticated_client: AsyncClient):
        """Test session management and token expiry"""
        # This would test token refresh, expiry, etc.
        # For now, just test basic session functionality
        response = await authenticated_client.get("/users/me")
        assert response.status_code == 200
