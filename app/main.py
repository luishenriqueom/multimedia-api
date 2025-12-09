from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .database import engine
from . import models
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multimedia CRUD API")
# Read allowed frontend origins from env var FRONTEND_ORIGINS (comma-separated).
# When the client uses `fetch(..., { credentials: 'include' })`, the Access-Control-Allow-Origin
# header must NOT be '*' — it must echo a specific origin. Default to localhost:3000 for dev.
allowed_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get('/')
def root():
    return {"message": "Multimedia API"}
