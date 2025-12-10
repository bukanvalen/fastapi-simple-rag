import pytest
from app import crud, schemas, models
from app.rag import embed_text_with_gemini
from datetime import datetime, time

@pytest.mark.asyncio
async def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sistem RAG yang Dipersonalisasi" in response.text
    assert "Test User" in response.text # Verifikasi pengguna dari fixture ditampilkan

@pytest.mark.asyncio
async def test_add_user(client, session):
    user_name = "New User"
    user_email = "newuser@example.com"
    response = client.post(
        "/add-user",
        data={
            "nama": user_name,
            "email": user_email,
            "bio": "Bio untuk pengguna baru.",
            "telepon": "1234567890",
            "lokasi": "Metropolis"
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menambahkan pengguna"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi pengguna dibuat
    db_user = crud.get_user_by_email(session, user_email)
    assert db_user is not None, "Pengguna baru seharusnya ada di database"
    assert db_user.nama == user_name, "Nama pengguna tidak sesuai"

    # Verifikasi embedding pengguna dibuat
    user_embeddings = session.query(models.RAGSEmbedding).filter(
        models.RAGSEmbedding.id_user == db_user.id_user,
        models.RAGSEmbedding.source_type == "user"
    ).all()
    assert len(user_embeddings) == 1, "Seharusnya ada satu embedding untuk pengguna baru"
    assert user_embeddings[0].text_original == f"Nama: {user_name}. Email: {user_email}. Telepon: 1234567890. Bio: Bio untuk pengguna baru.. Lokasi: Metropolis.", "Konten embedding pengguna tidak sesuai"


@pytest.mark.asyncio
async def test_delete_user(client, session):
    # Buat pengguna untuk dihapus
    user_to_delete = crud.create_user(session, schemas.UserCreate(nama="Hapus Saya", email="delete@example.com"))
    await crud.create_user_embedding(session, user_to_delete)
    session.commit()
    session.refresh(user_to_delete)
    
    # Pastikan pengguna dan embedding ada
    assert crud.get_user(session, user_to_delete.id_user) is not None, "Pengguna seharusnya ada sebelum dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(id_user=user_to_delete.id_user).count() > 0, "Embedding pengguna seharusnya ada sebelum dihapus"

    response = client.post(
        f"/delete-user/{user_to_delete.id_user}",
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menghapus pengguna"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi pengguna dan semua embedding terkait dihapus
    assert crud.get_user(session, user_to_delete.id_user) is None, "Pengguna seharusnya sudah dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(id_user=user_to_delete.id_user).count() == 0, "Semua embedding terkait pengguna seharusnya sudah dihapus"


@pytest.mark.asyncio
async def test_add_todo(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    todo_name = "Selesaikan Proyek"
    response = client.post(
        "/add-todo",
        data={
            "id_user": test_user.id_user,
            "nama": todo_name,
            "tipe": "Tugas",
            "tenggat": "2025-12-31T23:59",
            "deskripsi": "Selesaikan proyek RAG."
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menambahkan todo"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi todo dan embedding dibuat
    db_todo = session.query(models.Todo).filter_by(nama=todo_name).first()
    assert db_todo is not None, "Todo baru seharusnya ada di database"
    assert db_todo.deskripsi == "Selesaikan proyek RAG.", "Deskripsi todo tidak sesuai"

    todo_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="todo", source_id=str(db_todo.id_todo)
    ).first()
    assert todo_embedding is not None, "Embedding todo seharusnya dibuat"
    assert todo_embedding.text_original.startswith("Todo: Selesaikan Proyek"), "Konten embedding todo tidak sesuai"


@pytest.mark.asyncio
async def test_delete_todo(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    db_todo = crud.create_todo(session, schemas.TodoCreate(
        id_user=test_user.id_user,
        nama="Todo Sementara",
        tipe="Uji",
        tenggat=datetime(2025, 1, 1, 10, 0),
        deskripsi="Item sementara"
    ))
    # Buat embedding secara manual untuk pengujian penghapusan
    todo_text = f"Todo: {db_todo.nama}. Type: {db_todo.tipe}. Due: {db_todo.tenggat}. Description: {db_todo.deskripsi or ''}."
    embedding_list = await embed_text_with_gemini(todo_text)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=db_todo.id_user, source_type="todo", source_id=str(db_todo.id_todo), text_original=todo_text
    ), embedding_list)
    session.commit()
    session.refresh(db_todo)

    # Pastikan todo dan embedding ada
    assert crud.get_todo(session, db_todo.id_todo) is not None, "Todo seharusnya ada sebelum dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="todo", source_id=str(db_todo.id_todo)
    ).count() == 1, "Embedding todo seharusnya ada sebelum dihapus"

    response = client.post(
        f"/delete-todo/{db_todo.id_todo}",
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menghapus todo"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi todo dan embedding-nya dihapus
    assert crud.get_todo(session, db_todo.id_todo) is None, "Todo seharusnya sudah dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="todo", source_id=str(db_todo.id_todo)
    ).count() == 0, "Embedding todo seharusnya sudah dihapus"


@pytest.mark.asyncio
async def test_add_jadwal_matkul(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    jadwal_name = "Algoritma"
    response = client.post(
        "/add-jadwal",
        data={
            "id_user": test_user.id_user,
            "hari": "Selasa",
            "nama": jadwal_name,
            "jam_mulai": "09:00",
            "jam_selesai": "11:00",
            "sks": 3
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menambahkan jadwal"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi jadwal mata kuliah dan embedding dibuat
    db_jadwal = session.query(models.JadwalMatkul).filter_by(nama=jadwal_name).first()
    assert db_jadwal is not None, "Jadwal mata kuliah baru seharusnya ada di database"
    assert db_jadwal.hari == "Selasa", "Hari jadwal mata kuliah tidak sesuai"

    jadwal_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="jadwal", source_id=str(db_jadwal.id_jadwal)
    ).first()
    assert jadwal_embedding is not None, "Embedding jadwal mata kuliah seharusnya dibuat"
    assert jadwal_embedding.text_original.startswith("Jadwal Mata Kuliah: Algoritma"), "Konten embedding jadwal mata kuliah tidak sesuai"


@pytest.mark.asyncio
async def test_delete_jadwal_matkul(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    db_jadwal = crud.create_jadwal_matkul(session, schemas.JadwalMatkulCreate(
        id_user=test_user.id_user,
        hari="Rabu",
        nama="Jadwal Sementara",
        jam_mulai=time(14, 0),
        jam_selesai=time(16, 0),
        sks=2
    ))
    # Buat embedding secara manual untuk pengujian penghapusan
    jadwal_text = f"Jadwal Mata Kuliah: {db_jadwal.nama}. Hari: {db_jadwal.hari}. Mulai: {db_jadwal.jam_mulai}. Selesai: {db_jadwal.jam_selesai}. SKS: {db_jadwal.sks}."
    embedding_list = await embed_text_with_gemini(jadwal_text)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=db_jadwal.id_user, source_type="jadwal", source_id=str(db_jadwal.id_jadwal), text_original=jadwal_text
    ), embedding_list)
    session.commit()
    session.refresh(db_jadwal)

    # Ensure jadwal and embedding exist
    assert crud.get_jadwal_matkul(session, db_jadwal.id_jadwal) is not None
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="jadwal", source_id=str(db_jadwal.id_jadwal)
    ).count() == 1

    response = client.post(
        f"/delete-jadwal/{db_jadwal.id_jadwal}",
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Verify jadwal and its embedding are deleted
    assert crud.get_jadwal_matkul(session, db_jadwal.id_jadwal) is None
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="jadwal", source_id=str(db_jadwal.id_jadwal)
    ).count() == 0


@pytest.mark.asyncio
async def test_add_ukm(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    ukm_name = "Basket"
    response = client.post(
        "/add-ukm",
        data={
            "id_user": test_user.id_user,
            "nama": ukm_name,
            "jabatan": "Anggota",
            "deskripsi": "Bermain basket"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Verify UKM and embedding were created
    db_ukm = session.query(models.UKM).filter_by(nama=ukm_name).first()
    assert db_ukm is not None
    assert db_ukm.jabatan == "Anggota"

    ukm_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="ukm", source_id=str(db_ukm.id_ukm)
    ).first()
    assert ukm_embedding is not None
    assert ukm_embedding.text_original.startswith("UKM: Basket")


@pytest.mark.asyncio
async def test_delete_ukm(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    db_ukm = crud.create_ukm(session, schemas.UKMCreate(
        id_user=test_user.id_user,
        nama="UKM Sementara",
        jabatan="Pengurus",
        deskripsi="Aktivitas klub sementara"
    ))
    # Buat embedding secara manual untuk pengujian penghapusan
    ukm_text = f"UKM: {db_ukm.nama}. Jabatan: {db_ukm.jabatan}. Description: {db_ukm.deskripsi or ''}."
    embedding_list = await embed_text_with_gemini(ukm_text)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=db_ukm.id_user, source_type="ukm", source_id=str(db_ukm.id_ukm), text_original=ukm_text
    ), embedding_list)
    session.commit()
    session.refresh(db_ukm)

    # Pastikan UKM dan embedding ada
    assert crud.get_ukm(session, db_ukm.id_ukm) is not None, "UKM seharusnya ada sebelum dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="ukm", source_id=str(db_ukm.id_ukm)
    ).count() == 1, "Embedding UKM seharusnya ada sebelum dihapus"

    response = client.post(
        f"/delete-ukm/{db_ukm.id_ukm}",
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah menghapus UKM"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    # Verifikasi UKM dan embedding-nya dihapus
    assert crud.get_ukm(session, db_ukm.id_ukm) is None, "UKM seharusnya sudah dihapus"
    assert session.query(models.RAGSEmbedding).filter_by(
        source_type="ukm", source_id=str(db_ukm.id_ukm)
    ).count() == 0, "Embedding UKM seharusnya sudah dihapus"

@pytest.mark.asyncio
async def test_update_user(client, session):
    user_to_update = crud.create_user(session, schemas.UserCreate(nama="Pengguna Lama", email="old@example.com", bio="Bio lama.", lokasi="Lokasi Lama"))
    await crud.create_user_embedding(session, user_to_update)
    session.commit()
    session.refresh(user_to_update)

    updated_name = "Pengguna Baru"
    updated_bio = "Bio yang diperbarui."
    response = client.post(
        f"/update-user/{user_to_update.id_user}",
        data={
            "nama": updated_name,
            "bio": updated_bio
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah memperbarui pengguna"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    session.expire_all()  # Forces ORM cache to clear
    db_user = crud.get_user(session, user_to_update.id_user)
    assert db_user.nama == updated_name, "Nama pengguna seharusnya diperbarui"
    assert db_user.bio == updated_bio, "Bio pengguna seharusnya diperbarui"
    assert db_user.email == user_to_update.email, "Email pengguna seharusnya tidak berubah"

    # Verifikasi embedding pengguna diperbarui
    updated_embedding_text = f"Nama: {updated_name}. Email: {db_user.email}. Telepon: {db_user.telepon or ''}. Bio: {updated_bio}. Lokasi: {db_user.lokasi or ''}."
    user_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="user", source_id=str(db_user.id_user)
    ).first()
    assert user_embedding.text_original == updated_embedding_text, "Embedding pengguna seharusnya diperbarui dengan teks baru"


@pytest.mark.asyncio
async def test_update_todo(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    todo_to_update = crud.create_todo(session, schemas.TodoCreate(
        id_user=test_user.id_user, nama="Todo Awal", tipe="Tugas", tenggat=datetime(2025, 1, 1, 10, 0), deskripsi="Deskripsi awal."
    ))
    # Buat embedding secara manual
    todo_text_original = f"Todo: {todo_to_update.nama}. Type: {todo_to_update.tipe}. Due: {todo_to_update.tenggat}. Description: {todo_to_update.deskripsi or ''}."
    embedding_list = await embed_text_with_gemini(todo_text_original)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=todo_to_update.id_user, source_type="todo", source_id=str(todo_to_update.id_todo), text_original=todo_text_original
    ), embedding_list)
    session.commit()
    session.refresh(todo_to_update)

    updated_tipe = "Proyek"
    updated_deskripsi = "Deskripsi yang diperbarui untuk proyek."
    response = client.post(
        f"/update-todo/{todo_to_update.id_todo}",
        data={
            "tipe": updated_tipe,
            "deskripsi": updated_deskripsi
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah memperbarui todo"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    session.expire_all()  # Forces ORM cache to clear
    db_todo = crud.get_todo(session, todo_to_update.id_todo)
    assert db_todo.tipe == updated_tipe, "Tipe todo seharusnya diperbarui"
    assert db_todo.deskripsi == updated_deskripsi, "Deskripsi todo seharusnya diperbarui"
    assert db_todo.nama == todo_to_update.nama, "Nama todo seharusnya tidak berubah"

    # Verifikasi embedding todo diperbarui
    updated_embedding_text = f"Todo: {db_todo.nama}. Type: {db_todo.tipe}. Due: {db_todo.tenggat}. Description: {db_todo.deskripsi or ''}."
    todo_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="todo", source_id=str(db_todo.id_todo)
    ).first()
    assert todo_embedding.text_original == updated_embedding_text, "Embedding todo seharusnya diperbarui dengan teks baru"


@pytest.mark.asyncio
async def test_update_jadwal_matkul(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    jadwal_to_update = crud.create_jadwal_matkul(session, schemas.JadwalMatkulCreate(
        id_user=test_user.id_user, hari="Senin", nama="Matkul Awal", jam_mulai=time(8, 0), jam_selesai=time(10, 0), sks=2
    ))
    # Buat embedding secara manual
    jadwal_text_original = f"Jadwal Mata Kuliah: {jadwal_to_update.nama}. Hari: {jadwal_to_update.hari}. Mulai: {jadwal_to_update.jam_mulai}. Selesai: {jadwal_to_update.jam_selesai}. SKS: {jadwal_to_update.sks}."
    embedding_list = await embed_text_with_gemini(jadwal_text_original)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=jadwal_to_update.id_user, source_type="jadwal", source_id=str(jadwal_to_update.id_jadwal), text_original=jadwal_text_original
    ), embedding_list)
    session.commit()
    session.refresh(jadwal_to_update)

    updated_hari = "Rabu"
    updated_sks = 3
    response = client.post(
        f"/update-jadwal/{jadwal_to_update.id_jadwal}",
        data={
            "hari": updated_hari,
            "sks": updated_sks
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah memperbarui jadwal"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    session.expire_all()  # Forces ORM cache to clear
    db_jadwal = crud.get_jadwal_matkul(session, jadwal_to_update.id_jadwal)
    assert db_jadwal.hari == updated_hari, "Hari jadwal seharusnya diperbarui"
    assert db_jadwal.sks == updated_sks, "SKS jadwal seharusnya diperbarui"
    assert db_jadwal.nama == jadwal_to_update.nama, "Nama jadwal seharusnya tidak berubah"

    # Verifikasi embedding jadwal diperbarui
    updated_embedding_text = f"Jadwal Mata Kuliah: {db_jadwal.nama}. Hari: {db_jadwal.hari}. Mulai: {db_jadwal.jam_mulai}. Selesai: {db_jadwal.jam_selesai}. SKS: {db_jadwal.sks}."
    jadwal_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="jadwal", source_id=str(db_jadwal.id_jadwal)
    ).first()
    assert jadwal_embedding.text_original == updated_embedding_text, "Embedding jadwal seharusnya diperbarui dengan teks baru"


@pytest.mark.asyncio
async def test_update_ukm(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    ukm_to_update = crud.create_ukm(session, schemas.UKMCreate(
        id_user=test_user.id_user, nama="UKM Lama", jabatan="Anggota", deskripsi="Deskripsi lama."
    ))
    # Buat embedding secara manual
    ukm_text_original = f"UKM: {ukm_to_update.nama}. Jabatan: {ukm_to_update.jabatan}. Description: {ukm_to_update.deskripsi or ''}."
    embedding_list = await embed_text_with_gemini(ukm_text_original)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=ukm_to_update.id_user, source_type="ukm", source_id=str(ukm_to_update.id_ukm), text_original=ukm_text_original
    ), embedding_list)
    session.commit()
    session.refresh(ukm_to_update)

    updated_jabatan = "Ketua"
    updated_deskripsi = "Deskripsi yang diperbarui untuk ketua UKM."
    response = client.post(
        f"/update-ukm/{ukm_to_update.id_ukm}",
        data={
            "jabatan": updated_jabatan,
            "deskripsi": updated_deskripsi
        },
        follow_redirects=False
    )
    assert response.status_code == 303, "Seharusnya mengarahkan ulang setelah memperbarui UKM"
    assert response.headers["location"] == "/", "Seharusnya mengarahkan ke halaman utama"

    session.expire_all()  # Forces ORM cache to clear
    db_ukm = crud.get_ukm(session, ukm_to_update.id_ukm)
    assert db_ukm.jabatan == updated_jabatan, "Jabatan UKM seharusnya diperbarui"
    assert db_ukm.deskripsi == updated_deskripsi, "Deskripsi UKM seharusnya diperbarui"
    assert db_ukm.nama == ukm_to_update.nama, "Nama UKM seharusnya tidak berubah"

    # Verifikasi embedding UKM diperbarui
    updated_embedding_text = f"UKM: {db_ukm.nama}. Jabatan: {db_ukm.jabatan}. Description: {db_ukm.deskripsi or ''}."
    ukm_embedding = session.query(models.RAGSEmbedding).filter_by(
        source_type="ukm", source_id=str(db_ukm.id_ukm)
    ).first()
    assert ukm_embedding.text_original == updated_embedding_text, "Embedding UKM seharusnya diperbarui dengan teks baru"
