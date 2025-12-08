from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .db import Base


# ==========================
# USER
# ==========================

class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    telepon = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    lokasi = Column(String, nullable=True)

    # RELATIONSHIPS
    rags_embeddings = relationship("RAGSEmbedding", back_populates="owner", cascade="all, delete-orphan")
    chat_history = relationship("AIChatHistory", back_populates="owner", cascade="all, delete-orphan")
    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")
    jadwal_matkul = relationship("JadwalMatkul", back_populates="owner", cascade="all, delete-orphan")
    ukm = relationship("UKM", back_populates="owner", cascade="all, delete-orphan")


# ==========================
# RAGS EMBEDDING
# ==========================

class RAGSEmbedding(Base):
    __tablename__ = "rags_embeddings"

    id_embedding = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"), nullable=True)

    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=True)
    text_original = Column(Text, nullable=False)

    embedding = Column(Vector(768)) # Assuming Gemini embedding dimension is 768 as seen in rag.py

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="rags_embeddings")


# ==========================
# CHAT HISTORY
# ==========================

class AIChatHistory(Base):
    __tablename__ = "ai_chat_history"

    id_chat = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))

    role = Column(String, nullable=False)  # user / assistant
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="chat_history")


# ==========================
# TODO
# ==========================

class Todo(Base):
    __tablename__ = "todos"

    id_todo = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))

    nama = Column(String, nullable=False)
    tipe = Column(String, nullable=False)
    tenggat = Column(DateTime, nullable=True)
    deskripsi = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="todos")


# ==========================
# JADWAL MATA KULIAH
# ==========================

class JadwalMatkul(Base):
    __tablename__ = "jadwal_matkul"

    id_jadwal = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))

    hari = Column(String, nullable=False)
    nama = Column(String, nullable=False)
    jam_mulai = Column(Time, nullable=False)
    jam_selesai = Column(Time, nullable=False)
    sks = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="jadwal_matkul")


# ==========================
# UKM
# ==========================

class UKM(Base):
    __tablename__ = "ukm"

    id_ukm = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))

    nama = Column(String, nullable=False)
    jabatan = Column(String, nullable=False)
    deskripsi = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="ukm")