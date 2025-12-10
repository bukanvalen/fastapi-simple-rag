import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, time

from app.main import app, get_db
from app import models, auth, api

# Setup in-memory DB for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Mock Google Auth and Calendar
async def mock_get_current_active_user():
    # Return a fake user
    return models.User(id_user=1, nama="Test User", email="test@example.com")

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[api.get_db] = override_get_db
app.dependency_overrides[auth.get_current_active_user] = mock_get_current_active_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    models.Base.metadata.create_all(bind=engine)
    
    # Create a user
    db = TestingSessionLocal()
    user = models.User(id_user=1, nama="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.close()
    
    yield
    models.Base.metadata.drop_all(bind=engine)

# --- TESTS ---

def test_read_users():
    response = client.get("/api/users")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "test@example.com"

def test_api_me():
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_create_semester():
    response = client.post(
        "/api/semesters",
        json={
            "id_user": 1,
            "tipe": "Ganjil",
            "tahun_ajaran": "2025/2026",
            "tanggal_mulai": "2025-09-01",
            "tanggal_selesai": "2026-01-31"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tipe"] == "Ganjil"
    assert data["id_semester"] is not None

def test_read_semesters():
    # Create one first
    client.post(
        "/api/semesters",
        json={
            "id_user": 1,
            "tipe": "Ganjil",
            "tahun_ajaran": "2025/2026",
            "tanggal_mulai": "2025-09-01",
            "tanggal_selesai": "2026-01-31"
        },
    )
    
    response = client.get("/api/semesters")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["tipe"] == "Ganjil"

def test_create_jadwal():
    # Create semester first (optional but good practice as relation often exists)
    sem_res = client.post(
        "/api/semesters",
        json={
            "id_user": 1,
            "tipe": "Ganjil",
            "tahun_ajaran": "2025/2026",
            "tanggal_mulai": "2025-09-01",
            "tanggal_selesai": "2026-01-31"
        },
    )
    sem_id = sem_res.json()["id_semester"]
    
    response = client.post(
        "/api/jadwal",
        json={
            "id_user": 1,
            "id_semester": sem_id,
            "hari": "Senin",
            "nama": "Algoritma",
            "jam_mulai": "08:00:00",
            "jam_selesai": "10:00:00",
            "sks": 3
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nama"] == "Algoritma"
    assert data["id_semester"] == sem_id

def test_create_todo_api():
    response = client.post(
        "/api/todos",
        json={
             "id_user": 1,
             "nama": "Tugas 1",
             "tipe": "Quiz",
             "tenggat": "2025-12-31T23:59:00",
             "deskripsi": "Test"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nama"] == "Tugas 1"

def test_delete_todo_api():
    # Create
    res = client.post(
        "/api/todos",
        json={
             "id_user": 1,
             "nama": "Tugas 1",
             "tipe": "Quiz"
        }
    )
    todo_id = res.json()["id_todo"]
    
    # Delete
    del_res = client.delete(f"/api/todos/{todo_id}")
    assert del_res.status_code == 200
    
    # Verify gone
    get_res = client.get("/api/todos")
    assert len(get_res.json()) == 0
