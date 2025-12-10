import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from app import models, crud
import logging
import os

logger = logging.getLogger(__name__)

# Map Indonesian days to RRULE days
HARI_MAP = {
    "Senin": "MO",
    "Selasa": "TU",
    "Rabu": "WE",
    "Kamis": "TH",
    "Jumat": "FR",
    "Sabtu": "SA",
    "Minggu": "SU"
}

def get_creds(user: models.User):
    if not user.access_token:
        return None
    
    creds = Credentials(
        token=user.access_token,
        refresh_token=user.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    return creds

def get_service(user: models.User):
    creds = get_creds(user)
    if not creds:
        return None
    try:
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to build calendar service: {e}")
        return None

def get_or_create_todo_calendar(db: Session, user: models.User) -> str:
    """
    Returns the ID of the 'My Campus - Reminder' calendar.
    Creates it if it doesn't exist.
    """
    if user.todo_calendar_id:
        return user.todo_calendar_id
    
    service = get_service(user)
    if not service:
        return None

    base_name = user.calendar_name or "My Campus"
    calendar_summary = f"{base_name} - Reminder"
    
    # 1. Search existing calendars
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == calendar_summary:
                # Found it, save and return
                user.todo_calendar_id = calendar_list_entry['id']
                db.commit()
                return user.todo_calendar_id
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
            
    # 2. Create if not found
    calendar = {
        'summary': calendar_summary,
        'timeZone': 'Asia/Jakarta' # Defaulting to WIB logic or standard
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    
    user.todo_calendar_id = created_calendar['id']
    db.commit()
    return user.todo_calendar_id

def create_semester_calendar(db: Session, user: models.User, semester: models.Semester) -> str:
    if semester.google_calendar_id:
        return semester.google_calendar_id
        
    service = get_service(user)
    if not service:
        return None
        
    base_name = user.calendar_name or "My Campus"
    calendar_summary = f"{base_name} - {semester.tipe} {semester.tahun_ajaran}"
    
    calendar = {
        'summary': calendar_summary,
        'timeZone': 'Asia/Jakarta'
    }
    created_calendar = service.calendars().insert(body=calendar).execute()
    
    semester.google_calendar_id = created_calendar['id']
    db.commit()
    return semester.google_calendar_id

def create_todo_event(db: Session, user: models.User, todo: models.Todo):
    service = get_service(user)
    if not service:
        return None
    
    calendar_id = get_or_create_todo_calendar(db, user)
    if not calendar_id:
        return None

    if not todo.tenggat:
        return None
        
    start_time = todo.tenggat
    end_time = start_time + datetime.timedelta(hours=1)
    
    event = {
        'summary': todo.nama,
        'description': todo.deskripsi or "",
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Jakarta'},
    }

    try:
        result = service.events().insert(calendarId=calendar_id, body=event).execute()
        return result.get('id')
    except Exception as e:
        logger.error(f"Error creating todo event: {e}")
        return None

def create_recurring_class_event(db: Session, user: models.User, semester: models.Semester, jadwal: models.JadwalMatkul):
    """
    Creates a recurring event for the class schedule.
    """
    if not semester.google_calendar_id:
        create_semester_calendar(db, user, semester)
        
    service = get_service(user)
    if not service or not semester.google_calendar_id:
        return None
        
    # Validations
    if not jadwal.hari in HARI_MAP:
        logger.error(f"Invalid hari: {jadwal.hari}")
        return None
        
    rrule_day = HARI_MAP[jadwal.hari]
    
    # Construct start datetime for the FIRST occurrence
    # We need to find the first {jadwal.hari} on or after {semester.tanggal_mulai}
    # This logic is crucial.
    
    start_date = semester.tanggal_mulai # This is a date object
    
    target_weekday = -1
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    try:
        target_weekday = days.index(jadwal.hari) # 0=Senin, 6=Minggu
    except ValueError:
        return None
        
    # Calculate offset to first occurrence
    # start_date.weekday() returns 0=Monday, 6=Sunday
    current_weekday = start_date.weekday()
    days_ahead = target_weekday - current_weekday
    if days_ahead < 0: # Target day already happened this week
        days_ahead += 7
    
    first_occurrence_date = start_date + datetime.timedelta(days=days_ahead)
    
    # Combine date with time
    start_dt = datetime.datetime.combine(first_occurrence_date, jadwal.jam_mulai)
    end_dt = datetime.datetime.combine(first_occurrence_date, jadwal.jam_selesai)
    
    # RRULE UNTIL needs to be in UTC string usually, e.g. 20251231T235959Z
    # Or just YYYYMMDD if value is DATE.
    until_str = semester.tanggal_selesai.strftime("%Y%m%dT235959Z")
    
    event = {
        'summary': jadwal.nama,
        'description': f"SKS: {jadwal.sks}",
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'recurrence': [
            f"RRULE:FREQ=WEEKLY;BYDAY={rrule_day};UNTIL={until_str}"
        ]
    }
    
    try:
        result = service.events().insert(calendarId=semester.google_calendar_id, body=event).execute()
        return result.get('id')
    except Exception as e:
        logger.error(f"Error creating recurring event: {e}")
        return None

def delete_event(db: Session, user: models.User, event_id: str, calendar_id: str = 'primary'):
    service = get_service(user)
    if not service:
        return

    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except Exception as e:
        logger.error(f"Error deleting event: {e}")

def sync_todos_to_calendar(db: Session, user: models.User):
    # Updated to use dedicated calendar
    calendar_id = get_or_create_todo_calendar(db, user)
    if not calendar_id:
        return 0

    todos = crud.get_todos_by_user(db, user.id_user)
    service = get_service(user)
    if not service: 
        return 0

    synced = 0
    for todo in todos:
        if todo.tenggat and not todo.google_event_id:
             # Create logic reused
             event_id = create_todo_event(db, user, todo)
             if event_id:
                 todo.google_event_id = event_id
                 synced += 1
    
    # Update Calendar Name if it exists
    if calendar_id:
        base_name = user.calendar_name or "My Campus"
        expected_summary = f"{base_name} - Reminder"
        update_calendar_metadata(user, calendar_id, expected_summary)
    
    if synced > 0:
        db.commit()
    return synced

def delete_calendar(user: models.User, calendar_id: str):
    """Deletes a secondary calendar permanently."""
    service = get_service(user)
    if not service:
        return
    try:
        service.calendars().delete(calendarId=calendar_id).execute()
        logger.info(f"Calendar deleted: {calendar_id}")
    except Exception as e:
        logger.error(f"Error deleting calendar {calendar_id}: {e}")

def update_calendar_metadata(user: models.User, calendar_id: str, new_summary: str):
    """Updates the name/summary of a calendar."""
    service = get_service(user)
    if not service:
        return
    try:
        calendar = service.calendars().get(calendarId=calendar_id).execute()
        calendar['summary'] = new_summary
        service.calendars().update(calendarId=calendar_id, body=calendar).execute()
        logger.info(f"Calendar updated: {calendar_id} -> {new_summary}")
    except Exception as e:
        logger.error(f"Error updating calendar {calendar_id}: {e}")

def update_todo_event(db: Session, user: models.User, todo: models.Todo):
    """Updates a Todo event in the dedicated calendar."""
    if not todo.google_event_id:
        # If no event exists, create one
        event_id = create_todo_event(db, user, todo)
        if event_id:
            todo.google_event_id = event_id
        return

    service = get_service(user)
    if not service:
        return
    
    calendar_id = get_or_create_todo_calendar(db, user)
    if not calendar_id:
        return

    if not todo.tenggat:
        # If deadline removed, maybe delete event? Or leave as is?
        # Let's delete it to keep sync accurate.
        delete_event(db, user, todo.google_event_id, calendar_id)
        todo.google_event_id = None
        return

    start_time = todo.tenggat
    end_time = start_time + datetime.timedelta(hours=1)

    event_patch = {
        'summary': todo.nama,
        'description': todo.deskripsi or "",
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Jakarta'},
    }

    try:
        service.events().patch(
            calendarId=calendar_id,
            eventId=todo.google_event_id,
            body=event_patch
        ).execute()
    except Exception as e:
        logger.error(f"Error updating todo event: {e}")

def update_semester_calendar(db: Session, user: models.User, semester: models.Semester):
    """
    Updates the Google Calendar name/summary for the semester.
    """
    if not semester.google_calendar_id:
        create_semester_calendar(db, user, semester)
        return

    base_name = user.calendar_name or "My Campus"
    new_summary = f"{base_name} - {semester.tipe} {semester.tahun_ajaran}"
    update_calendar_metadata(user, semester.google_calendar_id, new_summary)

def update_recurring_event(db: Session, user: models.User, semester: models.Semester, jadwal: models.JadwalMatkul):
    """
    Syncs changes to a class schedule.
    If calendar_id changed (semester changed), delete old and create new.
    Otherwise, patch the existing event.
    """
    if not semester.google_calendar_id:
        return None
        
    service = get_service(user)
    if not service:
        return None

    # If the event doesn't exist yet, create it
    if not jadwal.google_event_id:
         return create_recurring_class_event(db, user, semester, jadwal)

    # We assume the event exists in the CURRENT semester's calendar.
    # Note: If the user changed the semester ID in the DB before calling this, 
    # we might have lost track of the OLD calendar ID. 
    # Ideally, the caller handles the 'move' logic logic if semester changed.
    # For now, we assume this is called AFTER update, and we just try to patch.
    # If the semester changed, the caller should have deleted the old event first.
    
    # Validation
    if not jadwal.hari in HARI_MAP:
        return None
    rrule_day = HARI_MAP[jadwal.hari]
    
    # Recalculate Start/End based on Semester Start + Day Offset (Same logic as create)
    start_date = semester.tanggal_mulai
    
    target_weekday = -1
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    try:
        target_weekday = days.index(jadwal.hari)
    except ValueError:
        return None
        
    current_weekday = start_date.weekday()
    days_ahead = target_weekday - current_weekday
    if days_ahead < 0: 
        days_ahead += 7
    
    first_occurrence_date = start_date + datetime.timedelta(days=days_ahead)
    
    start_dt = datetime.datetime.combine(first_occurrence_date, jadwal.jam_mulai)
    end_dt = datetime.datetime.combine(first_occurrence_date, jadwal.jam_selesai)
    until_str = semester.tanggal_selesai.strftime("%Y%m%dT235959Z")
    
    event_patch = {
        'summary': jadwal.nama,
        'description': f"SKS: {jadwal.sks}",
        'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Jakarta'},
        'recurrence': [
            f"RRULE:FREQ=WEEKLY;BYDAY={rrule_day};UNTIL={until_str}"
        ]
    }
    
    try:
        service.events().patch(
            calendarId=semester.google_calendar_id, 
            eventId=jadwal.google_event_id, 
            body=event_patch
        ).execute()
        return jadwal.google_event_id
    except Exception as e:
        logger.error(f"Error updating recurring event: {e}")
        return None

def update_all_matkul_for_semester(db: Session, user: models.User, semester: models.Semester):
    """
    Ghost update: Iterates all matkuls in semester and forces a patch update
    to satisfy the calendar's new state (e.g. if semester dates changed).
    """
    if not semester.jadwal_matkul:
        return
        
    for jadwal in semester.jadwal_matkul:
        update_recurring_event(db, user, semester, jadwal)

def resync_all_user_calendars(db: Session, user: models.User):
    """
    Resyncs Todo and Semester calendars.
    Useful if calendar_name changed or for manual trigger.
    """
    # 1. Sync Todos
    sync_todos_to_calendar(db, user)
    
    # 2. Sync Semesters (Names) and Matkuls
    semesters = crud.get_semesters_by_user(db, user.id_user)
    for semester in semesters:
        update_semester_calendar(db, user, semester)
        # Also sync matkuls
        update_all_matkul_for_semester(db, user, semester)
