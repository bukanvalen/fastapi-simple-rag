from sqlalchemy.orm import Session
from app import models, schemas, rag, crud
import logging

logger = logging.getLogger(__name__)

async def update_user_embedding(db: Session, user: models.User):
    """
    Generates and updates the RAG embedding for a user.
    """
    if not user:
        return

    # Construct text representation
    user_text = (
        f"Nama: {user.nama}. "
        f"Email: {user.email}. "
        f"Telepon: {user.telepon or ''}. "
        f"Bio: {user.bio or ''}. "
        f"Lokasi: {user.lokasi or ''}. "
    )
    
    try:
        # Generate embedding
        embedding_vector = await rag.embed_text_with_gemini(user_text)
        
        # Check if embedding exists
        existing_embedding = db.query(models.RAGSEmbedding).filter_by(
            source_type="user", source_id=str(user.id_user)
        ).first()

        if existing_embedding:
            existing_embedding.text_original = user_text
            existing_embedding.embedding = embedding_vector
        else:
            embedding_create = schemas.RAGSEmbeddingCreate(
                id_user=user.id_user,
                source_type="user",
                source_id=str(user.id_user),
                text_original=user_text
            )
            crud.create_rags_embedding(db, embedding_create, embedding_vector)
        
        db.commit()
        logger.info(f"Updated embedding for user {user.id_user}")

    except Exception as e:
        logger.error(f"Failed to update user embedding: {e}")

async def update_todo_embedding(db: Session, todo: models.Todo):
    """
    Generates and updates the RAG embedding for a todo item.
    """
    if not todo:
        return

    todo_text = (
        f"Todo: {todo.nama}. "
        f"Type: {todo.tipe}. "
        f"Due: {todo.tenggat}. "
        f"Description: {todo.deskripsi or ''}."
    )

    try:
        embedding_vector = await rag.embed_text_with_gemini(todo_text)

        existing_embedding = db.query(models.RAGSEmbedding).filter_by(
            source_type="todo", source_id=str(todo.id_todo)
        ).first()

        if existing_embedding:
            existing_embedding.text_original = todo_text
            existing_embedding.embedding = embedding_vector
        else:
            embedding_create = schemas.RAGSEmbeddingCreate(
                id_user=todo.id_user,
                source_type="todo",
                source_id=str(todo.id_todo),
                text_original=todo_text
            )
            crud.create_rags_embedding(db, embedding_create, embedding_vector)
            
        db.commit()
        logger.info(f"Updated embedding for todo {todo.id_todo}")

    except Exception as e:
        logger.error(f"Failed to update todo embedding: {e}")

async def update_jadwal_embedding(db: Session, jadwal: models.JadwalMatkul):
    """
    Generates and updates the RAG embedding for a class schedule (jadwal matkul).
    """
    if not jadwal:
        return

    jadwal_text = (
        f"Jadwal Mata Kuliah: {jadwal.nama}. "
        f"Hari: {jadwal.hari}. "
        f"Mulai: {jadwal.jam_mulai}. "
        f"Selesai: {jadwal.jam_selesai}. "
        f"SKS: {jadwal.sks}."
    )

    try:
        embedding_vector = await rag.embed_text_with_gemini(jadwal_text)

        existing_embedding = db.query(models.RAGSEmbedding).filter_by(
            source_type="jadwal", source_id=str(jadwal.id_jadwal)
        ).first()

        if existing_embedding:
            existing_embedding.text_original = jadwal_text
            existing_embedding.embedding = embedding_vector
        else:
            embedding_create = schemas.RAGSEmbeddingCreate(
                id_user=jadwal.id_user,
                source_type="jadwal",
                source_id=str(jadwal.id_jadwal),
                text_original=jadwal_text
            )
            crud.create_rags_embedding(db, embedding_create, embedding_vector)

        db.commit()
        logger.info(f"Updated embedding for jadwal {jadwal.id_jadwal}")

    except Exception as e:
        logger.error(f"Failed to update jadwal embedding: {e}")

async def update_ukm_embedding(db: Session, ukm: models.UKM):
    """
    Generates and updates the RAG embedding for a UKM activity.
    """
    if not ukm:
        return

    ukm_text = (
        f"UKM: {ukm.nama}. "
        f"Jabatan: {ukm.jabatan}. "
        f"Description: {ukm.deskripsi or ''}."
    )

    try:
        embedding_vector = await rag.embed_text_with_gemini(ukm_text)

        existing_embedding = db.query(models.RAGSEmbedding).filter_by(
            source_type="ukm", source_id=str(ukm.id_ukm)
        ).first()

        if existing_embedding:
            existing_embedding.text_original = ukm_text
            existing_embedding.embedding = embedding_vector
        else:
            embedding_create = schemas.RAGSEmbeddingCreate(
                id_user=ukm.id_user,
                source_type="ukm",
                source_id=str(ukm.id_ukm),
                text_original=ukm_text
            )
            crud.create_rags_embedding(db, embedding_create, embedding_vector)
            
        db.commit()
        logger.info(f"Updated embedding for UKM {ukm.id_ukm}")

    except Exception as e:
        logger.error(f"Failed to update UKM embedding: {e}")
