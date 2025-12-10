from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime, time, date

# User Schemas
class UserBase(BaseModel):
    nama: str
    email: str
    telepon: Optional[str] = None
    bio: Optional[str] = None
    bio: Optional[str] = None
    lokasi: Optional[str] = None
    calendar_name: Optional[str] = "My Campus"

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    nama: Optional[str] = None
    email: Optional[str] = None
    telepon: Optional[str] = None
    bio: Optional[str] = None
    lokasi: Optional[str] = None

class User(UserBase):
    id_user: int
    model_config = ConfigDict(from_attributes=True)


# RAGSEmbedding Schemas
class RAGSEmbeddingBase(BaseModel):
    id_user: Optional[int] = None
    source_type: str
    source_id: Optional[str] = None
    text_original: str

class RAGSEmbeddingCreate(RAGSEmbeddingBase):
    pass

class RAGSEmbedding(RAGSEmbeddingBase):
    id_embedding: int
    embedding: List[float] # This will be handled as a list of floats in Pydantic
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# AI Chat History Schemas
class AIChatHistoryBase(BaseModel):
    id_user: int
    role: str
    message: str

class AIChatHistoryCreate(AIChatHistoryBase):
    pass

class AIChatHistory(AIChatHistoryBase):
    id_chat: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Request body for /add-activity
class ActivityCreate(RAGSEmbeddingBase):
    pass

# Request body for /rag/query
class RAGQuery(BaseModel):
    id_user: Optional[int] = None
    question: str
    top_k: int = 5
    client_local_time: Optional[datetime] = None

# Response for /rag/query
class RAGResponse(BaseModel):
    answer: str
    context_docs: List[RAGSEmbedding]

# Google Calendar Integration (Optional)
class CalendarEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


# Todo Schemas
class TodoBase(BaseModel):
    id_user: int
    nama: str
    tipe: str
    tenggat: Optional[datetime] = None
    deskripsi: Optional[str] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(TodoBase):
    id_user: Optional[int] = None
    nama: Optional[str] = None
    tipe: Optional[str] = None
    tenggat: Optional[datetime] = None
    deskripsi: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class Todo(TodoBase):
    id_todo: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



# Semester Schemas
class SemesterBase(BaseModel):
    id_user: int
    tipe: str # "Ganjil" / "Genap"
    tahun_ajaran: str # "2025/2026"
    tanggal_mulai: date
    tanggal_selesai: date

class SemesterCreate(SemesterBase):
    pass

class SemesterUpdate(SemesterBase):
    id_user: Optional[int] = None
    tipe: Optional[str] = None
    tahun_ajaran: Optional[str] = None
    tanggal_mulai: Optional[date] = None
    tanggal_selesai: Optional[date] = None

class Semester(SemesterBase):
    id_semester: int
    google_calendar_id: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# JadwalMatkul Schemas
class JadwalMatkulBase(BaseModel):
    id_user: int
    id_semester: Optional[int] = None
    hari: str # We accept string, validated by Enum in DB or logic
    nama: str
    jam_mulai: time
    jam_selesai: time
    sks: int

class JadwalMatkulCreate(JadwalMatkulBase):
    pass

class JadwalMatkulUpdate(JadwalMatkulBase):
    id_user: Optional[int] = None
    id_semester: Optional[int] = None
    hari: Optional[str] = None
    nama: Optional[str] = None
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    sks: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class JadwalMatkul(JadwalMatkulBase):
    id_jadwal: int
    google_event_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# UKM Schemas
class UKMBase(BaseModel):
    id_user: int
    nama: str
    jabatan: str
    deskripsi: Optional[str] = None

class UKMCreate(UKMBase):
    pass

class UKMUpdate(UKMBase):
    id_user: Optional[int] = None
    nama: Optional[str] = None
    jabatan: Optional[str] = None
    deskripsi: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UKM(UKMBase):
    id_ukm: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)