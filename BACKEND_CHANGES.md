# Backend Changes & React Integration Guide

## 1. Schema Changes

### `Users` Table
*   **Added**: `google_id`, `picture`, `access_token`, `refresh_token` (for OAuth).
*   **Added**: `todo_calendar_id` (String) - Stores the Google Calendar ID for "My Campus - Reminder".

### `Todos` Table
*   **Added**: `google_event_id` (String) - Links local todo to Google Calendar event.

### `Semesters` Table (NEW)
*   **Fields**: `id_semester` (PK), `id_user` (FK), `tipe` ("Ganjil"/"Genap"), `tahun_ajaran` ("2025/2026"), `tanggal_mulai` (Date), `tanggal_selesai` (Date).
*   **Added**: `google_calendar_id` (String) - Stores ID for "My Campus - {Tipe} {Tahun}" calendar.

### `JadwalMatkul` Table
*   **Added**: `id_semester` (FK) - Links schedule to a semester.
*   **Added**: `google_event_id` (String) - Links to recurring GCal event.
*   **Changed**: `hari` is now an Enum in code, strict string in DB (Senin, Dienstag, etc. -> mapped to MO, TU, etc. for RRULE).

## 2. API Changes

### Authentication
*   `GET /login`: Initiates Google OAuth flow.
*   `GET /auth`: OAuth callback.
*   `GET /logout`: Clears session.
*   `POST /onboarding`: Updates user profile (bio, tel, location) after first login.
*   **Frontend Action**: React app should redirect browser to `http://localhost:8000/login` for sign-in. Session is cookie-based.

### Semesters
*   `POST /add-semester`: 
    *   Form Data: `tipe`, `tahun_ajaran`, `tanggal_mulai`, `tanggal_selesai`.
    *   **Effect**: Creates local semester AND a new Google Calendar "My Campus - ...".

### Jadwal Matkul
*   `POST /add-jadwal`:
    *   **New Field**: `id_semester` (Optional but recommended).
    *   **Effect**: If semester is selected, creates a **Recurring Event** (Weekly) in the Semester's Google Calendar from `tanggal_mulai` until `tanggal_selesai`.

### Calendar Sync
*   `POST /calendar/sync`: Manually triggers sync for all Todos to "My Campus - Reminder" calendar.

## 3. React Frontend Integration

1.  **Auth**:
    *   Check `current_user` from a profile endpoint (you might need to create `GET /me` or derive from `GET /` data).
    *   If not logged in, show "Login with Google" button pointing to backend `/login`.

2.  **Forms**:
    *   **Add Semester**: Needs date pickers for Start/End dates.
    *   **Add Jadwal**: 
        *   Fetch active semesters (`GET /` returns them in context, or create a list endpoint).
        *   Show Dropdown for Semester selection.
        *   Show Dropdown for Day (Senin-Minggu).

3.  **Calendars**:
    *   Users will see "My Campus - Reminder" and "My Campus - {Semester}" appear in their Google Calendar automatically.
