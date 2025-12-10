import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.db import Base
from app import crud, schemas, models

# Use a separate test PostgreSQL database
SQLALCHEMY_DATABASE_URL = "postgresql://admin:1@localhost:5432/ragdb_test"

test_engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override the get_db dependency to use the test database
def override_get_db():
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

@pytest.fixture(name="session", scope="function")
async def session_fixture():
    # Pastikan ekstensi pgvector diaktifkan untuk database pengujian
    with test_engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        connection.commit()
    
    # Hapus semua tabel terlebih dahulu untuk memastikan kondisi bersih
    Base.metadata.drop_all(bind=test_engine)
    # Buat semua tabel yang didefinisikan dalam models.py
    Base.metadata.create_all(bind=test_engine)
    
    db_session = TestingSessionLocal()
    try:
        # Create a user for general testing
        test_user = crud.create_user(db_session, schemas.UserCreate(nama="Test User", email="test@example.com", bio="Saya pengguna uji.", lokasi="Kota Uji"))
        # We need to await this since it's an async function in the real code, 
        # but in fixtures we might need to handle it carefully if the fixture itself isn't fully async-capable in the same way.
        # However, checking the original code, `crud.create_user_embedding` is async.
        # Pytest-asyncio handles async fixtures.
        await crud.create_user_embedding(db_session, test_user)
        db_session.commit()
        db_session.refresh(test_user)

        yield db_session
    finally:
        db_session.rollback() # Rollback any changes made during the test
        db_session.close()
        # Hapus semua tabel setelah pengujian
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(name="client", scope="function")
async def client_fixture(session):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
