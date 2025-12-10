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
    username: Optional[str]
    bio: Optional[str]
    is_active: bool
    created_at: datetime
    avatar_url: Optional[str] = None

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class MediaCreate(BaseModel):
    description: Optional[str] = None
    is_public: Optional[bool] = False

class ImageUpload(BaseModel):
    description: Optional[str] = None
    is_profile: Optional[bool] = False
    tags: Optional[list[str]] = None

class VideoUpload(BaseModel):
    description: Optional[str] = None
    genero: Optional[str] = None
    tags: Optional[list[str]] = None

class AudioUpload(BaseModel):
    description: Optional[str] = None
    genero: Optional[str] = None
    tags: Optional[list[str]] = None

class ImageUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[list[str]] = None

class VideoUpdate(BaseModel):
    description: Optional[str] = None
    genero: Optional[str] = None
    tags: Optional[list[str]] = None

class AudioUpdate(BaseModel):
    description: Optional[str] = None
    genero: Optional[str] = None
    tags: Optional[list[str]] = None

class MediaOut(BaseModel):
    id: int
    description: Optional[str]
    filename: str
    mimetype: Optional[str]
    size: Optional[int]
    is_public: bool
    owner_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class ImageOut(BaseModel):
    id: int
    description: Optional[str]
    filename: str
    mimetype: Optional[str]
    size: Optional[int]
    created_at: datetime
    width: Optional[int]
    height: Optional[int]
    color_depth: Optional[int]
    dpi_x: Optional[int]
    dpi_y: Optional[int]
    exif: Optional[dict]
    url: Optional[str]
    tags: Optional[list]

    class Config:
        orm_mode = True


class VideoOut(BaseModel):
    id: int
    description: Optional[str]
    filename: str
    mimetype: Optional[str]
    size: Optional[int]
    created_at: datetime
    duration_seconds: Optional[float]
    width: Optional[int]
    height: Optional[int]
    frame_rate: Optional[float]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    bitrate: Optional[int]
    tags: Optional[list]
    genero: Optional[str]
    url_1080: Optional[str]
    url_720: Optional[str]
    url_480: Optional[str]

    class Config:
        orm_mode = True


class AudioOut(BaseModel):
    id: int
    description: Optional[str]
    filename: str
    mimetype: Optional[str]
    size: Optional[int]
    created_at: datetime
    duration_seconds: Optional[float]
    bitrate: Optional[int]
    sample_rate: Optional[int]
    channels: Optional[int]
    tags: Optional[list]
    genero: Optional[str]
    url: Optional[str]

    class Config:
        orm_mode = True
