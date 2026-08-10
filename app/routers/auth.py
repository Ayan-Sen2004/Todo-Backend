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
        "password": hashed_password,
       "role": user.role or "user"
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
    hashed_password = db_user.get("password")
    if not hashed_password or not verify_password(
        user.password,
        hashed_password
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
        "token_type": "bearer",
        "role": db_user.get("role", "user"),
        "username": db_user.get("username") or db_user.get("email")
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
        "email": user["email"],
        "role": user.get("role", "user")
    }

@router.get("/users")
async def get_all_users(current_user=Depends(get_current_user)):
    user_id = current_user["sub"]
    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admins only"
        )
    
    users = []
    async for u in user_collection.find():
        users.append({
            "id": str(u["_id"]),
            "username": u["username"],
            "email": u["email"],
            "role": u.get("role", "user")
        })
    return users


# =========================
# RESET PASSWORD (Admin only)
# =========================
from app.schemas.user import ResetPassword

@router.post("/reset-password")
async def reset_password(
    data: ResetPassword,
    current_user=Depends(get_current_user)
):
    admin_id = current_user["sub"]
    admin_user = await user_collection.find_one({"_id": ObjectId(admin_id)})
    if not admin_user or admin_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admins only"
        )
    
    target_user = await user_collection.find_one({"_id": ObjectId(data.user_id)})
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Hashing new password
    hashed = hash_password(data.new_password)
    
    await user_collection.update_one(
        {"_id": ObjectId(data.user_id)},
        {"$set": {"password": hashed}}
    )
    
    return {"message": "User password reset successfully"}


# =========================
# DELETE USER (Admin only)
# =========================
@router.delete("/users/{delete_user_id}")
async def delete_user(
    delete_user_id: str,
    current_user=Depends(get_current_user)
):
    admin_id = current_user["sub"]
    admin_user = await user_collection.find_one({"_id": ObjectId(admin_id)})
    if not admin_user or admin_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admins only"
        )
        
    if admin_id == delete_user_id:
        raise HTTPException(
            status_code=400,
            detail="Admins cannot delete themselves"
        )
        
    result = await user_collection.delete_one({"_id": ObjectId(delete_user_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
        
    # Also clean up todos allocated to this user
    from app.models.todo import todo_collection
    await todo_collection.delete_many({"user_id": delete_user_id})
    
    return {"message": "User and their tasks deleted successfully"}


# =========================
# UPDATE USER (Admin only)
# =========================
from app.schemas.user import UserUpdate

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user=Depends(get_current_user)
):
    admin_id = current_user["sub"]
    admin_user = await user_collection.find_one({"_id": ObjectId(admin_id)})
    if not admin_user or admin_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admins only"
        )
    
    target_user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    update_data = {}
    if data.username is not None:
        update_data["username"] = data.username
    if data.email is not None:
        existing_email = await user_collection.find_one({"email": data.email, "_id": {"$ne": ObjectId(user_id)}})
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        update_data["email"] = data.email
    if data.password is not None and data.password.strip() != "":
        update_data["password"] = hash_password(data.password)
    if data.role is not None:
        update_data["role"] = data.role
        
    if update_data:
        await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
    return {"message": "User updated successfully"}