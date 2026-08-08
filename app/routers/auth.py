from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from app.utils.dependency import get_current_user

from app.models.user import user_collection
from app.schemas.user import UserRegister, UserLogin

from app.utils.hash import (
    hash_password,
    verify_password
)

from app.utils.jwt import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =========================
# REGISTER
# =========================

@router.post("/register")
async def register(user: UserRegister):

    # Check existing email
    existing_user = await user_collection.find_one(
        {"email": user.email}
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = hash_password(
        user.password
    )

    # User document
    new_user = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password
    }

    # Save user
    result = await user_collection.insert_one(
        new_user
    )

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


# =========================
# LOGIN
# =========================

@router.post("/login")
async def login(user: UserLogin):

    # Find user by email
    db_user = await user_collection.find_one(
        {"email": user.email}
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check password
    if not verify_password(
        user.password,
        db_user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Generate JWT
    access_token = create_access_token(
        {
            "sub": str(db_user["_id"])
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def get_user_details(
    current_user=Depends(get_current_user)
):

    user_id = current_user["sub"]

    user = await user_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"]
    }