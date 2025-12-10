from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import crud, schemas, auth, s3_utils, models
from . import utils
from . import video_processing
from . import audio_processing
from .database import get_db
from datetime import timedelta
import uuid
import io
from datetime import datetime
from PIL import Image, ExifTags
import math

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
@router.post('/media/upload/image', response_model=schemas.MediaOut)
def upload_image(
    description: str = Form(None),
    is_profile: bool = Form(False),
    tags: str = Form(None),  # Comma-separated tags
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Validate file type
    mimetype = file.content_type or 'application/octet-stream'
    if not mimetype.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be an image')

    safe_name = utils.sanitize_filename(file.filename)

    # Read the uploaded file into memory (bytes) for processing
    file.file.seek(0)
    file_bytes = file.file.read()
    size_bytes = len(file_bytes)

    # Use user id only as prefix and map by type: {id}/imagens, {id}/profile
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    uid = str(current_user.id)

    def _orig_key_for(prefix: str, name: str) -> str:
        return f"{uid}/{prefix}/{ts}_{uuid.uuid4().hex}_{name}"

    # Profile images can be stored under {id}/profile
    if is_profile:
        orig_key = _orig_key_for('profile', safe_name)
    else:
        orig_key = _orig_key_for('imagens', safe_name)

    # Upload original image to S3
    orig_io = io.BytesIO(file_bytes)
    orig_io.seek(0)
    s3_utils.upload_fileobj(orig_io, orig_key, mimetype)

    # Create media DB record (without is_public)
    meta = schemas.MediaCreate(description=description, is_public=False)
    media = crud.create_media(db, current_user, safe_name, orig_key, mimetype, size_bytes, meta, media_type='image')

    # Associate tags if provided
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if tag_list:
            crud.associate_tags_to_media(db, media, tag_list)

    # Analyze image using Pillow
    img = Image.open(io.BytesIO(file_bytes))
    try:
        width, height = img.size
    except Exception:
        width = None
        height = None

    # Color depth estimation from mode
    mode_to_depth = {
        '1': 1, 'L': 8, 'P': 8, 'RGB': 24, 'RGBA': 32, 'CMYK': 32, 'YCbCr': 24, 'I': 32, 'F': 32
    }
    color_depth = mode_to_depth.get(img.mode)

    # DPI
    dpi = img.info.get('dpi')
    dpi_x = int(dpi[0]) if dpi and len(dpi) > 0 else None
    dpi_y = int(dpi[1]) if dpi and len(dpi) > 1 else None

    # EXIF extraction
    exif_data = {}
    try:
        raw_exif = img._getexif() or {}
        if raw_exif:
            for tag, value in raw_exif.items():
                decoded = ExifTags.TAGS.get(tag, tag)
                exif_data[str(decoded)] = str(value)
    except Exception:
        exif_data = None

    # Generate thumbnail (listing size, e.g., width=320)
    thumb_io = io.BytesIO()
    try:
        thumb = img.copy()
        target_w = 320
        if width and width > target_w:
            # calculate proportional height
            ratio = target_w / float(width)
            target_h = math.floor(height * ratio) if height else None
            thumb.thumbnail((target_w, target_h or target_w))
        else:
            # keep original size if smaller
            thumb.thumbnail((320, 320))

        # Decide thumbnail format: preserve alpha/palette by saving PNG, otherwise JPEG
        need_png = False
        # If original image has alpha channel or is palette-based, prefer PNG
        if thumb.mode in ("RGBA", "LA") or thumb.mode == "P" or img.info.get('transparency') is not None:
            need_png = True

        if need_png:
            # Ensure mode supports alpha if originally had it; convert palette to RGBA to preserve transparency
            if thumb.mode == 'P':
                try:
                    thumb = thumb.convert('RGBA')
                except Exception:
                    thumb = thumb.convert('RGB')
            # Save as PNG to preserve alpha
            thumb.save(thumb_io, format='PNG', compress_level=6)
            thumb_content_type = 'image/png'
        else:
            # Convert to RGB and save as JPEG for smaller thumbnails
            if thumb.mode not in ('RGB',):
                thumb = thumb.convert('RGB')
            thumb.save(thumb_io, format='JPEG', quality=85)
            thumb_content_type = 'image/jpeg'

        thumb_io.seek(0)
        thumb_size = thumb_io.getbuffer().nbytes
        thumb_width, thumb_height = thumb.size
    except Exception:
        thumb_io = None
        thumb_size = None
        thumb_width = None
        thumb_height = None

    # Upload thumbnail to S3
    thumb_key = None
    if thumb_io:
        # Put thumbnails under {id}/imagens/thumbnails for regular images, or {id}/profile/thumbnails for profile
        thumb_prefix = 'profile' if is_profile else 'imagens'
        ext = 'png' if thumb_content_type == 'image/png' else 'jpg'
        thumb_key = f"{uid}/{thumb_prefix}/thumbnails/{ts}_{uuid.uuid4().hex}_{safe_name.rsplit('.',1)[0]}.{ext}"
        s3_utils.upload_fileobj(thumb_io, thumb_key, thumb_content_type)

    # Write thumbnail and image metadata to DB
    thumb_obj = None
    if thumb_key:
        thumb_obj = crud.create_thumbnail(db, media, thumb_key, thumb_width, thumb_height, thumb_size, purpose='listing')

    crud.create_image_metadata(db, media, width, height, color_depth, dpi_x, dpi_y, exif_data, main_thumbnail_id=(thumb_obj.id if thumb_obj else None))

    # Return the media object
    return media


@router.put('/media/image/{media_id}', response_model=schemas.ImageOut)
def update_image(
    media_id: int,
    updates: schemas.ImageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    # Ensure it's an image
    if not (media.mimetype and media.mimetype.startswith('image/')) and media.media_type != 'image':
        raise HTTPException(status_code=400, detail='Media is not an image')

    # Update description if provided
    if updates.description is not None:
        crud.update_media(db, media, description=updates.description)

    # Replace tags if provided
    if updates.tags is not None:
        crud.replace_tags_for_media(db, media, updates.tags)

    # Refresh media to get updated relationships
    db.refresh(media)

    # Build response similar to get_image
    img_md = getattr(media, 'image_metadata', None)
    try:
        url = s3_utils.generate_presigned_url(media.s3_key)
    except Exception:
        url = None

    tags = [t.name for t in (media.tags or [])]

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'width': getattr(img_md, 'width', None) if img_md else None,
        'height': getattr(img_md, 'height', None) if img_md else None,
        'color_depth': getattr(img_md, 'color_depth', None) if img_md else None,
        'dpi_x': getattr(img_md, 'dpi_x', None) if img_md else None,
        'dpi_y': getattr(img_md, 'dpi_y', None) if img_md else None,
        'exif': getattr(img_md, 'exif', None) if img_md else None,
        'url': url,
        'tags': tags,
    }
    return resp


@router.post('/media/upload/video', response_model=schemas.MediaOut)
def upload_video(
    description: str = Form(None),
    genero: str = Form(None),
    tags: str = Form(None),  # Comma-separated tags
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Validate file type
    mimetype = file.content_type or 'application/octet-stream'
    if not mimetype.startswith('video/'):
        raise HTTPException(status_code=400, detail='File must be a video')

    safe_name = utils.sanitize_filename(file.filename)

    # Read the uploaded file into memory (bytes) for processing
    file.file.seek(0)
    file_bytes = file.file.read()
    size_bytes = len(file_bytes)

    # Use user id only as prefix: {id}/videos
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    uid = str(current_user.id)

    def _orig_key_for(prefix: str, name: str) -> str:
        return f"{uid}/{prefix}/{ts}_{uuid.uuid4().hex}_{name}"

    orig_key = _orig_key_for('videos', safe_name)

    # Upload original video to S3
    file.file.seek(0)
    s3_utils.upload_fileobj(file.file, orig_key, mimetype)

    # Create media DB record
    meta = schemas.MediaCreate(description=description, is_public=False)
    media = crud.create_media(db, current_user, safe_name, orig_key, mimetype, size_bytes, meta, media_type='video')

    # Associate tags if provided
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if tag_list:
            crud.associate_tags_to_media(db, media, tag_list)

    # Extract video metadata using ffmpeg
    video_metadata = video_processing.extract_video_metadata(file_bytes)

    # Generate thumbnail
    thumb_io = video_processing.generate_video_thumbnail(file_bytes, timestamp=1.0)
    thumb_obj = None
    thumb_key = None
    
    if thumb_io:
        thumb_width, thumb_height = video_processing.get_thumbnail_dimensions(thumb_io)
        thumb_size = thumb_io.getbuffer().nbytes
        
        # Upload thumbnail to S3
        thumb_key = f"{uid}/videos/thumbnails/{ts}_{uuid.uuid4().hex}_{safe_name.rsplit('.',1)[0]}.jpg"
        thumb_io.seek(0)
        s3_utils.upload_fileobj(thumb_io, thumb_key, 'image/jpeg')
        
        # Create thumbnail record
        thumb_obj = crud.create_thumbnail(
            db, 
            media, 
            thumb_key, 
            thumb_width, 
            thumb_height, 
            thumb_size, 
            purpose='listing'
        )

    # Generate video renditions (480p, 720p, 1080p)
    url_480 = None
    url_720 = None
    url_1080 = None
    
    # Generate 480p version
    rendition_480 = video_processing.generate_video_rendition(file_bytes, target_height=480)
    if rendition_480:
        rendition_480_key = f"{uid}/videos/renditions/{ts}_{uuid.uuid4().hex}_{safe_name.rsplit('.',1)[0]}_480p.mp4"
        rendition_480.seek(0)
        s3_utils.upload_fileobj(rendition_480, rendition_480_key, 'video/mp4')
        url_480 = rendition_480_key
    
    # Generate 720p version
    rendition_720 = video_processing.generate_video_rendition(file_bytes, target_height=720)
    if rendition_720:
        rendition_720_key = f"{uid}/videos/renditions/{ts}_{uuid.uuid4().hex}_{safe_name.rsplit('.',1)[0]}_720p.mp4"
        rendition_720.seek(0)
        s3_utils.upload_fileobj(rendition_720, rendition_720_key, 'video/mp4')
        url_720 = rendition_720_key
    
    # Generate 1080p version
    rendition_1080 = video_processing.generate_video_rendition(file_bytes, target_height=1080)
    if rendition_1080:
        rendition_1080_key = f"{uid}/videos/renditions/{ts}_{uuid.uuid4().hex}_{safe_name.rsplit('.',1)[0]}_1080p.mp4"
        rendition_1080.seek(0)
        s3_utils.upload_fileobj(rendition_1080, rendition_1080_key, 'video/mp4')
        url_1080 = rendition_1080_key

    # Create video metadata with all extracted information
    crud.create_video_metadata(
        db, 
        media, 
        duration_seconds=video_metadata.get('duration_seconds'),
        width=video_metadata.get('width'),
        height=video_metadata.get('height'),
        frame_rate=video_metadata.get('frame_rate'),
        video_codec=video_metadata.get('video_codec'),
        audio_codec=video_metadata.get('audio_codec'),
        bitrate=video_metadata.get('bitrate'),
        genero=genero,
        main_thumbnail_id=thumb_obj.id if thumb_obj else None,
        url_1080=url_1080,
        url_720=url_720,
        url_480=url_480
    )

    return media


@router.post('/media/upload/audio', response_model=schemas.MediaOut)
def upload_audio(
    description: str = Form(None),
    genero: str = Form(None),
    tags: str = Form(None),  # Comma-separated tags
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Validate file type
    mimetype = file.content_type or 'application/octet-stream'
    if not mimetype.startswith('audio/'):
        raise HTTPException(status_code=400, detail='File must be an audio file')

    safe_name = utils.sanitize_filename(file.filename)

    # Read the uploaded file into memory (bytes) for processing
    file.file.seek(0)
    file_bytes = file.file.read()
    size_bytes = len(file_bytes)

    # Use user id only as prefix: {id}/audios
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    uid = str(current_user.id)

    def _orig_key_for(prefix: str, name: str) -> str:
        return f"{uid}/{prefix}/{ts}_{uuid.uuid4().hex}_{name}"

    orig_key = _orig_key_for('audios', safe_name)

    # Upload original audio to S3
    file.file.seek(0)
    s3_utils.upload_fileobj(file.file, orig_key, mimetype)

    # Create media DB record
    meta = schemas.MediaCreate(description=description, is_public=False)
    media = crud.create_media(db, current_user, safe_name, orig_key, mimetype, size_bytes, meta, media_type='audio')

    # Associate tags if provided
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        if tag_list:
            crud.associate_tags_to_media(db, media, tag_list)

    # Extract audio metadata using audio_processing
    audio_metadata = audio_processing.extract_audio_metadata(file_bytes)

    # Create audio metadata with extracted information
    crud.create_audio_metadata(
        db, 
        media, 
        duration_seconds=audio_metadata.get('duration_seconds'),
        bitrate=audio_metadata.get('bitrate'),
        sample_rate=audio_metadata.get('sample_rate'),
        channels=audio_metadata.get('channels'),
        genero=genero
    )

    return media

@router.get('/media/')
def list_media(q: str | None = Query(None), limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Return the current user's media in a simplified JSON format with thumbnail URLs.

    Format per item:
    {
      "filename": "aaaa.jpg",
      "size": 100,
      "mimetype": "image/jpg",
      "thumbnail": "https://...",
      "created_at": "YYYY-MM-DDTHH:MM:SS"
    }
    """
    medias = crud.list_media(db, current_user.id, q=q, limit=limit, offset=offset)
    result = []
    for m in medias:
        # get thumbnail key if any
        thumb_key = crud.get_listing_thumbnail_key(db, m.id)
        thumb_url = None
        if thumb_key:
            thumb_url = s3_utils.generate_presigned_url(thumb_key)

        item = {
            "id": m.id,
            "filename": m.filename,
            "size": m.size,
            "mimetype": m.mimetype,
            "thumbnail": thumb_url,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        result.append(item)
    return result

@router.get('/media/{media_id}', response_model=schemas.MediaOut)
def get_media(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    # ensure the current user owns this media
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    return media




@router.get('/media/image/{media_id}', response_model=schemas.ImageOut)
def get_image(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    # Ensure it's an image
    if not (media.mimetype and media.mimetype.startswith('image/')) and media.media_type != 'image':
        raise HTTPException(status_code=400, detail='Media is not an image')

    img_md = getattr(media, 'image_metadata', None)
    try:
        url = s3_utils.generate_presigned_url(media.s3_key)
    except Exception:
        url = None

    tags = [t.name for t in (media.tags or [])]

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'width': getattr(img_md, 'width', None) if img_md else None,
        'height': getattr(img_md, 'height', None) if img_md else None,
        'color_depth': getattr(img_md, 'color_depth', None) if img_md else None,
        'dpi_x': getattr(img_md, 'dpi_x', None) if img_md else None,
        'dpi_y': getattr(img_md, 'dpi_y', None) if img_md else None,
        'exif': getattr(img_md, 'exif', None) if img_md else None,
        'url': url,
        'tags': tags,
    }
    return resp


@router.get('/media/video/{media_id}', response_model=schemas.VideoOut)
def get_video(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    if not (media.mimetype and media.mimetype.startswith('video/')) and media.media_type != 'video':
        raise HTTPException(status_code=400, detail='Media is not a video')

    vid_md = getattr(media, 'video_metadata', None)
    tags = [t.name for t in (media.tags or [])]
    genero = getattr(vid_md, 'genero', None) if vid_md else None

    # Get S3 keys from video_metadata columns and generate presigned URLs
    s3_key_1080 = getattr(vid_md, 'url_1080', None) if vid_md else None
    s3_key_720 = getattr(vid_md, 'url_720', None) if vid_md else None
    s3_key_480 = getattr(vid_md, 'url_480', None) if vid_md else None

    # Generate presigned URLs for each rendition
    url_1080 = None
    url_720 = None
    url_480 = None
    
    if s3_key_1080:
        try:
            url_1080 = s3_utils.generate_presigned_url(s3_key_1080)
        except Exception:
            url_1080 = None
    
    if s3_key_720:
        try:
            url_720 = s3_utils.generate_presigned_url(s3_key_720)
        except Exception:
            url_720 = None
    
    if s3_key_480:
        try:
            url_480 = s3_utils.generate_presigned_url(s3_key_480)
        except Exception:
            url_480 = None

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'duration_seconds': float(getattr(vid_md, 'duration_seconds')) if vid_md and getattr(vid_md, 'duration_seconds') is not None else None,
        'width': getattr(vid_md, 'width', None) if vid_md else None,
        'height': getattr(vid_md, 'height', None) if vid_md else None,
        'frame_rate': float(getattr(vid_md, 'frame_rate')) if vid_md and getattr(vid_md, 'frame_rate') is not None else None,
        'video_codec': getattr(vid_md, 'video_codec', None) if vid_md else None,
        'audio_codec': getattr(vid_md, 'audio_codec', None) if vid_md else None,
        'bitrate': getattr(vid_md, 'bitrate', None) if vid_md else None,
        'tags': tags,
        'genero': genero,
        'url_1080': url_1080,
        'url_720': url_720,
        'url_480': url_480,
    }
    return resp


@router.put('/media/video/{media_id}', response_model=schemas.VideoOut)
def update_video(
    media_id: int,
    updates: schemas.VideoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    if not (media.mimetype and media.mimetype.startswith('video/')) and media.media_type != 'video':
        raise HTTPException(status_code=400, detail='Media is not a video')

    # Update description if provided
    if updates.description is not None:
        crud.update_media(db, media, description=updates.description)

    # Update genero if provided
    if updates.genero is not None:
        crud.update_video_metadata_genero(db, media, genero=updates.genero)

    # Replace tags if provided
    if updates.tags is not None:
        crud.replace_tags_for_media(db, media, updates.tags)

    # Refresh media to get updated relationships
    db.refresh(media)

    # Build response similar to get_video
    vid_md = getattr(media, 'video_metadata', None)
    tags = [t.name for t in (media.tags or [])]
    genero = getattr(vid_md, 'genero', None) if vid_md else None

    # Get S3 keys from video_metadata columns and generate presigned URLs
    s3_key_1080 = getattr(vid_md, 'url_1080', None) if vid_md else None
    s3_key_720 = getattr(vid_md, 'url_720', None) if vid_md else None
    s3_key_480 = getattr(vid_md, 'url_480', None) if vid_md else None

    # Generate presigned URLs for each rendition
    url_1080 = None
    url_720 = None
    url_480 = None
    
    if s3_key_1080:
        try:
            url_1080 = s3_utils.generate_presigned_url(s3_key_1080)
        except Exception:
            url_1080 = None
    
    if s3_key_720:
        try:
            url_720 = s3_utils.generate_presigned_url(s3_key_720)
        except Exception:
            url_720 = None
    
    if s3_key_480:
        try:
            url_480 = s3_utils.generate_presigned_url(s3_key_480)
        except Exception:
            url_480 = None

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'duration_seconds': float(getattr(vid_md, 'duration_seconds')) if vid_md and getattr(vid_md, 'duration_seconds') is not None else None,
        'width': getattr(vid_md, 'width', None) if vid_md else None,
        'height': getattr(vid_md, 'height', None) if vid_md else None,
        'frame_rate': float(getattr(vid_md, 'frame_rate')) if vid_md and getattr(vid_md, 'frame_rate') is not None else None,
        'video_codec': getattr(vid_md, 'video_codec', None) if vid_md else None,
        'audio_codec': getattr(vid_md, 'audio_codec', None) if vid_md else None,
        'bitrate': getattr(vid_md, 'bitrate', None) if vid_md else None,
        'tags': tags,
        'genero': genero,
        'url_1080': url_1080,
        'url_720': url_720,
        'url_480': url_480,
    }
    return resp


@router.get('/media/audio/{media_id}', response_model=schemas.AudioOut)
def get_audio(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    if not (media.mimetype and media.mimetype.startswith('audio/')) and media.media_type != 'audio':
        raise HTTPException(status_code=400, detail='Media is not an audio')

    aud_md = getattr(media, 'audio_metadata', None)
    tags = [t.name for t in (media.tags or [])]
    genero = getattr(aud_md, 'genero', None) if aud_md else None
    try:
        url = s3_utils.generate_presigned_url(media.s3_key)
    except Exception:
        url = None

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'duration_seconds': float(getattr(aud_md, 'duration_seconds')) if aud_md and getattr(aud_md, 'duration_seconds') is not None else None,
        'bitrate': getattr(aud_md, 'bitrate', None) if aud_md else None,
        'sample_rate': getattr(aud_md, 'sample_rate', None) if aud_md else None,
        'channels': getattr(aud_md, 'channels', None) if aud_md else None,
        'tags': tags,
        'genero': genero,
        'url': url,
    }
    return resp


@router.put('/media/audio/{media_id}', response_model=schemas.AudioOut)
def update_audio(
    media_id: int,
    updates: schemas.AudioUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    if not (media.mimetype and media.mimetype.startswith('audio/')) and media.media_type != 'audio':
        raise HTTPException(status_code=400, detail='Media is not an audio')

    # Update description if provided
    if updates.description is not None:
        crud.update_media(db, media, description=updates.description)

    # Update genero if provided
    if updates.genero is not None:
        crud.update_audio_metadata_genero(db, media, genero=updates.genero)

    # Replace tags if provided
    if updates.tags is not None:
        crud.replace_tags_for_media(db, media, updates.tags)

    # Refresh media to get updated relationships
    db.refresh(media)

    # Build response similar to get_audio
    aud_md = getattr(media, 'audio_metadata', None)
    tags = [t.name for t in (media.tags or [])]
    genero = getattr(aud_md, 'genero', None) if aud_md else None
    try:
        url = s3_utils.generate_presigned_url(media.s3_key)
    except Exception:
        url = None

    resp = {
        'id': media.id,
        'description': media.description,
        'filename': media.filename,
        'mimetype': media.mimetype,
        'size': media.size,
        'created_at': media.created_at.isoformat() if media.created_at else None,
        'duration_seconds': float(getattr(aud_md, 'duration_seconds')) if aud_md and getattr(aud_md, 'duration_seconds') is not None else None,
        'bitrate': getattr(aud_md, 'bitrate', None) if aud_md else None,
        'sample_rate': getattr(aud_md, 'sample_rate', None) if aud_md else None,
        'channels': getattr(aud_md, 'channels', None) if aud_md else None,
        'tags': tags,
        'genero': genero,
        'url': url,
    }
    return resp

@router.get('/media/{media_id}/url')
def media_presigned_url(media_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    media = crud.get_media(db, media_id)
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')
    # ensure only the owner can get a presigned URL
    if media.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
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
