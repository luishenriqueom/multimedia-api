from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    media = relationship("Media", back_populates="owner")

class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    filename = Column(String, nullable=False)
    s3_key = Column(String, nullable=False, unique=True)
    mimetype = Column(String)
    size = Column(BigInteger)
    is_public = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="media")
