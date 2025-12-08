# **BACKEND_DETAILS.md**

This document provides a detailed overview of the FastAPI backend routes and references, designed to assist frontend development for the Personalized RAG System.

---

## **1. Base URL**

`http://localhost:8000` (assuming default `uvicorn` host and port)

---

## **2. Authentication**

No explicit authentication or authorization is implemented in this prototype. All endpoints are publicly accessible. `id_user` is used for data association and RAG query filtering but does not enforce access control.

---

## **3. Data Models (Pydantic Schemas for Request/Response Bodies)**

### **User**
*   **`UserCreate`**: For creating new users.
    ```json
    {
      "nama": "string",
      "email": "user@example.com",
      "telepon": "string", // optional
      "bio": "string",     // optional
      "lokasi": "string"   // optional
    }
    ```
*   **`UserUpdate`**: For updating existing users. All fields are optional for partial updates.
    ```json
    {
      "nama": "string",    // optional
      "email": "user@example.com", // optional
      "telepon": "string", // optional
      "bio": "string",     // optional
      "lokasi": "string"   // optional
    }
    ```

### **RAGSEmbedding**
*   Used internally, or for displaying context documents.
    ```json
    {
      "id_user": 0, // optional
      "source_type": "string",
      "source_id": "string", // optional
      "text_original": "string",
      "id_embedding": 0,
      "embedding": [0.0], // List of floats, 768 dimensions
      "created_at": "2023-10-27T10:00:00Z"
    }
    ```

### **AIChatHistory**
*   Used for storing chat interactions.
    ```json
    {
      "id_user": 0,
      "role": "user" | "assistant",
      "message": "string",
      "id_chat": 0,
      "created_at": "2023-10-27T10:00:00Z"
    }
    ```

### **Todo**
*   **`TodoCreate`**: For creating new Todo entries.
    ```json
    {
      "id_user": 0,
      "nama": "string",
      "tipe": "string",
      "tenggat": "2025-12-31T23:59:59.999Z", // optional (ISO 8601 format)
      "deskripsi": "string" // optional
    }
    ```
*   **`TodoUpdate`**: For updating existing Todo entries. All fields are optional for partial updates.
    ```json
    {
      "id_user": 0, // optional
      "nama": "string",    // optional
      "tipe": "string",    // optional
      "tenggat": "2025-12-31T23:59:59.999Z", // optional
      "deskripsi": "string" // optional
    }
    ```

### **JadwalMatkul (Course Schedule)**
*   **`JadwalMatkulCreate`**: For creating new Jadwal Matkul entries.
    ```json
    {
      "id_user": 0,
      "hari": "string",
      "nama": "string",
      "jam_mulai": "HH:MM:SS", // e.g., "09:00:00"
      "jam_selesai": "HH:MM:SS", // e.g., "11:00:00"
      "sks": 0
    }
    ```
*   **`JadwalMatkulUpdate`**: For updating existing Jadwal Matkul entries. All fields are optional for partial updates.
    ```json
    {
      "id_user": 0, // optional
      "hari": "string",    // optional
      "nama": "string",    // optional
      "jam_mulai": "HH:MM:SS", // optional
      "jam_selesai": "HH:MM:SS", // optional
      "sks": 0             // optional
    }
    ```

### **UKM (Student Activity Unit)**
*   **`UKMCreate`**: For creating new UKM entries.
    ```json
    {
      "id_user": 0,
      "nama": "string",
      "jabatan": "string",
      "deskripsi": "string" // optional
    }
    ```
*   **`UKMUpdate`**: For updating existing UKM entries. All fields are optional for partial updates.
    ```json
    {
      "id_user": 0, // optional
      "nama": "string",    // optional
      "jabatan": "string", // optional
      "deskripsi": "string" // optional
    }
    ```

### **RAGQuery**
*   For asking questions to the RAG system.
    ```json
    {
      "id_user": 0, // optional, for user-specific RAG
      "question": "string",
      "top_k": 5,   // optional, default 5
      "client_local_time": "2025-12-08T15:30:00.000Z" // optional, ISO 8601 format
    }
    ```

### **RAGResponse**
*   Response from the RAG query.
    ```json
    {
      "answer": "string",
      "context_docs": [
        // List of RAGSEmbedding objects
      ]
    }
    ```

---

## **4. API Endpoints**

### **CORS Middleware**
The FastAPI application is configured with `CORSMiddleware` to allow cross-origin requests. For development purposes, all origins, methods, and headers are currently allowed (`allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]`). This facilitates integration with separate frontend applications (e.g., React, Vue, Angular).

All `POST` endpoints for CRUD operations (add, update, delete) on the HTML frontend use `application/x-www-form-urlencoded` (form data). For React/frontend, you might prefer sending `application/json` with `fetch` or `axios`. The current FastAPI endpoints are set up to receive `Form(...)` parameters, which works directly with HTML forms. If you want to send JSON from React, the endpoint signatures in `app/main.py` would need to be adjusted to expect a JSON body (e.g., `item: schemas.ItemCreate`) instead of individual `Form(...)` parameters.

### **HTML Frontend Routes (via `GET`)**

*   **`GET /`**
    *   **Description**: Renders the main HTML page, displaying all users, todos, jadwal matkul, ukm, and RAG embeddings. Includes forms for adding and controls for deleting/updating.
    *   **Response**: HTML content.

### **User Management**

*   **`POST /add-user`**
    *   **Description**: Creates a new user entry and its associated RAG embedding.
    *   **Request Body (Form Data)**:
        *   `nama` (string, required)
        *   `email` (string, required)
        *   `telepon` (string, optional)
        *   `bio` (string, optional)
        *   `lokasi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /update-user/{user_id}`**
    *   **Description**: Updates an existing user's details and re-generates its RAG embedding if relevant fields are changed.
    *   **Path Parameter**: `user_id` (integer)
    *   **Request Body (Form Data)**:
        *   `nama` (string, optional)
        *   `email` (string, optional)
        *   `telepon` (string, optional)
        *   `bio` (string, optional)
        *   `lokasi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /delete-user/{user_id}`**
    *   **Description**: Deletes a user and all their associated RAG embeddings.
    *   **Path Parameter**: `user_id` (integer)
    *   **Response**: Redirects to `/`.

### **Todo Management**

*   **`POST /add-todo`**
    *   **Description**: Creates a new Todo entry and its associated RAG embedding.
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, required)
        *   `nama` (string, required)
        *   `tipe` (string, required)
        *   `tenggat` (string, optional, format: "YYYY-MM-DDTHH:MM")
        *   `deskripsi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /update-todo/{todo_id}`**
    *   **Description**: Updates an existing Todo entry and re-generates its RAG embedding if relevant fields are changed.
    *   **Path Parameter**: `todo_id` (integer)
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, optional)
        *   `nama` (string, optional)
        *   `tipe` (string, optional)
        *   `tenggat` (string, optional, format: "YYYY-MM-DDTHH:MM")
        *   `deskripsi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /delete-todo/{todo_id}`**
    *   **Description**: Deletes a Todo entry and its associated RAG embedding.
    *   **Path Parameter**: `todo_id` (integer)
    *   **Response**: Redirects to `/`.

### **Jadwal Matkul (Course Schedule) Management**

*   **`POST /add-jadwal`**
    *   **Description**: Creates a new Jadwal Matkul entry and its associated RAG embedding.
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, required)
        *   `hari` (string, required)
        *   `nama` (string, required)
        *   `jam_mulai` (string, required, format: "HH:MM")
        *   `jam_selesai` (string, required, format: "HH:MM")
        *   `sks` (integer, required)
    *   **Response**: Redirects to `/`.

*   **`POST /update-jadwal/{jadwal_id}`**
    *   **Description**: Updates an existing Jadwal Matkul entry and re-generates its RAG embedding if relevant fields are changed.
    *   **Path Parameter**: `jadwal_id` (integer)
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, optional)
        *   `hari` (string, optional)
        *   `nama` (string, optional)
        *   `jam_mulai` (string, optional, format: "HH:MM")
        *   `jam_selesai` (string, optional, format: "HH:MM")
        *   `sks` (integer, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /delete-jadwal/{jadwal_id}`**
    *   **Description**: Deletes a Jadwal Matkul entry and its associated RAG embedding.
    *   **Path Parameter**: `jadwal_id` (integer)
    *   **Response**: Redirects to `/`.

### **UKM (Student Activity Unit) Management**

*   **`POST /add-ukm`**
    *   **Description**: Creates a new UKM entry and its associated RAG embedding.
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, required)
        *   `nama` (string, required)
        *   `jabatan` (string, required)
        *   `deskripsi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /update-ukm/{ukm_id}`**
    *   **Description**: Updates an existing UKM entry and re-generates its RAG embedding if relevant fields are changed.
    *   **Path Parameter**: `ukm_id` (integer)
    *   **Request Body (Form Data)**:
        *   `id_user` (integer, optional)
        *   `nama` (string, optional)
        *   `jabatan` (string, optional)
        *   `deskripsi` (string, optional)
    *   **Response**: Redirects to `/`.

*   **`POST /delete-ukm/{ukm_id}`**
    *   **Description**: Deletes a UKM entry and its associated RAG embedding.
    *   **Path Parameter**: `ukm_id` (integer)
    *   **Response**: Redirects to `/`.

### **RAG Query**

*   **`POST /rag/query`**
    *   **Description**: Processes a natural language question using RAG, retrieves relevant context (optionally filtered by user), and generates an answer using Gemini. Also saves chat history. Includes `client_local_time` for time-sensitive queries.
    *   **Request Body (JSON)**: `schemas.RAGQuery`
        ```json
        {
          "id_user": 1,        // optional, for user-specific RAG
          "question": "Kapan rapat saya?",
          "top_k": 5,           // optional, default 5
          "client_local_time": "2025-12-08T15:30:00.000Z" // optional, ISO 8601 format
        }
        ```
    *   **Response (JSON)**: `schemas.RAGResponse`
        ```json
        {
          "answer": "Jawaban dari Gemini berdasarkan konteks.",
          "context_docs": [
            {
              "id_user": 1,
              "source_type": "todo",
              "source_id": "123",
              "text_original": "Rapat dengan klien pada hari Senin.",
              "id_embedding": 456,
              "embedding": [...], // truncated for brevity
              "created_at": "2023-10-27T10:00:00Z"
            }
          ]
        }
        ```

### **Chat History**

*   **`GET /chat-history/{user_id}`**
    *   **Description**: Retrieves the chat history for a specific user.
    *   **Path Parameter**: `user_id` (integer, required)
    *   **Response (JSON)**: `List[schemas.AIChatHistory]`
        ```json
        [
          {
            "id_user": 1,
            "role": "user",
            "message": "Apa rencana saya hari ini?",
            "id_chat": 1,
            "created_at": "2023-10-27T10:05:00Z"
          },
          {
            "id_user": 1,
            "role": "assistant",
            "message": "Berdasarkan data Anda, hari ini ada rapat jam 10 pagi.",
            "id_chat": 2,
            "created_at": "2023-10-27T10:05:15Z"
          }
        ]
        ```

---

## **5. Embedding Management Details**

For each creatable entity (User, Todo, Jadwal Matkul, UKM):
*   When an entity is **created**: A composite string is formed from its relevant text fields. This string is then embedded using Gemini and stored in the `rags_embeddings` table. The `source_type` and `source_id` fields in `rags_embeddings` link back to the original entity.
*   When an entity is **updated**: The application checks if any fields contributing to its RAG embedding have changed. If so, a new composite string is formed, a new embedding is generated, and the existing `rags_embeddings` entry for that `source_type` and `source_id` is updated with the new text and embedding.
*   When an entity is **deleted**: Its corresponding `rags_embeddings` entry (or entries, if multiple are associated) is also deleted using `source_type` and `source_id` to maintain data integrity. For users, all associated embeddings (user, todo, jadwal, ukm, chat history) are deleted via cascading deletes configured in `app/models.py`.

---

## **6. Time-Sensitive RAG**

This functionality has been implemented to allow Gemini to consider the current local time when generating responses.
*   **`client_local_time` Field**: The `POST /rag/query` endpoint now accepts an optional `client_local_time` field in the `RAGQuery` schema (ISO 8601 format). This field carries the user's local system time from the frontend.
*   **Prompt Augmentation**: The `augment_prompt` function (`app/rag.py`) integrates this `client_local_time` into the prompt sent to Gemini. It formats the time into a natural language string (e.g., "Given that the current local date and time is Monday, 08 December 2025 15:30:00 (from the user's local system), please consider this time information especially for time-sensitive queries.")
*   **Gemini Response**: Gemini is explicitly instructed to consider this time information in its responses, enabling more accurate and contextually relevant answers for time-sensitive questions.


---

## **7. Google Calendar Integration (Optional)**

*   **`POST /calendar/create-event`**
    *   **Description**: Endpoint for creating Google Calendar events. Requires Google API client setup.
    *   **Request Body (JSON)**: `schemas.CalendarEventCreate`
        ```json
        {
          "summary": "Meeting with John",
          "description": "Discuss project progress", // optional
          "start_time": "2025-12-25T09:00:00Z", // ISO 8601 format
          "end_time": "2025-12-25T10:00:00Z"   // ISO 8601 format
        }
        ```
    *   **Response**: `{"message": "Calendar event creation not yet implemented. Please refer to the code for integration instructions."}` (Currently a placeholder)