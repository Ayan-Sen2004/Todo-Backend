from pydantic import BaseModel, EmailStr
from typing import Optional

# UserRegister
# UserLogin
# UserResponse

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "user"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str


class ChangePassword(BaseModel):
    new_password: str


class ResetPassword(BaseModel):
    user_id: str
    new_password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

