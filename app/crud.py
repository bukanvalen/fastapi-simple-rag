from sqlalchemy.orm import Session
from . import models, schemas
from pgvector.sqlalchemy import Vector
from typing import List, Optional

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id_user == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        nama=user.nama,
        email=user.email,
        telepon=user.telepon,
        bio=user.bio,
        lokasi=user.lokasi
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = db.query(models.User).filter(models.User.id_user == user_id).first()
    if db_user:
        update_data = user_update.model_dump(exclude_unset=True, exclude_none=True)
        if update_data:
            # ORM-style update (correct)
            for key, value in update_data.items():
                setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id_user == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def get_rags_embeddings(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.RAGSEmbedding).offset(skip).limit(limit).all()

def create_rags_embedding(db: Session, embedding: schemas.RAGSEmbeddingCreate, vector_embedding: List[float]):
    db_embedding = models.RAGSEmbedding(
        id_user=embedding.id_user,
        source_type=embedding.source_type,
        source_id=embedding.source_id,
        text_original=embedding.text_original,
        embedding=vector_embedding
    )
    db.add(db_embedding)
    db.commit()
    db.refresh(db_embedding)
    return db_embedding

def delete_rags_embedding(db: Session, embedding_id: int):
    db_embedding = db.query(models.RAGSEmbedding).filter(models.RAGSEmbedding.id_embedding == embedding_id).first()
    if db_embedding:
        db.delete(db_embedding)
        db.commit()
    return db_embedding

def delete_rags_embeddings_by_user_id(db: Session, user_id: int):
    db.query(models.RAGSEmbedding).filter(models.RAGSEmbedding.id_user == user_id).delete()
    db.commit()

def delete_rags_embedding_by_source_type_and_id(db: Session, source_type: str, source_id: str):
    db.query(models.RAGSEmbedding).filter(
        models.RAGSEmbedding.source_type == source_type,
        models.RAGSEmbedding.source_id == source_id
    ).delete()
    db.commit()

def create_ai_chat_history(db: Session, chat_entry: schemas.AIChatHistoryCreate):
    db_chat_entry = models.AIChatHistory(
        id_user=chat_entry.id_user,
        role=chat_entry.role,
        message=chat_entry.message
    )
    db.add(db_chat_entry)
    db.commit()
    db.refresh(db_chat_entry)
    return db_chat_entry

# --- TODO CRUD ---
def create_todo(db: Session, todo: schemas.TodoCreate) -> models.Todo:
    db_todo = models.Todo(
        id_user=todo.id_user,
        nama=todo.nama,
        tipe=todo.tipe,
        tenggat=todo.tenggat,
        deskripsi=todo.deskripsi
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo_update: schemas.TodoUpdate) -> Optional[models.Todo]:
    db_todo = db.query(models.Todo).filter(models.Todo.id_todo == todo_id).first()
    if db_todo:
        update_data = todo_update.model_dump(exclude_unset=True, exclude_none=True)
        if update_data: # Only execute update if there's data to update
            for key, value in update_data.items():
                setattr(db_todo, key, value)
        db.commit()
        db.refresh(db_todo) # Refresh the in-memory object to reflect changes from the direct update
    return db_todo

def get_todo(db: Session, todo_id: int) -> Optional[models.Todo]:
    return db.query(models.Todo).filter(models.Todo.id_todo == todo_id).first()

def get_all_todos(db: Session, skip: int = 0, limit: int = 100) -> List[models.Todo]:
    return db.query(models.Todo).offset(skip).limit(limit).all()

def get_todos_by_user(db: Session, id_user: int, skip: int = 0, limit: int = 100) -> List[models.Todo]:
    return db.query(models.Todo).filter(models.Todo.id_user == id_user).offset(skip).limit(limit).all()

def delete_todo(db: Session, todo_id: int):
    db_todo = db.query(models.Todo).filter(models.Todo.id_todo == todo_id).first()
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

# --- JADWAL MATKUL CRUD ---
def create_jadwal_matkul(db: Session, jadwal: schemas.JadwalMatkulCreate) -> models.JadwalMatkul:
    db_jadwal = models.JadwalMatkul(
        id_user=jadwal.id_user,
        hari=jadwal.hari,
        nama=jadwal.nama,
        jam_mulai=jadwal.jam_mulai,
        jam_selesai=jadwal.jam_selesai,
        sks=jadwal.sks
    )
    db.add(db_jadwal)
    db.commit()
    db.refresh(db_jadwal)
    return db_jadwal

def update_jadwal_matkul(db: Session, jadwal_id: int, jadwal_update: schemas.JadwalMatkulUpdate) -> Optional[models.JadwalMatkul]:
    db_jadwal = db.query(models.JadwalMatkul).filter(models.JadwalMatkul.id_jadwal == jadwal_id).first()
    if db_jadwal:
        update_data = jadwal_update.model_dump(exclude_unset=True, exclude_none=True)
        if update_data: # Only execute update if there's data to update
            for key, value in update_data.items():
                setattr(db_jadwal, key, value)
        db.commit()
        db.refresh(db_jadwal) # Refresh the in-memory object to reflect changes from the direct update
    return db_jadwal

def get_jadwal_matkul(db: Session, jadwal_id: int) -> Optional[models.JadwalMatkul]:
    return db.query(models.JadwalMatkul).filter(models.JadwalMatkul.id_jadwal == jadwal_id).first()

def get_all_jadwal_matkul(db: Session, skip: int = 0, limit: int = 100) -> List[models.JadwalMatkul]:
    return db.query(models.JadwalMatkul).offset(skip).limit(limit).all()

def get_jadwal_matkul_by_user(db: Session, id_user: int, skip: int = 0, limit: int = 100) -> List[models.JadwalMatkul]:
    return db.query(models.JadwalMatkul).filter(models.JadwalMatkul.id_user == id_user).offset(skip).limit(limit).all()

def delete_jadwal_matkul(db: Session, jadwal_id: int):
    db_jadwal = db.query(models.JadwalMatkul).filter(models.JadwalMatkul.id_jadwal == jadwal_id).first()
    if db_jadwal:
        db.delete(db_jadwal)
        db.commit()
    return db_jadwal

# --- UKM CRUD ---
def create_ukm(db: Session, ukm: schemas.UKMCreate) -> models.UKM:
    db_ukm = models.UKM(
        id_user=ukm.id_user,
        nama=ukm.nama,
        jabatan=ukm.jabatan,
        deskripsi=ukm.deskripsi
    )
    db.add(db_ukm)
    db.commit()
    db.refresh(db_ukm)
    return db_ukm

def update_ukm(db: Session, ukm_id: int, ukm_update: schemas.UKMUpdate) -> Optional[models.UKM]:
    db_ukm = db.query(models.UKM).filter(models.UKM.id_ukm == ukm_id).first()
    if db_ukm:
        update_data = ukm_update.model_dump(exclude_unset=True, exclude_none=True)
        if update_data: # Only execute update if there's data to update
            for key, value in update_data.items():
                setattr(db_ukm, key, value)
        db.commit()
        db.refresh(db_ukm) # Refresh the in-memory object to reflect changes from the direct update
    return db_ukm

def get_ukm(db: Session, ukm_id: int) -> Optional[models.UKM]:
    return db.query(models.UKM).filter(models.UKM.id_ukm == ukm_id).first()

def get_all_ukm(db: Session, skip: int = 0, limit: int = 100) -> List[models.UKM]:
    return db.query(models.UKM).offset(skip).limit(limit).all()

def get_ukm_by_user(db: Session, id_user: int, skip: int = 0, limit: int = 100) -> List[models.UKM]:
    return db.query(models.UKM).filter(models.UKM.id_user == id_user).offset(skip).limit(limit).all()

def delete_ukm(db: Session, ukm_id: int):
    db_ukm = db.query(models.UKM).filter(models.UKM.id_ukm == ukm_id).first()
    if db_ukm:
        db.delete(db_ukm)
        db.commit()
    return db_ukm

def get_chat_history(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.AIChatHistory).filter(models.AIChatHistory.id_user == user_id).offset(skip).limit(limit).all()

def get_all_rags_embeddings(db: Session):
    return db.query(models.RAGSEmbedding).all()

from .rag import embed_text_with_gemini # Import the embedding function

async def create_user_embedding(db: Session, db_user: models.User):
    # Combine relevant user data into a single text for embedding
    user_data_text = f"Nama: {db_user.nama}. Email: {db_user.email}. Telepon: {db_user.telepon or ''}. Bio: {db_user.bio or ''}. Lokasi: {db_user.lokasi or ''}."
    
    # Generate embedding
    user_embedding_vector = await embed_text_with_gemini(user_data_text)
    
    # Create RAGSEmbedding entry
    db_embedding = models.RAGSEmbedding(
        id_user=db_user.id_user,
        source_type="user",
        source_id=str(db_user.id_user), # Use user ID as source_id
        text_original=user_data_text,
        embedding=user_embedding_vector
    )
    db.add(db_embedding)
    db.commit()
    db.refresh(db_embedding)
    return db_embedding

