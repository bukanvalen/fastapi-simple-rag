import pytest
from app import crud, schemas
from app.rag import embed_text_with_gemini

@pytest.mark.asyncio
async def test_rag_query(client, session):
    test_user = crud.get_user_by_email(session, "test@example.com")
    user_id = test_user.id_user

    # Tambahkan beberapa embedding spesifik untuk diambil oleh kueri RAG
    # Perhatikan: Kami menggunakan API Gemini asli di sini sesuai permintaan
    todo_text = "Rapat dengan klien pukul 10 pagi pada hari Senin."
    embedding1 = await embed_text_with_gemini(todo_text)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=user_id,
        source_type="tugas",
        source_id="manual_1", # Source ID tiruan
        text_original=todo_text
    ), embedding1)
    
    jadwal_text = "Janji dokter gigi pada Selasa sore."
    embedding2 = await embed_text_with_gemini(jadwal_text)
    crud.create_rags_embedding(session, schemas.RAGSEmbeddingCreate(
        id_user=user_id,
        source_type="jadwal",
        source_id="manual_2", # Source ID tiruan
        text_original=jadwal_text
    ), embedding2)
    session.commit()

    query_data = {
        "id_user": user_id,
        "question": "Kapan rapat atau janji temu saya?",
        "top_k": 2
    }
    response = client.post("/rag/query", json=query_data)
    
    if response.status_code != 200:
        print(f"Permintaan RAG gagal dengan status {response.status_code}: {response.text}")

    assert response.status_code == 200, "Permintaan RAG seharusnya berhasil"
    json_response = response.json()
    
    assert "answer" in json_response, "Respons seharusnya berisi 'answer'"
    assert "context_docs" in json_response, "Respons seharusnya berisi 'context_docs'"
    assert json_response["answer"] is not None, "Jawaban seharusnya tidak kosong"
    # Periksa bahwa konteks berisi informasi yang relevan
    context_texts = [doc["text_original"] for doc in json_response["context_docs"]]
    assert any("Rapat dengan klien" in text for text in context_texts), "Konteks seharusnya berisi informasi rapat klien"
    assert any("Janji dokter gigi" in text for text in context_texts), "Konteks seharusnya berisi informasi janji dokter gigi"

    # Verifikasi riwayat obrolan disimpan
    chat_history = crud.get_chat_history(session, user_id)
    # Seharusnya ada setidaknya 2 entri (pertanyaan pengguna + jawaban asisten)
    assert len(chat_history) >= 2, "Seharusnya ada setidaknya 2 entri riwayat obrolan" # Pembuatan pengguna awal mungkin juga membuat entri
    user_message_exists = any(entry.role == "user" and entry.message == query_data["question"] for entry in chat_history)
    assistant_message_exists = any(entry.role == "assistant" and entry.message == json_response["answer"] for entry in chat_history)
    assert user_message_exists, "Pesan pertanyaan pengguna seharusnya ada di riwayat obrolan"
    assert assistant_message_exists, "Pesan jawaban asisten seharusnya ada di riwayat obrolan"
