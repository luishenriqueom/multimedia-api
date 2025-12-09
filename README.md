FastAPI Multimedia Backend

This backend provides:

- JWT authentication (register/login)
- User profile management
- CRUD for multimedia objects (images, audio, video)
- Uploads to AWS S3 and presigned URLs for streaming
- PostgreSQL (SQLAlchemy) for metadata storage

See `DEPLOYMENT.md` for AWS deployment and networking guidance.

Local development:

- Copy `.env.example` to `.env` and update values.
- Start dependencies with `docker-compose up --build`.
- The API will be available at `http://localhost:8000`.

Basic endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me` / `PUT /users/me`
- `POST /media/upload` (multipart file)
- `GET /media/` (list + search)
- `GET /media/{id}` (metadata + presigned URL)
- `DELETE /media/{id}`
