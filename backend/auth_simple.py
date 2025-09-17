# Simple authentication for testing
import json
import os
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import bcrypt
import jwt
from datetime import datetime, timedelta

router = APIRouter()

# Simple file-based user storage for testing
USERS_FILE = "users_simple.json"
SECRET_KEY = "test-secret-key-change-in-production"

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    password_confirm: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str = "user"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds
    user: UserResponse

def load_users() -> Dict[str, Any]:
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"users": [], "next_id": 1}

def save_users(data: Dict[str, Any]):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_data: Dict[str, Any]) -> str:
    """Create JWT token"""
    payload = {
        "sub": str(user_data["id"]),
        "email": user_data["email"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

@router.post("/register", response_model=dict)
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        # Validate passwords match
        if user_data.password != user_data.password_confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las passwords no coinciden"
            )

        # Load existing users
        data = load_users()

        # Check if email already exists
        for user in data["users"]:
            if user["email"] == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este email ya está registrado"
                )
            if user["username"] == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este username ya está en uso"
                )

        # Create new user
        new_user = {
            "id": data["next_id"],
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "password_hash": hash_password(user_data.password),
            "role": "user",
            "created_at": datetime.utcnow().isoformat()
        }

        # Add user and save
        data["users"].append(new_user)
        data["next_id"] += 1
        save_users(data)

        return {
            "success": True,
            "message": "Usuario creado exitosamente",
            "user": {
                "id": new_user["id"],
                "email": new_user["email"],
                "username": new_user["username"],
                "full_name": new_user["full_name"],
                "role": new_user["role"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user and return tokens"""
    try:
        # Load users
        data = load_users()

        # Find user by email
        user = None
        for u in data["users"]:
            if u["email"] == login_data.email:
                user = u
                break

        if not user or not verify_password(login_data.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o password incorrectos"
            )

        # Create tokens
        access_token = create_token(user)
        refresh_token = create_token(user)  # Simplified - same token for both

        # Return response
        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"]
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current user info - returns first admin user for simplicity"""
    try:
        # Load users from database
        data = load_users()

        # For simplicity, return the first admin user
        # In a real implementation, this would decode the JWT token
        for user in data["users"]:
            if user["role"] == "admin":
                return UserResponse(
                    id=user["id"],
                    email=user["email"],
                    username=user["username"],
                    full_name=user["full_name"],
                    role=user["role"]
                )

        # If no admin found, return the first user
        if data["users"]:
            user = data["users"][0]
            return UserResponse(
                id=user["id"],
                email=user["email"],
                username=user["username"],
                full_name=user["full_name"],
                role=user["role"]
            )

        # If no users at all, return error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found"
        )

    except Exception as e:
        print(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting user info"
        )

@router.get("/users/count")
async def get_users_count():
    """Get total number of registered users"""
    data = load_users()
    return {"count": len(data["users"])}