# Frontend Backend Requirements

This document outlines the API endpoints that the React frontend application expects from the FastAPI backend. These endpoints are crucial for dynamic data display, management, and AI interaction.

---

## **1. Base URL**

`http://localhost:8000` (assuming default `uvicorn` host and port)

---

## **2. API Endpoints for Data Retrieval and Management**

### **2.1. User Management**

*   **`GET /users`**
    *   **Description**: Retrieves a list of all User objects.
    *   **Response (JSON Example)**:
        ```json
        [
          {
            "id_user": 1,
            "nama": "John Doe",
            "email": "john@example.com",
            "telepon": "123-456-7890",
            "bio": "Software Engineer",
            "lokasi": "New York"
          }
        ]
        ```
*   **`POST /add-user`**
    *   **Description**: Creates a new user.
    *   **Request Body (Form Data)**: Expects `nama` (string, required), `email` (string, required), `telepon` (string, optional), `bio` (string, optional), `lokasi` (string, optional).
*   **`POST /update-user/{user_id}`**
    *   **Description**: Updates an existing user.
    *   **Path Parameter**: `user_id` (integer).
    *   **Request Body (Form Data)**: Expects any of the `UserUpdate` fields (all optional for partial updates) plus `id_user` in the form data for consistency.
*   **`POST /delete-user/{user_id}`**
    *   **Description**: Deletes a user.
    *   **Path Parameter**: `user_id` (integer).

### **2.2. Tugas Akademik (Todo) Management**

*   **`GET /todos?id_user={id_user}`**
    *   **Description**: Retrieves a list of Todo objects, filtered by `id_user`.
    *   **Query Parameter**: `id_user` (integer, required).
    *   **Response (JSON Example)**:
        ```json
        [
          {
            "id_todo": 1, // Frontend expects this ID for updates/deletions
            "id_user": 1,
            "nama": "Frontend Development",
            "tipe": "Homework",
            "tenggat": "2025-12-31T23:59:59.999Z",
            "deskripsi": "Complete the React UI for the RAG system"
          }
        ]
        ```
*   **`POST /add-todo`**
    *   **Description**: Creates a new Todo entry.
    *   **Request Body (Form Data)**: Expects `id_user` (integer, required), `nama` (string, required), `tipe` (string, required), `tenggat` (string, optional, format: "YYYY-MM-DDTHH:MM"), `deskripsi` (string, optional).
*   **`POST /update-todo/{todo_id}`**
    *   **Description**: Updates an existing Todo entry.
    *   **Path Parameter**: `todo_id` (integer).
    *   **Request Body (Form Data)**: Expects any of the `TodoUpdate` fields (all optional for partial updates) plus `id_user` and `id_todo` in the form data for consistency.
*   **`POST /delete-todo/{todo_id}`**
    *   **Description**: Deletes a Todo entry.
    *   **Path Parameter**: `todo_id` (integer).

### **2.3. Jadwal Matkul (Course Schedule) Management**

*   **`GET /jadwal?id_user={id_user}`**
    *   **Description**: Retrieves a list of Jadwal Matkul objects, filtered by `id_user`.
    *   **Query Parameter**: `id_user` (integer, required).
    *   **Response (JSON Example)**:
        ```json
        [
          {
            "id_jadwal": 1, // Frontend expects this ID for updates/deletions
            "id_user": 1,
            "hari": "Senin",
            "nama": "Algoritma & Struktur Data",
            "jam_mulai": "08:00:00",
            "jam_selesai": "10:00:00",
            "sks": 3
          }
        ]
        ```
*   **`POST /add-jadwal`**
    *   **Description**: Creates a new Jadwal Matkul entry.
    *   **Request Body (Form Data)**: Expects `id_user` (integer, required), `hari` (string, required), `nama` (string, required), `jam_mulai` (string, required, format: "HH:MM"), `jam_selesai` (string, required, format: "HH:MM"), `sks` (integer, required).
*   **`POST /update-jadwal/{jadwal_id}`**
    *   **Description**: Updates an existing Jadwal Matkul entry.
    *   **Path Parameter**: `jadwal_id` (integer).
    *   **Request Body (Form Data)**: Expects any of the `JadwalMatkulUpdate` fields (all optional for partial updates) plus `id_user` and `id_jadwal` in the form data for consistency.
*   **`POST /delete-jadwal/{jadwal_id}`**
    *   **Description**: Deletes a Jadwal Matkul entry.
    *   **Path Parameter**: `jadwal_id` (integer).

### **2.4. UKM (Student Activity Unit) Management**

*   **`GET /ukm?id_user={id_user}`**
    *   **Description**: Retrieves a list of UKM objects, filtered by `id_user`.
    *   **Query Parameter**: `id_user` (integer, required).
    *   **Response (JSON Example)**:
        ```json
        [
          {
            "id_ukm": 1, // Frontend expects this ID for updates/deletions
            "id_user": 1,
            "nama": "UKM Coding Club",
            "jabatan": "Anggota",
            "deskripsi": "Mengikuti berbagai workshop dan proyek coding"
          }
        ]
        ```
*   **`POST /add-ukm`**
    *   **Description**: Creates a new UKM entry.
    *   **Request Body (Form Data)**: Expects `id_user` (integer, required), `nama` (string, required), `jabatan` (string, required), `deskripsi` (string, optional).
*   **`POST /update-ukm/{ukm_id}`**
    *   **Description**: Updates an existing UKM entry.
    *   **Path Parameter**: `ukm_id` (integer).
    *   **Request Body (Form Data)**: Expects any of the `UKMUpdate` fields (all optional for partial updates) plus `id_user` and `id_ukm` in the form data for consistency.
*   **`POST /delete-ukm/{ukm_id}`**
    *   **Description**: Deletes a UKM entry.
    *   **Path Parameter**: `ukm_id` (integer).

### **2.5. AI Chat Functionality**

*   **`GET /chat-history/{user_id}`**
    *   **Description**: Retrieves the chat history for a specific user.
    *   **Path Parameter**: `user_id` (integer, required).
    *   **Response (JSON Example)**:
        ```json
        [
          {
            "id_chat": 1, // Frontend expects this ID for list keys
            "id_user": 1,
            "role": "user",
            "message": "Apa rencana saya hari ini?",
            "created_at": "2023-10-27T10:05:00Z"
          },
          {
            "id_chat": 2, // Frontend expects this ID for list keys
            "id_user": 1,
            "role": "assistant",
            "message": "Berdasarkan data Anda, hari ini ada rapat jam 10 pagi.",
            "created_at": "2023-10-27T10:05:15Z"
          }
        ]
        ```
*   **`POST /rag/query`**
    *   **Description**: Processes a natural language question using RAG and generates an answer.
    *   **Request Body (JSON)**: `schemas.RAGQuery`
        ```json
        {
          "id_user": 1,                                   // (integer, optional) for user-specific RAG
          "question": "Kapan rapat saya?",                 // (string, required)
          "top_k": 5,                                     // (integer, optional) default 5
          "client_local_time": "2025-12-08T15:30:00.000Z" // (string, optional) ISO 8601 format
        }
        ```
    *   **Response (JSON)**: `schemas.RAGResponse` (contains `answer` and `context_docs`).

---

## **3. Frontend Considerations**

*   **CORS Configuration**: The backend currently uses `CORSMiddleware` configured to allow all origins (`allow_origins=["*"]`). For production environments, it is highly recommended to restrict `allow_origins` to your specific frontend domain(s) for security reasons.
*   **Form Data vs. JSON**: The frontend uses `application/x-www-form-urlencoded` for `POST` requests related to add/update/delete operations, matching existing backend expectations. For RAG queries, `application/json` is used.
*   **ID Fields**: The frontend expects `id_user` for Users, `id_todo` for Todos, `id_jadwal` for Jadwal Matkul, `id_ukm` for UKM, and `id_chat` for chat history items as primary identifiers for list rendering, updates, and deletions. Please ensure your backend consistently returns these fields.
*   **Impersonation**: The frontend relies on an `id_user` from an "impersonated user" for most data operations and displays.
*   **Modal Styling**: Frontend modals use `bg-[rgba(0,0,0,0.5)]` for a semi-transparent background overlay.

---