from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext
from typing import Optional, List
from sqlalchemy import or_

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Users

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed, full_name=user.full_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def update_user(db: Session, db_user: models.User, updates: schemas.UserUpdate) -> models.User:
    if updates.full_name is not None:
        db_user.full_name = updates.full_name
    if updates.bio is not None:
        db_user.bio = updates.bio
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Media

def create_media(db: Session, owner: models.User, filename: str, s3_key: str, mimetype: str, size: int, meta: schemas.MediaCreate) -> models.Media:
    db_media = models.Media(
        title=meta.title,
        description=meta.description,
        filename=filename,
        s3_key=s3_key,
        mimetype=mimetype,
        size=size,
        is_public=meta.is_public or False,
        owner=owner
    )
    db.add(db_media)
    db.commit()
    db.refresh(db_media)
    return db_media

def get_media(db: Session, media_id: int) -> Optional[models.Media]:
    return db.query(models.Media).filter(models.Media.id == media_id).first()

def delete_media(db: Session, media: models.Media):
    db.delete(media)
    db.commit()

def list_media(db: Session, q: Optional[str]=None, limit: int=50, offset: int=0) -> List[models.Media]:
    query = db.query(models.Media)
    if q:
        term = f"%{q}%"
        query = query.filter(or_(models.Media.title.ilike(term), models.Media.description.ilike(term)))
    return query.order_by(models.Media.created_at.desc()).limit(limit).offset(offset).all()
