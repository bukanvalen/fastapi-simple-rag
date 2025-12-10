# React Frontend Integration Guide

This guide details how the React frontend should interact with the FastAPI backend, focusing on the new Calendar and Semester synchronization features.

## 1. Project Structure Recommendation

It is highly recommended to organize your project as a Monorepo for easier management:

```
my-campus-monorepo/
├── backend/            # The FastAPI project (current fastapi-simple-rag folder)
└── frontend/           # Your React project
```

This allows you to open the root `my-campus-monorepo` in your code editor to view and debut both simultaneously.

## 2. Authentication Flow

The system uses **Session-based Authentication** via cookies.

*   **Login**: Redirect the user's browser window to `http://localhost:8000/login`.
    *   Example: `<button onClick={() => window.location.href = 'http://localhost:8000/login'}>Login with Google</button>`
*   **Check Auth Status**: There is currently no dedicated JSON endpoint for "me". You should create one or scrape it from the root HTML.
    *   *Recommendation*: Create a `GET /api/me` endpoint that returns `{ "user": { ... }, "logged_in": true }` or status 401.
*   **Logout**: Redirect to `http://localhost:8000/logout`.

## 3. Semester Management (Full Sync)

Semesters are now fully synced. **Creating** creates a Google Calendar. **Updating** renames it. **Deleting** removes it.

### Fetch Semesters
You can currently find semesters rendered in `index.html`. For React, you should access the database or create a JSON API endpoint.
*   **Endpoint**: `GET /` (HTML) - Needs to be refactored to `GET /api/semesters` for React JSON consumption.

### Create Semester
*   **URL**: `POST /add-semester`
*   **Method**: `POST` (Form Data)
*   **Payload**:
    *   `tipe`: "Ganjil" | "Genap"
    *   `tahun_ajaran`: e.g. "2025/2026"
    *   `tanggal_mulai`: "YYYY-MM-DD"
    *   `tanggal_selesai`: "YYYY-MM-DD"

### Update Semester (Syncs Calendar Name)
*   **URL**: `POST /update-semester/{id}`
*   **Method**: `POST` (Form Data)
*   **Payload**:
    *   `tipe`: "Ganjil" | "Genap"
    *   `tahun_ajaran`: "2025/2026"

### Delete Semester (Deletes Calendar & Events)
*   **URL**: `POST /delete-semester/{id}`
*   **Method**: `POST`
*   **Warning**: This deletes the associated Google Calendar and all Class Schedules (Jadwal Matkul) in the database.

## 4. Class Schedule (Jadwal Matkul) Management

Events are synced as **Recurring Weekly Events**.

### Create Schedule
*   **URL**: `POST /add-jadwal`
*   **Payload**:
    *   `id_semester`: (Int) ID of the semester.
    *   `hari`: "Senin" | "Selasa" | ... | "Minggu"
    *   `jam_mulai`: "HH:MM"
    *   `jam_selesai`: "HH:MM"
    *   `nama`: (String) Course Name
    *   `sks`: (Int)

### Update Schedule (Resyncs Event)
*   **URL**: `POST /update-jadwal/{id}`
*   **Behavior**: If you change the time or day, the old event is updated/referenced to the new time logic.
*   **Payload**: Any subset of the Create fields.

## 5. Todos (Dedicated Calendar)

Todos created with a deadline are added to the **"My Campus - Reminder"** calendar.

*   **Create**: `POST /add-todo`
*   **Delete**: `POST /delete-todo/{id}` (Removes from Calendar)
*   **Manual Sync**: `POST /calendar/sync` (Trigger this button if user feels out of sync).

## 6. Next Steps for React

1.  **API Refactor**: The current backend relies heavily on `RedirectResponse` (PRG Pattern) suitable for standard HTML apps. For a React SPA (Single Page App), you should refactor endpoints to return `JSONResponse`.
    *   Change `@app.post(..., response_class=RedirectResponse)` to returning Pydantic models.
2.  **CORS**: `CORSMiddleware` is already set up to allow requests from `localhost:3000`.
