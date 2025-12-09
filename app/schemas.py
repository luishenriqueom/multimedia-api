from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    bio: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None

class MediaCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = False

class MediaOut(BaseModel):
    id: int
    title: Optional[str]
    description: Optional[str]
    filename: str
    mimetype: Optional[str]
    size: Optional[int]
    is_public: bool
    owner_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True
