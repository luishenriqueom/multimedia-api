from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
from typing import Optional, List
import hashlib
import bcrypt
from sqlalchemy import or_

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# Users

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    pw_bytes = user.password.encode("utf-8")
    sha = hashlib.sha256(pw_bytes).digest()
    hashed = bcrypt.hashpw(sha, bcrypt.gensalt()).decode("utf-8")
    db_user = models.User(email=user.email, hashed_password=hashed, full_name=user.full_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    pw_bytes = password.encode("utf-8")
    sha = hashlib.sha256(pw_bytes).digest()
    try:
        if bcrypt.checkpw(sha, user.hashed_password.encode("utf-8")):
            return user
    except Exception:
        # fallback to passlib verification for legacy hashes
        try:
            if pwd_context.verify(password, user.hashed_password):
                # re-hash under the new scheme and store
                new_hash = bcrypt.hashpw(sha, bcrypt.gensalt()).decode("utf-8")
                user.hashed_password = new_hash
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
        except Exception:
            return None
    return None

def update_user(db: Session, db_user: models.User, updates: schemas.UserUpdate) -> models.User:
    if updates.full_name is not None:
        db_user.full_name = updates.full_name
    # Allow updating username if provided
    if getattr(updates, 'username', None) is not None:
        # Normalize empty strings to None
        username_val = updates.username.strip() if isinstance(updates.username, str) else updates.username
        db_user.username = username_val or None
    if updates.bio is not None:
        db_user.bio = updates.bio
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def change_user_password(db: Session, db_user: models.User, new_password: str) -> models.User:
    """Change the user's password (hashes with the same scheme as create_user)."""
    if not new_password:
        raise ValueError("new_password must not be empty")
    pw_bytes = new_password.encode("utf-8")
    sha = hashlib.sha256(pw_bytes).digest()
    hashed = bcrypt.hashpw(sha, bcrypt.gensalt()).decode("utf-8")
    db_user.hashed_password = hashed
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Media

def create_media(db: Session, owner: models.User, filename: str, s3_key: str, mimetype: str, size: int, meta: schemas.MediaCreate, media_type: str = 'other') -> models.Media:
    db_media = models.Media(
        description=meta.description,
        filename=filename,
        s3_key=s3_key,
        mimetype=mimetype,
        size=size,
        is_public=meta.is_public or False,
        media_type=media_type,
        owner=owner
    )
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media


def create_thumbnail(db: Session, media: models.Media, s3_key: str, width: int | None, height: int | None, size: int | None, purpose: str = 'listing') -> models.Thumbnail:
    thumb = models.Thumbnail(
        media_id=media.id,
        s3_key=s3_key,
        width=width,
        height=height,
        size=size,
        purpose=purpose
    )
    db.add(thumb)
    db.commit()
    db.refresh(thumb)
    return thumb


def create_image_metadata(db: Session, media: models.Media, width: int | None, height: int | None, color_depth: int | None, dpi_x: int | None, dpi_y: int | None, exif: dict | None, main_thumbnail_id: int | None = None) -> models.ImageMetadata:
    img_md = models.ImageMetadata(
        media_id=media.id,
        width=width,
        height=height,
        color_depth=color_depth,
        dpi_x=dpi_x,
        dpi_y=dpi_y,
        exif=exif,
        main_thumbnail_id=main_thumbnail_id
    )
    db.add(img_md)
    db.commit()
    db.refresh(img_md)
    return img_md

def create_video_metadata(db: Session, media: models.Media, duration_seconds: float | None = None, width: int | None = None, height: int | None = None, frame_rate: float | None = None, video_codec: str | None = None, audio_codec: str | None = None, bitrate: int | None = None, genero: str | None = None, main_thumbnail_id: int | None = None, url_1080: str | None = None, url_720: str | None = None, url_480: str | None = None) -> models.VideoMetadata:
    vid_md = models.VideoMetadata(
        media_id=media.id,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
        frame_rate=frame_rate,
        video_codec=video_codec,
        audio_codec=audio_codec,
        bitrate=bitrate,
        genero=genero,
        main_thumbnail_id=main_thumbnail_id,
        url_1080=url_1080,
        url_720=url_720,
        url_480=url_480
    )
    db.add(vid_md)
    db.commit()
    db.refresh(vid_md)
    return vid_md

def create_audio_metadata(db: Session, media: models.Media, duration_seconds: float | None = None, bitrate: int | None = None, sample_rate: int | None = None, channels: int | None = None, genero: str | None = None) -> models.AudioMetadata:
    aud_md = models.AudioMetadata(
        media_id=media.id,
        duration_seconds=duration_seconds,
        bitrate=bitrate,
        sample_rate=sample_rate,
        channels=channels,
        genero=genero
    )
    db.add(aud_md)
    db.commit()
    db.refresh(aud_md)
    return aud_md

def get_media(db: Session, media_id: int) -> Optional[models.Media]:
    return db.query(models.Media).filter(models.Media.id == media_id).first()


def get_listing_thumbnail_key(db: Session, media_id: int) -> Optional[str]:
    """Return the s3_key for the listing thumbnail for a given media, if any."""
    # Prefer thumbnails with purpose='listing'
    thumb = (
        db.query(models.Thumbnail)
        .filter(models.Thumbnail.media_id == media_id, models.Thumbnail.purpose == 'listing')
        .order_by(models.Thumbnail.created_at.desc())
        .first()
    )
    if not thumb:
        # Fallback to any thumbnail for the media
        thumb = (
            db.query(models.Thumbnail)
            .filter(models.Thumbnail.media_id == media_id)
            .order_by(models.Thumbnail.created_at.desc())
            .first()
        )
    return thumb.s3_key if thumb else None

def delete_media(db: Session, media: models.Media):
    db.delete(media)
    db.commit()

def list_media(db: Session, owner_id: int, q: Optional[str]=None, limit: int=50, offset: int=0) -> List[models.Media]:
    """List media belonging to a specific owner. Only returns items owned by `owner_id`.

    This enforces per-user visibility at the DB level.
    """
    query = db.query(models.Media).filter(models.Media.owner_id == owner_id)
    if q:
        term = f"%{q}%"
        query = query.filter(or_(models.Media.filename.ilike(term), models.Media.description.ilike(term)))
    return query.order_by(models.Media.created_at.desc()).limit(limit).offset(offset).all()

# Tags

def get_or_create_tag(db: Session, tag_name: str) -> models.Tag:
    """Get an existing tag by name or create a new one."""
    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
    if not tag:
        tag = models.Tag(name=tag_name)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag

def associate_tags_to_media(db: Session, media: models.Media, tag_names: List[str]):
    """Associate tags to a media item. Creates tags if they don't exist."""
    if not tag_names:
        return
    for tag_name in tag_names:
        tag = get_or_create_tag(db, tag_name.strip())
        if tag not in media.tags:
            media.tags.append(tag)
    db.commit()
    db.refresh(media)

def replace_tags_for_media(db: Session, media: models.Media, tag_names: Optional[List[str]]):
    """Replace all tags for a media item with the provided tags. Creates tags if they don't exist."""
    # Clear existing tags
    media.tags.clear()
    # Add new tags if provided
    if tag_names:
        for tag_name in tag_names:
            tag = get_or_create_tag(db, tag_name.strip())
            media.tags.append(tag)
    db.commit()
    db.refresh(media)

def update_media(db: Session, media: models.Media, description: Optional[str] = None) -> models.Media:
    """Update basic media fields."""
    if description is not None:
        media.description = description
    db.add(media)
    db.commit()
    db.refresh(media)
    return media

def update_video_metadata_genero(db: Session, media: models.Media, genero: Optional[str] = None):
    """Update genero in video metadata."""
    if not media.video_metadata:
        return
    if genero is not None:
        media.video_metadata.genero = genero
        db.add(media.video_metadata)
        db.commit()
        db.refresh(media.video_metadata)

def update_audio_metadata_genero(db: Session, media: models.Media, genero: Optional[str] = None):
    """Update genero in audio metadata."""
    if not media.audio_metadata:
        return
    if genero is not None:
        media.audio_metadata.genero = genero
        db.add(media.audio_metadata)
        db.commit()
        db.refresh(media.audio_metadata)
