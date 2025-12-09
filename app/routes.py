from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import crud, schemas, auth, s3_utils, models
from .database import get_db
from datetime import timedelta
import uuid

router = APIRouter()

# Auth endpoints
@router.post('/auth/register', response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail='Email already registered')
    user = crud.create_user(db, user_in)
    return user

@router.post('/auth/login', response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses 'username' field — treat it as the user's email
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail='Incorrect username or password')
    access_token = auth.create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# User profile
@router.get('/users/me', response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put('/users/me', response_model=schemas.UserOut)
def update_users_me(updates: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return crud.update_user(db, current_user, updates)

# Media endpoints
@router.post('/media/upload', response_model=schemas.MediaOut)
def upload_media(
    title: str = Form(None),
    description: str = Form(None),
    is_public: bool = Form(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # generate a unique key
    key = f"media/{uuid.uuid4().hex}_{file.filename}"
    s3_utils.upload_fileobj(file.file, key, file.content_type)
    meta = schemas.MediaCreate(title=title, description=description, is_public=is_public)
    media = crud.create_media(db, current_user, file.filename, key, file.content_type, 0, meta)
    return media

@router.get('/media/', response_model=list[schemas.MediaOut])
def list_media(q: str | None = Query(None), limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    return crud.list_media(db, q=q, limit=limit, offset=offset)

@router.get('/media/{media_id}', response_model=schemas.MediaOut)
def get_media(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    # generate presigned URL
    url = s3_utils.generate_presigned_url(media.s3_key)
    result = media
    # attach url as attribute for client usage (not in schema), client can request the presigned url separately if needed
    return result

@router.get('/media/{media_id}/url')
def media_presigned_url(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    url = s3_utils.generate_presigned_url(media.s3_key)
    if not url:
        raise HTTPException(status_code=500, detail='Could not generate URL')
    return {"url": url}

@router.delete('/media/{media_id}')
def delete_media(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    s3_utils.delete_object(media.s3_key)
    crud.delete_media(db, media)
    return {"ok": True}
