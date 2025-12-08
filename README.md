# RAG Workflow Explanation

This document explains the workflow of your personalized RAG (Retrieval Augmented Generation) system, from user interaction to the final AI response, detailing the functions involved.

## 1. Overall System Workflow

The system is a FastAPI application that allows users to store personal activities (like tasks, schedules, hobbies) as vector embeddings in a PostgreSQL database with the `pgvector` extension. When a user asks a question, the system retrieves relevant stored information (RAG), augments the question with this context, and then uses a Gemini Large Language Model (LLM) to generate a personalized answer.

### Components:
*   **FastAPI Backend:** Handles API requests, database interactions, and communication with the Gemini API.
*   **PostgreSQL + `pgvector`:** Stores user data and vector embeddings, enabling efficient similarity searches.
*   **Google Gemini API:** Used for both generating embeddings (vector representations of text) and generating natural language answers.
*   **Simple Frontend (HTML + Bootstrap):** Provides a basic user interface for adding activities and asking questions.

### High-Level Flow:

1.  **User Adds Activity:** User inputs personal information (e.g., "ngoding" as a hobby) via the web interface.
2.  **Activity Processing:** FastAPI receives the activity, converts its text into a vector embedding using Gemini, and stores it in the database.
3.  **User Asks Question:** User asks a question (e.g., "What are my hobbies?") via the web interface.
4.  **RAG Process:** FastAPI takes the question, converts it to an embedding, searches the database for similar stored activities, and uses the retrieved context to augment the user's question.
5.  **AI Generation:** The augmented question is sent to the Gemini LLM to generate a personalized answer.
6.  **Response & History:** The answer is returned to the user and both the question and answer are saved in the chat history.

---

## 2. Detailed RAG Process (Function by Function)

Let's break down the RAG process with the specific functions used in your `app/` directory.

### A. Initial Setup & User/Embedding Creation (`app/main.py`, `app/crud.py`, `app/rag.py`)

1.  **Application Startup (`app/main.py`)**:
    *   When your FastAPI application starts, the `create_tables_and_default_user` function is called.
    *   This function uses `app.db.Base.metadata.create_all(bind=engine)` to ensure all necessary tables (`users`, `rags_embeddings`, `ai_chat_history`) are created in your PostgreSQL database.
    *   It then checks if a default user (e.g., `id_user=1`) exists. If not, it calls `crud.create_user` to create one, preventing foreign key errors when activities are added.

2.  **Adding a User Activity (Endpoint: `POST /add-activity` in `app/main.py`)**:
    *   A user submits a form with `source_type` (e.g., "hobi") and `text_original` (e.g., "ngoding").
    *   **Embedding Generation (`app/rag.py`)**:
        *   The `embed_text_with_gemini(text: str)` function is called with the `text_original` (e.g., "ngoding").
        *   This function makes an asynchronous HTTP `POST` request to the `GEMINI_EMBED_URL` (e.g., `https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent`).
        *   It sends a JSON payload including the text, the model name (`gemini-embedding-001`), and specifies `output_dimensionality: 768`.
        *   The Gemini API returns a 768-dimensional vector (a list of floats) representing the semantic meaning of the text.
        *   **Retry Mechanism**: The `embed_text_with_gemini` function includes a retry loop with exponential backoff (`asyncio.sleep`) to handle transient network issues or API timeouts/disconnections.
    *   **Storing Embedding (`app/crud.py`)**:
        *   The generated `embedding_values` (the list of floats) and the activity details are passed to `crud.create_rags_embedding(db: Session, embedding: schemas.RAGSEmbeddingCreate, vector_embedding: List[float])`.
        *   This function creates a new `RAGSEmbedding` object in the database, storing the original text and its vector embedding in the `rags_embeddings` table. The `embedding` column is of type `VECTOR(768)`.

### B. Asking a Question & Generating an Answer (Endpoint: `POST /rag/query` in `app/main.py`)

1.  **User Submits Question (Endpoint: `POST /rag/query` in `app/main.py`)**:
    *   A user submits a JSON request with `id_user`, `question` (e.g., "Apa rencana kuliah saya minggu ini?"), and `top_k`.
    *   **Embedding the Question (`app/rag.py`)**:
        *   Similar to step 2a, the `embed_text_with_gemini(text: str)` function is called to convert the user's `question` into a vector embedding (`query_vector`).
    *   **Retrieving Similar RAGs (`app/rag.py`)**:
        *   The `retrieve_similar_rags(db: Session, query_vector: List[float], top_k: int)` function is called.
        *   This is where the magic of `pgvector` happens: it queries the `rags_embeddings` table to find stored embeddings that are most similar to the `query_vector`.
        *   The `db.query(models.RAGSEmbedding).order_by(models.RAGSEmbedding.embedding.l2_distance(query_vector))` line uses the `l2_distance` operator (Euclidean distance) provided by `pgvector.sqlalchemy` to calculate the distance between the question's embedding and all stored activity embeddings. The results are ordered by similarity (lowest distance first).
        *   `limit(top_k)` restricts the number of retrieved documents to the most relevant ones.
        *   The function returns a list of `RAGSEmbedding` objects, which are your retrieved "context documents".
    *   **Augmenting the Prompt (`app/rag.py`)**:
        *   The `augment_prompt(question: str, context_docs: List[models.RAGSEmbedding])` function takes the original `question` and the `context_docs`.
        *   It constructs a new, enhanced prompt for the LLM. This prompt typically looks like:
            ```
            Use the following context to answer the question.

            Context:
            [<source_type>#<id>] <text_original>
            ... (details from retrieved documents) ...

            Question: <user_question>

            Answer concisely and with actionable steps.
            ```
        *   This augmented prompt provides the LLM with relevant background information to generate a more accurate and personalized answer.
    *   **Generating the Answer (`app/rag.py`)**:
        *   The `generate_answer_with_gemini(augmented_prompt: str)` function is called with the newly constructed prompt.
        *   This function makes an asynchronous HTTP `POST` request to the `GEMINI_GEN_URL` (e.g., `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent`).
        *   It sends a JSON payload containing the augmented prompt in the `contents` field.
        *   The Gemini LLM processes the prompt and generates a natural language answer.
        *   **Retry Mechanism**: Similar to embedding, this function also includes a retry mechanism for robustness.
    *   **Saving Chat History (`app/crud.py`)**:
        *   Both the user's original `question` and the `answer` generated by Gemini are saved into the `ai_chat_history` table using `crud.create_ai_chat_history`.

2.  **Returning the Response (`app/main.py`)**:
    *   The generated `answer` and the `context_docs` used are returned to the user as a JSON response.

This complete workflow ensures that the AI's responses are not only generated by a powerful LLM but are also grounded in the user's specific, stored information, creating a personalized and contextually aware experience.
