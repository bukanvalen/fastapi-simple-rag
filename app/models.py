from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Time, Date, Enum as SAEnum
import enum

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
    
    # OAuth Fields
    google_id = Column(String, unique=True, nullable=True, index=True)
    picture = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    
    # Phase 2: Todo Calendar
    todo_calendar_id = Column(String, nullable=True)
    
    # Phase 3: Customization
    calendar_name = Column(String, nullable=True, default="My Campus")

    # RELATIONSHIPS
    rags_embeddings = relationship("RAGSEmbedding", back_populates="owner", cascade="all, delete-orphan")
    chat_history = relationship("AIChatHistory", back_populates="owner", cascade="all, delete-orphan")
    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")
    jadwal_matkul = relationship("JadwalMatkul", back_populates="owner", cascade="all, delete-orphan")
    ukm = relationship("UKM", back_populates="owner", cascade="all, delete-orphan")
    semesters = relationship("Semester", back_populates="owner", cascade="all, delete-orphan")


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
    
    # Calendar Sync
    google_event_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="todos")


# ==========================
# SEMESTER (Phase 2)
# ==========================

class Semester(Base):
    __tablename__ = "semesters"

    id_semester = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))
    
    tipe = Column(String, nullable=False) # "Ganjil" / "Genap"
    tahun_ajaran = Column(String, nullable=False) # "2025/2026"
    tanggal_mulai = Column(Date, nullable=False)
    tanggal_selesai = Column(Date, nullable=False)
    
    google_calendar_id = Column(String, nullable=True)
    
    owner = relationship("User", back_populates="semesters")
    jadwal_matkul = relationship("JadwalMatkul", back_populates="semester", cascade="all, delete-orphan")


# ==========================
# JADWAL MATA KULIAH
# ==========================

class HariEnum(str, enum.Enum):
    Senin = "Senin"
    Selasa = "Selasa"
    Rabu = "Rabu"
    Kamis = "Kamis"
    Jumat = "Jumat"
    Sabtu = "Sabtu"
    Minggu = "Minggu"

class JadwalMatkul(Base):
    __tablename__ = "jadwal_matkul"

    id_jadwal = Column(Integer, primary_key=True, index=True)
    id_user = Column(Integer, ForeignKey("users.id_user"))
    id_semester = Column(Integer, ForeignKey("semesters.id_semester"), nullable=True) # Optional for backward compat, but intended to be used

    hari = Column(SAEnum(HariEnum), nullable=False)
    nama = Column(String, nullable=False)
    jam_mulai = Column(Time, nullable=False)
    jam_selesai = Column(Time, nullable=False)
    sks = Column(Integer, nullable=False)
    
    google_event_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="jadwal_matkul")
    semester = relationship("Semester", back_populates="jadwal_matkul")


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