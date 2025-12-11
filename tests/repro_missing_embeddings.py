
import sys
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models, crud, rag_service, db, schemas
from app.api import router

import logging
logging.basicConfig(level=logging.INFO)

# Setup DB
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    print("DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_todo_embedding():
    session = TestingSessionLocal()
    try:
        # Create user
        user = crud.get_user_by_email(session, "test@example.com")
        if not user:
            user = crud.create_user(session, schemas.UserCreate(
                nama="Test User", email="test@example.com"
            ))
            # Embedding for user created in main, but here we test rag_service directly
            await rag_service.update_user_embedding(session, user)

        # Create Todo
        print("Creating Todo...")
        todo = crud.create_todo(session, schemas.TodoCreate(
            id_user=user.id_user,
            nama="Test Todo",
            tipe="Tugas",
            tenggat=None,
            deskripsi="Test Description"
        ))
        
        # Manually trigger service (simulating main.py)
        print("Triggering Embedding Service for Todo...")
        await rag_service.update_todo_embedding(session, todo)
        
        # Verify Embedding
        embedding = session.query(models.RAGSEmbedding).filter_by(
            source_type="todo", source_id=str(todo.id_todo)
        ).first()
        
        if embedding:
            print(f"[SUCCESS] Todo Embedding Found: {embedding.text_original}")
        else:
            print("[FAILURE] Todo Embedding NOT Found")

        # Cleanup
        crud.delete_todo(session, todo.id_todo)
        crud.delete_rags_embedding_by_source_type_and_id(session, "todo", str(todo.id_todo))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

async def test_jadwal_embedding():
    session = TestingSessionLocal()
    try:
        user = crud.get_user_by_email(session, "test@example.com")
        if not user:
             # Should exist from prev test or create
             pass # assume exists for brevity or recreates

        # Create Jadwal
        import datetime
        print("Creating Jadwal...")
        jadwal = crud.create_jadwal_matkul(session, schemas.JadwalMatkulCreate(
            id_user=user.id_user,
            hari="Senin",
            nama="Test Matkul",
            jam_mulai=datetime.time(9, 0),
            jam_selesai=datetime.time(11, 0),
            sks=3
        ))

        # Manually trigger service
        print("Triggering Embedding Service for Jadwal...")
        await rag_service.update_jadwal_embedding(session, jadwal)

        # Verify Embedding
        embedding = session.query(models.RAGSEmbedding).filter_by(
            source_type="jadwal", source_id=str(jadwal.id_jadwal)
        ).first()

        if embedding:
             print(f"[SUCCESS] Jadwal Embedding Found: {embedding.text_original}")
        else:
             print("[FAILURE] Jadwal Embedding NOT Found")

        # Cleanup
        crud.delete_jadwal_matkul(session, jadwal.id_jadwal)
        crud.delete_rags_embedding_by_source_type_and_id(session, "jadwal", str(jadwal.id_jadwal))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_todo_embedding())
    loop.run_until_complete(test_jadwal_embedding())
