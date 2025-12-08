# **GEMINI.md**

This file describes the full specification for an AI-powered RAG System using **FastAPI**, **PostgreSQL + pgvector**, **Google Gemini API**, and optional **Gemini CLI Agent Mode** to automatically generate code.

Gemini CLI may read only this file to generate the entire project from scratch.

---

# **1. Project Goal**

Build a fast prototype of a **personalized RAG system** that uses:

* **FastAPI only** (no Laravel)
* **PostgreSQL** with **pgvector** extension
* **Gemini** for:

  * embeddings
  * text generation
* Minimal frontend (simple HTML + Bootstrap)
* CRUD forms for adding/deleting user activities (stored as embeddings)
* RAG retrieval of user-specific context
* Optional Google Calendar integration
* Unit tests
* Gemini CLI agent compatibility

The system must allow:

* Users to enter personal information (tugas, jadwal, hobi, cv, pengalaman, dll)
* System stores these as vector embeddings
* When user asks a question → system performs RAG + Gemini generation

---

# **2. System Architecture (final)**

### Components:

1. **FastAPI backend**
2. **PostgreSQL + pgvector**
3. **Gemini API for embedding & generation**
4. **Simple frontend**
5. **Unit tests (pytest)**

### Architecture Flow:

1. User submits activity → FastAPI → generate embedding → save to DB
2. User asks question → embed question → pgvector similarity search → augmented context → Gemini → answer
3. Responses saved in chat history
4. Optional: output events to Google Calendar

---

# **3. Data Model (final)**

Use the following PostgreSQL tables:

### **users**

```
id_user (PK)
nama
email
telepon
bio
lokasi
```

### **rags_embeddings**

```
id_embedding (PK)
id_user (nullable)
source_type (varchar)      # e.g. user, todo, jadwal, ukm
source_id (nullable)       # e.g. id_user, id_todo, id_jadwal, id_ukm
text_original (text)
embedding VECTOR(768)      # Gemini embedding dimension
created_at timestamp
```

### **ai_chat_history**

```
id_chat (PK)
id_user
role ('user'|'assistant')
message text
created_at timestamp
```

### **todos**

```
id_todo (PK)
id_user (FK)
nama
tipe
tenggat timestamp
deskripsi
created_at timestamp
```

### **jadwal_matkul**

```
id_jadwal (PK)
id_user (FK)
hari
nama
jam_mulai time
jam_selesai time
sks
created_at timestamp
```

### **ukm**

```
id_ukm (PK)
id_user (FK)
nama
jabatan
deskripsi
created_at timestamp
```

---

# **4. PostgreSQL Setup (pgvector)**

Run inside psql:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Create index:

### If pgvector supports HNSW:

```sql
CREATE INDEX rags_embeddings_hnsw_idx
ON rags_embeddings
USING hnsw (embedding vector_l2_ops)
WITH (m=16, ef_construction=200);
```

### If older version → use IVFFLAT:

```sql
CREATE INDEX rags_embeddings_ivfflat_idx
ON rags_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists=100);
```

---

# **5. FastAPI Project Structure**

Gemini CLI should generate:

```
app/
  main.py
  db.py
  models.py
  schemas.py
  crud.py
  rag.py
  templates/index.html
  static/style.css
tests/test_api.py
requirements.txt
GEMINI.md   (this file)
```

---

# **6. Required Python Libraries**

```
fastapi
uvicorn
sqlalchemy
psycopg[binary]
pgvector
jinja2
python-dotenv
httpx
pytest
```

---

# **7. Required Environment Variables**

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ragdb
GEMINI_API_KEY=AIzaSyBQDHHbIAE6DNjLXCd8vooOUhRv2NQNHK0
GEMINI_EMBED_URL=https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedText?key=YOUR_KEY
GEMINI_GEN_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateText?key=YOUR_KEY
```

> If using **Gemini CLI instead of REST**, Gemini CLI agent should replace embedding & generation calls with subprocess calls. (See section 12.)

---

# **8. FastAPI Endpoints Specification**

Gemini CLI must implement the following endpoints:

### **GET /**

* Render HTML template
* Display all users, todos, jadwal matkul, ukm, and embeddings
* Forms to add new user, todo, jadwal matkul, ukm

### **POST /add-user**

Form fields:

* nama
* email
* telepon (optional)
* bio (optional)
* lokasi (optional)

Behavior:

1. Create user in DB
2. Generate embedding for user data
3. Insert user embedding into DB
4. Redirect to "/"

### **POST /update-user/{id_user}**

Form fields: (all optional, for partial update)

* nama
* email
* telepon
* bio
* lokasi

Behavior:

1. Update user in DB
2. Re-generate and update user embedding if relevant fields changed
3. Redirect to "/"

### **POST /delete-user/{id_user}**

Deletes a user and all associated RAG embeddings.

### **POST /add-todo**

Form fields:

* id_user
* nama
* tipe
* tenggat (optional, datetime-local format)
* deskripsi (optional)

Behavior:

1. Create todo in DB
2. Generate embedding for todo data
3. Insert todo embedding into DB
4. Redirect to "/"

### **POST /update-todo/{id_todo}**

Form fields: (all optional, for partial update)

* id_user
* nama
* tipe
* tenggat (optional, datetime-local format)
* deskripsi (optional)

Behavior:

1. Update todo in DB
2. Re-generate and update todo embedding if relevant fields changed
3. Redirect to "/"

### **POST /delete-todo/{id_todo}**

Deletes a todo entry and its associated RAG embedding.

### **POST /add-jadwal**

Form fields:

* id_user
* hari
* nama
* jam_mulai (time format e.g. "09:00")
* jam_selesai (time format e.g. "11:00")
* sks

Behavior:

1. Create jadwal matkul in DB
2. Generate embedding for jadwal matkul data
3. Insert jadwal matkul embedding into DB
4. Redirect to "/"

### **POST /update-jadwal/{id_jadwal}**

Form fields: (all optional, for partial update)

* id_user
* hari
* nama
* jam_mulai (time format)
* jam_selesai (time format)
* sks

Behavior:

1. Update jadwal matkul in DB
2. Re-generate and update jadwal matkul embedding if relevant fields changed
3. Redirect to "/"

### **POST /delete-jadwal/{id_jadwal}**

Deletes a jadwal matkul entry and its associated RAG embedding.

### **POST /add-ukm**

Form fields:

* id_user
* nama
* jabatan
* deskripsi (optional)

Behavior:

1. Create ukm in DB
2. Generate embedding for ukm data
3. Insert ukm embedding into DB
4. Redirect to "/"

### **POST /update-ukm/{id_ukm}**

Form fields: (all optional, for partial update)

* id_user
* nama
* jabatan
* deskripsi

Behavior:

1. Update ukm in DB
2. Re-generate and update ukm embedding if relevant fields changed
3. Redirect to "/"

### **POST /delete-ukm/{id_ukm}**

Deletes an ukm entry and its associated RAG embedding.

### **POST /rag/query**

JSON:

```
{
  "id_user": 1,
  "question": "Apa rencana kuliah saya minggu ini?",
  "top_k": 5
}
```

Behavior:

1. Embed question
2. Find similar rows (`ORDER BY embedding <-> query_vec`, filtered by `id_user` if provided)
3. Build augmented prompt
4. Call Gemini generate
5. Save chat history

Response:

```
{
  "answer": "...",
  "context_docs": [...]
}
```

---

# **9. RAG Logic (Gemini CLI should implement)**

### **Embedding**

Call Gemini embeddings model with:

```
POST GEMINI_EMBED_URL
{
  "input": "text..."
}
```

### **Retrieval (pgvector)**

SQL:

```sql
SELECT *
FROM rags_embeddings
ORDER BY embedding <-> :query_vec
LIMIT :top_k;
```

### **Augmentation**

Construct prompt:

```
Use the following context to answer the question.

Context:
[<source_type>#<id>] <text_original>
...

Question: <user_question>

Answer concisely and with actionable steps.
```

### **Generation**

POST Gemini generation model:

```
POST GEMINI_GEN_URL
{
  "prompt": "<augmented_prompt>"
}
```

---

# **10. Frontend Requirements**

Simple HTML with:

* Bootstrap 5
* Multiple separate forms for adding users, todos, jadwal matkul, and ukm.
* Tables listing users, todos, jadwal matkul, ukm, and embeddings.
* Delete buttons for each entry in the tables.
* Mechanisms to trigger update operations for each entry (e.g., via forms or modals not explicitly detailed here, but implied by backend updates).

No React, no Laravel, no SPA.

---

# **11. Unit Tests Specifications**

Gemini CLI must generate pytest tests:

### Tests must include:

* root page loads
* Comprehensive CRUD (Create, Read, Update, Delete) tests for:
    * Users (including embedding generation and deletion)
    * Todos (including embedding generation and deletion)
    * Jadwal Matkul (including embedding generation and deletion)
    * UKM (including embedding generation and deletion)
* rag/query returns answer (monkeypatch generation)
* chat history saving
* DB resets between tests
* All test messages in Bahasa Indonesia

Monkeypatch examples:

* Replace `embed_text_with_gemini` with fake vector
* Replace `generate_answer_with_gemini` with fake string

---

# **12. Support for Gemini CLI Agent Mode**

Gemini CLI Agent must:

### **Option A: Use REST API**

Already defined in ENV vars.

### **Option B: Use Gemini CLI subprocess**

Gemini CLI agent can generate code using:

```
gemini embed --model ... --text "..." --output json
```

Python example Gemini CLI should generate:

```python
import subprocess, json

def embed_with_cli(text):
    out = subprocess.check_output(["gemini", "embed", "--model", "embedding-001", "--text", text, "--output", "json"])
    data = json.loads(out)
    return data["embedding"]
```

### **Option C: Tools Mode**

Gemini CLI agent can expose FastAPI endpoints as tools for planning.

---

# **13. Google Calendar Integration (optional)**

Gemini CLI should create:

### Endpoint

`POST /calendar/create-event`

Fields:

```
summary
description
start_time
end_time
```

### Behavior:

1. Use Google API client
2. Create event in user’s Google Calendar
3. Return event ID

---

# **14. What the Agent Should Build**

Gemini CLI, using this file alone, must generate:

* Entire FastAPI directory structure
* Database models (users, rags_embeddings, ai_chat_history, todos, jadwal_matkul, ukm)
* Comprehensive CRUD logic (Create, Read, Update, Delete) for users, todos, jadwal matkul, ukm, and embeddings
* RAG logic
* Embedding + Generation functions
* Extended Frontend HTML with multiple forms and tables for various entities
* Unit tests
* Requirements.txt
* Instructions for running the server

---

# **15. Running the App**

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Set environment variables

```
export DATABASE_URL=...
export GEMINI_API_KEY=...
export GEMINI_EMBED_URL=...
export GEMINI_GEN_URL=...
```

### 3. Create tables

FastAPI auto-creates via SQLAlchemy on startup.

### 4. Run:

```
uvicorn app.main:app --reload
```

### 5. Open:

```
http://localhost:8000/
```

---

# **16. Summary**

Using this GEMINI.md, Gemini CLI agent must create an entire functional:

* FastAPI backend
* pgvector RAG pipeline
* Gemini embedding & generation system
* Comprehensive CRUD HTML UI for users, todos, jadwal matkul, ukm, and chat history
* Optional Google Calendar integration
* Unit tests

No external docs needed.
No Laravel.
No React.
Pure FastAPI prototype.

# **16. Notes**

The system is Windows 11, so use PowerShell commands
PostgreSQL 17 and pgvector are inside a Docker, so use this command to access it:
```
docker exec -it pg17-vector psql -U admin -d ragdb
```

---

# **17. Development Status**

The core FastAPI backend, pgvector RAG pipeline, Gemini embedding & generation system, and the comprehensive CRUD HTML UI for users, todos, jadwal matkul, and ukm have been successfully implemented.

**Key Updates:**
*   `requirements.txt` has been created with the necessary Python libraries.
*   All CRUD operations (Create, Read, Update, Delete) for users, todos, jadwal matkul, and ukm entities are fully functional, including automatic embedding generation, update, and deletion.
*   **CORS Middleware**: Implemented to allow cross-origin requests, facilitating integration with separate frontend applications.
*   **AI Chat Feature**: Developed a robust AI chat feature, including:
    *   **Time Sensitivity**: The system now incorporates client-side local time into the prompt for Gemini, allowing for time-sensitive responses.
    *   **Chat History**: Chat logs (user queries and AI responses) are saved per user and can be retrieved via a dedicated `GET /chat-history/{user_id}` endpoint.
*   The unit tests have been thoroughly updated to cover all new CRUD functionalities, including update operations.
*   All unit tests are passing (100%), and their assertion messages have been translated to Bahasa Indonesia for localized presentation.
*   The separate React frontend project is progressing well, with CRUD functionalities working as expected.

**Pending (Future Scope):**
*   Google Calendar integration.
*   OAuth integration for enhanced security and user management.

**Action Required**: To achieve 100% passing tests with real data, please ensure your `GEMINI_API_KEY` has sufficient quota or is not rate-limited. This agent cannot resolve API quota issues directly.