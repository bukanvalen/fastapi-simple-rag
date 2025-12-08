# AI Chat Feature Implementation Guide

This document outlines the steps to implement an AI chat feature on your frontend, integrating with the existing FastAPI backend, handling chat history, and incorporating time-sensitive querying.

## 1. Overview of Chat Feature

The goal is to create an interactive chat interface where users can ask questions and receive AI-generated answers. This will leverage the existing `/rag/query` endpoint for AI processing.

## 2. Backend (FastAPI) Considerations

### 2.1. Chat History Saving

The `/rag/query` endpoint already includes logic to save chat history.
As seen in `app/main.py`:

```python
        # 5. Save chat history (for user question)
        if query.id_user:
            crud.create_ai_chat_history(db_session, schemas.AIChatHistoryCreate(
                id_user=query.id_user, role="user", message=query.question
            ))
            crud.create_ai_chat_history(db_session, schemas.AIChatHistoryCreate(
                id_user=query.id_user, role="assistant", message=answer
            ))
```

This means:
*   **Per-User Storage**: Chat messages (user query and AI response) are saved in the `ai_chat_history` table, linked to a specific `id_user`.
*   **Requirement**: Ensure `id_user` is always provided in your frontend calls to `/rag/query` if you want the chat history to be recorded.

### 2.2. Handling Time Sensitivity & Local Time

To make Gemini aware of the current time and handle time-sensitive queries, we need to pass the client's local time to the backend and then incorporate it into the prompt.

#### 2.2.1. Update `schemas.RAGQuery`

Modify `app/schemas.py` to include an optional `client_local_time` field in the `RAGQuery` schema. This field will hold the current local time from the client's browser.

**File: `app/schemas.py`**
Find the `RAGQuery` class and update it like this:

```python
class RAGQuery(BaseModel):
    id_user: Optional[int] = None
    question: str
    top_k: int = 5
    client_local_time: Optional[datetime] = None # Add this line
```
*(Note: `datetime` should be imported from the `datetime` module if not already.)*

#### 2.2.2. Update `rag_query` Endpoint

Modify the `app/main.py` file to accept the new `client_local_time` from the `RAGQuery` and pass it to the `augment_prompt` function.

**File: `app/main.py`**
Inside the `rag_query` endpoint:

```python
@app.post("/rag/query", response_model=schemas.RAGResponse)
async def rag_query(query: schemas.RAGQuery, db_session: Session = Depends(get_db)):
    try:
        # ... existing code ...

        # 3. Build augmented prompt
        # Pass client_local_time to augment_prompt
        augmented_prompt = rag.augment_prompt(query.question, context_docs, query.client_local_time)
        
        # ... existing code ...
```

#### 2.2.3. Update `augment_prompt` Function

Modify the `app/rag.py` file to accept the `client_local_time` and integrate it into the prompt.

**File: `app/rag.py`**
Update the `augment_prompt` function signature and logic:

```python
from datetime import datetime

# ... other imports and functions ...

def augment_prompt(question: str, context_docs: List[dict], client_local_time: Optional[datetime] = None) -> str:
    context_text = "\n".join([
        f"{doc['source_type']}#{doc['source_id']}] {doc['text_original']}"
        for doc in context_docs
    ])

    time_context = ""
    if client_local_time:
        # Format the client_local_time for natural language in the prompt
        formatted_time = client_local_time.strftime("%A, %d %B %Y %H:%M:%S")
        time_context = f"Given that the current local date and time is {formatted_time} (from the user's local system), " \
                       "please consider this time information especially for time-sensitive queries. "

    prompt = f"""Use the following context to answer the question.
{time_context}
Context:
{context_text}

Question: {question}

Answer concisely and with actionable steps.
"""
    return prompt
```

This way, if `client_local_time` is provided, the prompt will include this information, guiding Gemini to consider the current time for its responses.

### 2.3. Retrieving Chat History

While chat messages are saved, you'll need a dedicated endpoint to retrieve them for display on the frontend. A function `crud.get_chat_history` already exists in `app/crud.py` that can be used for this.

#### 2.3.1. Add a New Endpoint to `app/main.py`

Add a new `GET` endpoint to `app/main.py` to fetch chat history for a specific user.

**File: `app/main.py`**
Add this new endpoint, for example, after the existing list endpoints:

```python
# GET /chat-history/{user_id}
@app.get("/chat-history/{user_id}", response_model=List[schemas.AIChatHistory])
async def get_user_chat_history(user_id: int, db_session: Session = Depends(get_db)):
    chat_history = crud.get_chat_history(db_session, user_id)
    return chat_history
```

## 3. Frontend (HTML/JavaScript) Implementation

This section assumes you are developing a separate frontend application (e.g., in React, Vue, or plain HTML/JavaScript).

### 3.1. User Interface (UI)

Create a simple chat UI:
*   An input field (`<input type="text">` or `<textarea>`) for the user's question.
*   A button to submit the question.
*   A display area (e.g., a `<div>` or `<ul>`) to show chat messages (user questions and AI answers).
*   A way to specify `id_user` (e.g., a dropdown, a hidden input, or fetched from a user session if implemented).

Example basic HTML structure:

```html
<div id="chat-container">
    <div id="messages"></div>
    <div id="input-area">
        <input type="hidden" id="user-id" value="1"> <!-- Replace with dynamic user ID -->
        <input type="text" id="question-input" placeholder="Ask me anything...">
        <button id="send-button">Send</button>
    </div>
</div>
```

### 3.2. Capturing Local Time & Making the API Call for New Queries

Use JavaScript to:
1.  Get the `id_user` from your UI (e.g., from a hidden input or global state).
2.  Get the user's current local time.
3.  Construct the payload for the `/rag/query` endpoint.
4.  Send a `POST` request using `fetch` or `axios`.
5.  Handle the response and display it in the chat UI.

```javascript
document.getElementById('send-button').addEventListener('click', async () => {
    const userId = parseInt(document.getElementById('user-id').value); // Ensure it's an integer
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    const messagesDiv = document.getElementById('messages');

    if (!question) return;

    // Display user's question immediately
    messagesDiv.innerHTML += `<p><strong>You:</strong> ${question}</p>`;
    questionInput.value = ''; // Clear input

    // Capture client's local time
    const clientLocalTime = new Date().toISOString(); // ISO 8601 format

    try {
        const response = await fetch('http://localhost:8000/rag/query', { // Adjust URL if needed
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // If you have authentication, add your token here:
                // 'Authorization': 'Bearer YOUR_AUTH_TOKEN'
            },
            body: JSON.stringify({
                id_user: userId, // Include id_user
                question: question,
                top_k: 5, // Or allow user to configure
                client_local_time: clientLocalTime // Include local time
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        // Display AI's answer
        messagesDiv.innerHTML += `<p><strong>AI:</strong> ${data.answer}</p>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to bottom
    } catch (error) {
        console.error('Error fetching RAG query:', error);
        messagesDiv.innerHTML += `<p style="color: red;"><strong>AI Error:</strong> Could not get a response.</p>`;
    }
});
```

### 3.3. Displaying Past Chat History on Load

To display past chat history when the user opens the chat, you will fetch it using the new `GET /chat-history/{user_id}` endpoint.

```javascript
// Function to fetch and display chat history
async function loadChatHistory(userId) {
    const messagesDiv = document.getElementById('messages');
    messagesDiv.innerHTML = ''; // Clear existing messages before loading history

    try {
        const response = await fetch(`http://localhost:8000/chat-history/${userId}`, { // Adjust URL if needed
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const chatHistory = await response.json();

        chatHistory.forEach(message => {
            const sender = message.role === 'user' ? 'You' : 'AI';
            messagesDiv.innerHTML += `<p><strong>${sender}:</strong> ${message.message}</p>`;
        });
        messagesDiv.scrollTop = messagesDiv.scrollHeight; // Scroll to bottom
    } catch (error) {
        console.error('Error fetching chat history:', error);
        messagesDiv.innerHTML += `<p style="color: red;"><strong>Error loading history:</strong> Could not retrieve past messages.</p>`;
    }
}

// Call loadChatHistory when the page loads, using the appropriate user ID
// For example, if you have a hidden input for user ID:
document.addEventListener('DOMContentLoaded', () => {
    const userId = parseInt(document.getElementById('user-id').value);
    if (userId) {
        loadChatHistory(userId);
    }
});
```

---

## 4. Summary of Code Changes Needed

To summarize, you need to make the following modifications to your backend files:

1.  **`app/schemas.py`**: Add `client_local_time: Optional[datetime] = None` to `RAGQuery`.
2.  **`app/main.py`**:
    *   Add a new `GET /chat-history/{user_id}` endpoint.
    *   Pass `query.client_local_time` to `rag.augment_prompt` in the `/rag/query` endpoint.
3.  **`app/rag.py`**: Update `augment_prompt` to accept `client_local_time` and integrate it into the final prompt sent to Gemini. Make sure to import `datetime`.

After these backend changes, you can proceed with your frontend implementation using the JavaScript examples provided above.