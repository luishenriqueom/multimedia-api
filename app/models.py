from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    BigInteger,
    Text,
    JSON,
    Enum,
    Numeric,
    Table,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# Association table for tags (N:N)
media_tags = Table(
    "media_tags",
    Base.metadata,
    Column("media_id", Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    # user-visible short username (handle); optional and distinct from full_name
    username = Column(String, unique=False, nullable=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    media = relationship("Media", back_populates="owner", cascade="all, delete-orphan")
    # S3 key for user's avatar (thumbnail or original)
    avatar_s3_key = Column(String, nullable=True)


class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False, unique=True)
    mimetype = Column(String)
    size = Column(BigInteger)
    is_public = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    upload_at = Column(DateTime, default=datetime.utcnow)

    # media_type enum: image, video, audio, other
    media_type = Column(Enum("image", "video", "audio", "other", name="media_type_enum"), nullable=False, default="other")

    owner = relationship("User", back_populates="media")

    # Relationships to specialized metadata
    image_metadata = relationship("ImageMetadata", uselist=False, back_populates="media", cascade="all, delete-orphan")
    video_metadata = relationship("VideoMetadata", uselist=False, back_populates="media", cascade="all, delete-orphan")
    audio_metadata = relationship("AudioMetadata", uselist=False, back_populates="media", cascade="all, delete-orphan")

    thumbnails = relationship("Thumbnail", back_populates="media", cascade="all, delete-orphan")
    renditions = relationship("VideoRendition", back_populates="media", cascade="all, delete-orphan")

    tags = relationship("Tag", secondary=media_tags, back_populates="media")


class Thumbnail(Base):
    __tablename__ = "thumbnails"
    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    s3_key = Column(String, nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    size = Column(BigInteger)
    purpose = Column(String)  # e.g. 'listing', 'preview', 'video-frame'
    created_at = Column(DateTime, default=datetime.utcnow)

    media = relationship("Media", back_populates="thumbnails")


class ImageMetadata(Base):
    __tablename__ = "image_metadata"
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    width = Column(Integer)
    height = Column(Integer)
    color_depth = Column(Integer)
    dpi_x = Column(Integer)
    dpi_y = Column(Integer)
    exif = Column(JSON)
    main_thumbnail_id = Column(Integer, ForeignKey("thumbnails.id", ondelete="SET NULL"))

    media = relationship("Media", back_populates="image_metadata")
    main_thumbnail = relationship("Thumbnail", foreign_keys=[main_thumbnail_id])


class VideoMetadata(Base):
    __tablename__ = "video_metadata"
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    duration_seconds = Column(Numeric)
    width = Column(Integer)
    height = Column(Integer)
    frame_rate = Column(Numeric)
    video_codec = Column(String)
    audio_codec = Column(String)
    bitrate = Column(BigInteger)
    main_thumbnail_id = Column(Integer, ForeignKey("thumbnails.id", ondelete="SET NULL"))
    url_1080 = Column(String)
    url_720 = Column(String)
    url_480 = Column(String)
    genero = Column(String)

    media = relationship("Media", back_populates="video_metadata")
    main_thumbnail = relationship("Thumbnail", foreign_keys=[main_thumbnail_id])


class AudioMetadata(Base):
    __tablename__ = "audio_metadata"
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    duration_seconds = Column(Numeric)
    bitrate = Column(BigInteger)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    genero = Column(String)

    media = relationship("Media", back_populates="audio_metadata")


class VideoRendition(Base):
    __tablename__ = "video_renditions"
    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    resolution = Column(String, nullable=False)  # e.g. '1080p'
    width = Column(Integer)
    height = Column(Integer)
    bitrate = Column(BigInteger)
    s3_key = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    media = relationship("Media", back_populates="renditions")


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    media = relationship("Media", secondary=media_tags, back_populates="tags")

