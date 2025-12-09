from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .database import engine
from . import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multimedia CRUD API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get('/')
def root():
    return {"message": "Multimedia API"}
