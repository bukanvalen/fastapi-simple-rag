from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from . import models, schemas, crud, db, auth, calendar_service

router = APIRouter(prefix="/api", tags=["api"])

# Dependency
def get_db():
    yield from db.get_db()

# --- USERS ---
@router.get("/me", response_model=schemas.User)
async def get_current_user_api(
    user: models.User = Depends(auth.get_current_active_user)
):
    """Get current logged in user"""
    return user

@router.post("/manual-sync")
def manual_sync(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    calendar_service.resync_all_user_calendars(db, current_user)
    return {"message": "Sync triggered"}

@router.get("/users", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

# --- SEMESTERS ---
@router.get("/semesters", response_model=List[schemas.Semester])
def read_semesters(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_semesters_by_user(db, current_user.id_user)

@router.post("/semesters", response_model=schemas.Semester)
def create_semester(
    semester: schemas.SemesterCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if semester.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_semester = crud.create_semester(db, semester)
    # Sync with Calendar
    calendar_service.create_semester_calendar(db, current_user, db_semester)
    return db_semester

@router.put("/semesters/{semester_id}", response_model=schemas.Semester)
def update_semester(
    semester_id: int, 
    semester_update: schemas.SemesterUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_semester = crud.get_semester(db, semester_id)
    if not db_semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    if db_semester.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    updated_semester = crud.update_semester(db, semester_id, semester_update)
    
    # Sync with Calendar (Rename)
    calendar_service.update_semester_calendar(db, current_user, updated_semester)
    # Ghost update for matkuls
    calendar_service.update_all_matkul_for_semester(db, current_user, updated_semester)
    
    return updated_semester

@router.delete("/semesters/{semester_id}")
def delete_semester(
    semester_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_semester = crud.get_semester(db, semester_id)
    if not db_semester:
        raise HTTPException(status_code=404, detail="Semester not found")
    if db_semester.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Sync with Calendar (Delete)
    calendar_service.delete_semester_calendar(db, current_user, db_semester)
    
    crud.delete_semester(db, semester_id)
    return {"message": "Semester deleted"}

# --- JADWAL MATKUL ---
@router.get("/jadwal", response_model=List[schemas.JadwalMatkul])
def read_jadwal(
    semester_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if semester_id:
        return crud.get_jadwal_matkul_by_semester(db, semester_id)
    return crud.get_jadwal_matkul_by_user(db, current_user.id_user)

@router.post("/jadwal", response_model=schemas.JadwalMatkul)
def create_jadwal(
    jadwal: schemas.JadwalMatkulCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if jadwal.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_jadwal = crud.create_jadwal_matkul(db, jadwal)
    
    # Sync
    if jadwal.id_semester:
        db_semester = crud.get_semester(db, jadwal.id_semester)
        if db_semester:
            event_id = calendar_service.create_recurring_class_event(db, current_user, db_semester, db_jadwal)
            if event_id:
                db_jadwal.google_event_id = event_id
                db.commit()

    return db_jadwal

@router.put("/jadwal/{jadwal_id}", response_model=schemas.JadwalMatkul)
def update_jadwal(
    jadwal_id: int, 
    jadwal_update: schemas.JadwalMatkulUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_jadwal = crud.get_jadwal_matkul(db, jadwal_id)
    if not db_jadwal:
        raise HTTPException(status_code=404, detail="Jadwal not found")
    if db_jadwal.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    updated_jadwal = crud.update_jadwal_matkul(db, jadwal_id, jadwal_update)
    
    # Sync Update
    if updated_jadwal.id_semester and updated_jadwal.google_event_id:
        db_semester = crud.get_semester(db, updated_jadwal.id_semester)
        if db_semester:
             calendar_service.update_recurring_event(db, current_user, db_semester, updated_jadwal)

    return updated_jadwal

@router.delete("/jadwal/{jadwal_id}")
def delete_jadwal(
    jadwal_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_jadwal = crud.get_jadwal_matkul(db, jadwal_id)
    if not db_jadwal:
        raise HTTPException(status_code=404, detail="Jadwal not found")
    if db_jadwal.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Sync Delete
    if db_jadwal.google_event_id and db_jadwal.id_semester:
         db_semester = crud.get_semester(db, db_jadwal.id_semester)
         if db_semester and db_semester.google_calendar_id:
             calendar_service.delete_event(db, current_user, db_jadwal.google_event_id, calendar_id=db_semester.google_calendar_id)

    crud.delete_jadwal_matkul(db, jadwal_id)
    return {"message": "Jadwal deleted"}

# --- TODOS ---
@router.get("/todos", response_model=List[schemas.Todo])
def read_todos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    return crud.get_todos_by_user(db, current_user.id_user)

@router.post("/todos", response_model=schemas.Todo)
def create_todo(
    todo: schemas.TodoCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    if todo.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_todo = crud.create_todo(db, todo)
    
    # Sync
    if todo.tenggat:
        event_id = calendar_service.create_todo_event(db, current_user, db_todo)
        if event_id:
            db_todo.google_event_id = event_id
            db.commit()
            
    return db_todo

@router.put("/todos/{todo_id}", response_model=schemas.Todo)
def update_todo(
    todo_id: int, 
    todo_update: schemas.TodoUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_todo = crud.get_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    updated_todo = crud.update_todo(db, todo_id, todo_update)
    
    # Update Sync
    if updated_todo:
         calendar_service.update_todo_event(db, current_user, updated_todo)
         db.commit() # Commit the potential google_event_id change if create happened inside update logic
    
    return updated_todo

@router.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_todo = crud.get_todo(db, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.id_user != current_user.id_user:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Sync Delete
    if db_todo.google_event_id:
        cal_id = current_user.todo_calendar_id if current_user.todo_calendar_id else 'primary'
        calendar_service.delete_event(db, current_user, db_todo.google_event_id, calendar_id=cal_id)

    crud.delete_todo(db, todo_id)
    return {"message": "Todo deleted"}
