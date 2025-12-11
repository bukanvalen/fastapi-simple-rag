from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime, time, date
import logging
import traceback

from . import models, schemas, crud, db, rag, auth, calendar_service, api, rag_service
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    db.Base.metadata.create_all(bind=db.engine)
    db.create_hnsw_index()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=auth.SECRET_KEY)

app.include_router(api.router)


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure Jinja2Templates
templates = Jinja2Templates(directory="app/templates")

# Dependency to get DB session
def get_db():
    yield from db.get_db()

# Root endpoint - Render HTML template (Section 8, 10)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db_session: Session = Depends(get_db)):
    rags_embeddings = crud.get_all_rags_embeddings(db_session)
    users = crud.get_users(db_session)
    todos = crud.get_all_todos(db_session)
    jadwal_matkul = crud.get_all_jadwal_matkul(db_session)
    jadwal_matkul = crud.get_all_jadwal_matkul(db_session)
    ukm = crud.get_all_ukm(db_session)
    
    current_user = await auth.get_current_user(request, db_session)
    semesters = []
    if current_user:
        semesters = crud.get_semesters_by_user(db_session, current_user.id_user)
    
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "rags_embeddings": rags_embeddings,
            "users": users,
            "todos": todos,
            "jadwal_matkul": jadwal_matkul,
            "jadwal_matkul": jadwal_matkul,
            "ukm": ukm,
            "current_user": current_user,
            "semesters": semesters
        }
    )

# --- AUTH ROUTES ---

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await auth.oauth.google.authorize_redirect(
        request, 
        redirect_uri, 
        access_type='offline', 
        prompt='consent'
    )

@app.get("/auth", name="auth_callback")
async def auth_callback(request: Request, db_session: Session = Depends(get_db)):
    try:
        token = await auth.oauth.google.authorize_access_token(request)
    except Exception as e:
        # Handle cases where user cancels or error occurs
        return RedirectResponse(url="/")
        
    user_info = token.get('userinfo')
    if not user_info:
        # Fallback if userinfo not in token (depends on scope/provider)
        user_info = await auth.oauth.google.userinfo(token=token)

    # user_info contains 'sub' (google_id), 'name', 'email', 'picture'
    email = user_info.get('email')
    nama = user_info.get('name')
    picture = user_info.get('picture')
    google_id = user_info.get('sub')
    
    # Check if user exists
    db_user = crud.get_user_by_email(db_session, email)
    
    if not db_user:
        # Create new user
        # We need to handle the case where we don't have all fields required by UserCreate yet
        # Ensure crud.create_user can handle this or do it manually here
        new_user = models.User(
            nama=nama,
            email=email,
            # Others optional
            google_id=google_id,
            picture=picture,
            access_token=token.get('access_token'),
            refresh_token=token.get('refresh_token')
        )
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)
        
        # Create embedding for new user automatically
        try:
             await crud.create_user_embedding(db_session, new_user)
        except Exception as e:
            logger.error(f"Failed to create embedding for new Google user: {e}")

        request.session['user_id'] = new_user.id_user
        # Redirect to React Frontend Onboarding or Profile
        return RedirectResponse(url="http://localhost:5173/")
    else:
        if not db_user.google_id:
             db_user.google_id = google_id
             db_user.picture = picture
        db_user.access_token = token.get('access_token')
        if token.get('refresh_token'):
            db_user.refresh_token = token.get('refresh_token')
        
        db_session.commit()
        request.session['user_id'] = db_user.id_user
        # Redirect to React Frontend
        return RedirectResponse(url="http://localhost:5173/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user_id', None)
    return RedirectResponse(url="http://localhost:5173/")

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request, db_session: Session = Depends(get_db)):
    user = await auth.get_current_user(request, db_session)
    if not user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "onboarding.html", {"user": user})

@app.post("/onboarding", response_class=RedirectResponse)
async def onboarding_submit(
    request: Request,
    telepon: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    lokasi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    user = await auth.get_current_user(request, db_session)
    if not user:
        return RedirectResponse(url="/")
    
    user_update = schemas.UserUpdate(
        telepon=telepon,
        bio=bio,
        lokasi=lokasi
    )
    crud.update_user(db_session, user.id_user, user_update)
    
    # Regnerate embedding using service
    await rag_service.update_user_embedding(db_session, user)
    
    return RedirectResponse(url="/", status_code=303)



# POST /add-user
@app.post("/add-user", response_class=RedirectResponse)
async def add_user(
    nama: str = Form(...),
    email: str = Form(...),
    telepon: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    lokasi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        user_create = schemas.UserCreate(
            nama=nama,
            email=email,
            telepon=telepon,
            bio=bio,
            lokasi=lokasi
        )
        db_user = crud.create_user(db_session, user_create)
        await rag_service.update_user_embedding(db_session, db_user) # Create embedding for the new user using service
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# POST /update-user/{user_id}
@app.post("/update-user/{user_id}", response_class=RedirectResponse)
async def update_user_route(
    user_id: int,
    nama: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telepon: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    lokasi: Optional[str] = Form(None),
    calendar_name: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        # Check if name changed for sync trigger
        user_update_data = schemas.UserUpdate(
            nama=nama,
            email=email,
            telepon=telepon,
            bio=bio,
            lokasi=lokasi,
            calendar_name=calendar_name
        )
        
        # We need to know if calendar_name changed to trigger resync
        current_db_user = crud.get_user(db_session, user_id)
        old_cal_name = current_db_user.calendar_name
        
        db_user = crud.update_user(db_session, user_id, user_update_data)
        
        # Trigger full resync if calendar name changed
        if db_user and db_user.calendar_name != old_cal_name:
             # This will rename all semester calendars
             calendar_service.resync_all_user_calendars(db_session, db_user)

        if db_user:
            # Re-generate and update user embedding if user data was changed
            await rag_service.update_user_embedding(db_session, db_user)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# POST /delete-user/{user_id}

@app.post("/delete-user/{user_id}", response_class=RedirectResponse)

async def delete_user_route(user_id: int, db_session: Session = Depends(get_db)):

    crud.delete_user(db_session, user_id)

    crud.delete_rags_embeddings_by_user_id(db_session, user_id) # Delete all related embeddings

    return RedirectResponse(url="/", status_code=303)



# --- JSON List Endpoints for Frontend ---



# GET /users

@app.get("/users", response_model=List[schemas.User])

async def get_users_json(db_session: Session = Depends(get_db)):

    users = crud.get_users(db_session)

    return users



# GET /todos

@app.get("/todos", response_model=List[schemas.Todo])

async def get_todos_json(

    id_user: Optional[int] = None,

    db_session: Session = Depends(get_db)

):

    if id_user:

        todos = crud.get_todos_by_user(db_session, id_user)

    else:

        todos = crud.get_all_todos(db_session)

    return todos



# GET /jadwal

@app.get("/jadwal", response_model=List[schemas.JadwalMatkul])

async def get_jadwal_json(

    id_user: Optional[int] = None,

    db_session: Session = Depends(get_db)

):

    if id_user:

        jadwal = crud.get_jadwal_matkul_by_user(db_session, id_user)

    else:

        jadwal = crud.get_all_jadwal_matkul(db_session)

    return jadwal



# GET /ukm

@app.get("/ukm", response_model=List[schemas.UKM])

async def get_ukm_json(

    id_user: Optional[int] = None,

    db_session: Session = Depends(get_db)

):

    if id_user:

        ukm = crud.get_ukm_by_user(db_session, id_user)

    else:

        ukm = crud.get_all_ukm(db_session)

    return ukm

# GET /chat-history/{user_id}
@app.get("/chat-history/{user_id}", response_model=List[schemas.AIChatHistory])
async def get_user_chat_history(user_id: int, db_session: Session = Depends(get_db)):
    chat_history = crud.get_chat_history(db_session, user_id)
    return chat_history





# --- TODO Endpoints ---
@app.post("/add-todo", response_class=RedirectResponse)
async def add_todo(
    request: Request,
    id_user: int = Form(...),
    nama: str = Form(...),
    tipe: str = Form(...),
    tenggat: Optional[str] = Form(None), # Receive as string, parse later
    deskripsi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        tenggat_dt = datetime.fromisoformat(tenggat) if tenggat else None
        todo_create = schemas.TodoCreate(
            id_user=id_user,
            nama=nama,
            tipe=tipe,
            tenggat=tenggat_dt,
            deskripsi=deskripsi
        )
        db_todo = crud.create_todo(db_session, todo_create)
        
        # Calendar Sync (Phase 2)
        db_user = crud.get_user(db_session, id_user)
        if db_user and db_user.access_token and tenggat_dt:
             # Use the new service that handles dedicated calendar
             event_id = calendar_service.create_todo_event(db_session, db_user, db_todo)
             if event_id:
                 db_todo.google_event_id = event_id
                 db_session.commit()
        
        await rag_service.update_todo_embedding(db_session, db_todo)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-todo/{todo_id}", response_class=RedirectResponse)
async def delete_todo_route(todo_id: int, db_session: Session = Depends(get_db)):
    # Check for calendar event to delete
    db_todo = crud.get_todo(db_session, todo_id)
    if db_todo and db_todo.google_event_id:
         db_user = crud.get_user(db_session, db_todo.id_user)
         if db_user:
             # Phase 2: Delete from custom calendar if exists, or primary default logic handled in service
             # Check if we have calendar id stored or just try delete
             # For Todo, we typically used primary before, but now custom.
             # Service handles fetching the right calendar ID context if we update 'delete_event' 
             # But 'delete_event' in service takes specific calendar_id.
             
             # Let's get the ID to delete from.
             cal_id = db_user.todo_calendar_id if db_user.todo_calendar_id else 'primary'
             calendar_service.delete_event(db_session, db_user, db_todo.google_event_id, calendar_id=cal_id)

    crud.delete_todo(db_session, todo_id)
    crud.delete_rags_embedding_by_source_type_and_id(db_session, "todo", str(todo_id))
    return RedirectResponse(url="/", status_code=303)

@app.post("/update-todo/{todo_id}", response_class=RedirectResponse)
async def update_todo_route(
    todo_id: int,
    id_user: Optional[int] = Form(None),
    nama: Optional[str] = Form(None),
    tipe: Optional[str] = Form(None),
    tenggat: Optional[str] = Form(None), # Receive as string, parse later
    deskripsi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        tenggat_dt = datetime.fromisoformat(tenggat) if tenggat else None
        todo_update_data = schemas.TodoUpdate(
            id_user=id_user,
            nama=nama,
            tipe=tipe,
            tenggat=tenggat_dt,
            deskripsi=deskripsi
        )
        db_todo = crud.update_todo(db_session, todo_id, todo_update_data)

        if db_todo:
            # Re-generate and update embedding using service
            await rag_service.update_todo_embedding(db_session, db_todo)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# --- JADWAL MATKUL Endpoints ---
@app.post("/add-jadwal", response_class=RedirectResponse)
async def add_jadwal(
    id_user: int = Form(...),
    id_semester: Optional[int] = Form(None),
    hari: str = Form(...),
    nama: str = Form(...),
    jam_mulai: str = Form(...), # Receive as string, parse later
    jam_selesai: str = Form(...), # Receive as string, parse later
    sks: int = Form(...),
    db_session: Session = Depends(get_db)
):
    try:
        jam_mulai_time = time.fromisoformat(jam_mulai)
        jam_selesai_time = time.fromisoformat(jam_selesai)
        
        jadwal_create = schemas.JadwalMatkulCreate(
            id_user=id_user,
            id_semester=id_semester,
            hari=hari,
            nama=nama,
            jam_mulai=jam_mulai_time,
            jam_selesai=jam_selesai_time,
            sks=sks
        )
        db_jadwal = crud.create_jadwal_matkul(db_session, jadwal_create)
        
        # Calendar Sync (Phase 2: Recurring)
        if id_semester:
             db_semester = crud.get_semester(db_session, id_semester)
             db_user = crud.get_user(db_session, id_user)
             if db_semester and db_user and db_user.access_token:
                 event_id = calendar_service.create_recurring_class_event(db_session, db_user, db_semester, db_jadwal)
                 if event_id:
                     db_jadwal.google_event_id = event_id
                     db_session.commit()
        
        await rag_service.update_jadwal_embedding(db_session, db_jadwal)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-jadwal/{jadwal_id}", response_class=RedirectResponse)
async def delete_jadwal_route(jadwal_id: int, db_session: Session = Depends(get_db)):
    db_jadwal = crud.get_jadwal_matkul(db_session, jadwal_id)
    if db_jadwal and db_jadwal.google_event_id and db_jadwal.id_semester:
        # Need semester to know calendar ID
        db_semester = crud.get_semester(db_session, db_jadwal.id_semester)
        db_user = crud.get_user(db_session, db_jadwal.id_user)
        if db_semester and db_semester.google_calendar_id and db_user:
            calendar_service.delete_event(db_session, db_user, db_jadwal.google_event_id, calendar_id=db_semester.google_calendar_id)

    crud.delete_jadwal_matkul(db_session, jadwal_id)
    crud.delete_rags_embedding_by_source_type_and_id(db_session, "jadwal", str(jadwal_id))
    return RedirectResponse(url="/", status_code=303)

@app.post("/update-jadwal/{jadwal_id}", response_class=RedirectResponse)
async def update_jadwal_route(
    jadwal_id: int,
    id_user: Optional[int] = Form(None),
    id_semester: Optional[int] = Form(None),
    hari: Optional[str] = Form(None),
    nama: Optional[str] = Form(None),
    jam_mulai: Optional[str] = Form(None), # Receive as string, parse later
    jam_selesai: Optional[str] = Form(None), # Receive as string, parse later
    sks: Optional[int] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        jam_mulai_time = time.fromisoformat(jam_mulai) if jam_mulai else None
        jam_selesai_time = time.fromisoformat(jam_selesai) if jam_selesai else None
        jadwal_update_data = schemas.JadwalMatkulUpdate(
            id_user=id_user,
            id_semester=id_semester,
            hari=hari,
            nama=nama,
            jam_mulai=jam_mulai_time,
            jam_selesai=jam_selesai_time,
            sks=sks
        )
        db_jadwal = crud.update_jadwal_matkul(db_session, jadwal_id, jadwal_update_data)

        if db_jadwal:
            # Re-generate and update embedding using service
            await rag_service.update_jadwal_embedding(db_session, db_jadwal)
            
            # Calendar Sync Update (Phase 2.5)
            if db_jadwal.id_semester and db_jadwal.google_event_id:
                 db_semester = crud.get_semester(db_session, db_jadwal.id_semester)
                 db_user = crud.get_user(db_session, db_jadwal.id_user)
                 if db_semester and db_user:
                     calendar_service.update_recurring_event(db_session, db_user, db_semester, db_jadwal)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-ukm", response_class=RedirectResponse)
async def add_ukm(
    id_user: int = Form(...),
    nama: str = Form(...),
    jabatan: str = Form(...),
    deskripsi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        ukm_create = schemas.UKMCreate(
            id_user=id_user,
            nama=nama,
            jabatan=jabatan,
            deskripsi=deskripsi
        )
        db_ukm = crud.create_ukm(db_session, ukm_create)
        
        await rag_service.update_ukm_embedding(db_session, db_ukm)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-ukm/{ukm_id}", response_class=RedirectResponse)
async def delete_ukm_route(ukm_id: int, db_session: Session = Depends(get_db)):
    crud.delete_ukm(db_session, ukm_id)
    crud.delete_rags_embedding_by_source_type_and_id(db_session, "ukm", str(ukm_id))
    return RedirectResponse(url="/", status_code=303)

@app.post("/update-ukm/{ukm_id}", response_class=RedirectResponse)
async def update_ukm_route(
    ukm_id: int,
    id_user: Optional[int] = Form(None),
    nama: Optional[str] = Form(None),
    jabatan: Optional[str] = Form(None),
    deskripsi: Optional[str] = Form(None),
    db_session: Session = Depends(get_db)
):
    try:
        ukm_update_data = schemas.UKMUpdate(
            id_user=id_user,
            nama=nama,
            jabatan=jabatan,
            deskripsi=deskripsi
        )
        db_ukm = crud.update_ukm(db_session, ukm_id, ukm_update_data)

        if db_ukm:
            # Re-generate and update embedding using service
            await rag_service.update_ukm_embedding(db_session, db_ukm)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



# POST /rag/query (Section 8)
@app.post("/rag/query", response_model=schemas.RAGResponse)
async def rag_query(query: schemas.RAGQuery, db_session: Session = Depends(get_db)):
    try:
        # 1. Embed question
        query_embedding = await rag.embed_text_with_gemini(query.question)
        
        # 2. Find similar rows
        context_docs = rag.retrieve_similar_rags(db_session, query_embedding, query.top_k, query.id_user)
        
        # 3. Build augmented prompt
        augmented_prompt = rag.augment_prompt(query.question, context_docs, query.client_local_time)
        
        # 4. Call Gemini generate
        answer = await rag.generate_answer_with_gemini(augmented_prompt)

        # 5. Save chat history (for user question)
        if query.id_user:
            crud.create_ai_chat_history(db_session, schemas.AIChatHistoryCreate(
                id_user=query.id_user, role="user", message=query.question
            ))
            crud.create_ai_chat_history(db_session, schemas.AIChatHistoryCreate(
                id_user=query.id_user, role="assistant", message=answer
            ))
        
        return schemas.RAGResponse(answer=answer, context_docs=context_docs)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Optional: POST /calendar/create-event (Section 13)
@app.post("/calendar/sync", response_class=RedirectResponse)
async def manual_calendar_sync(request: Request, db_session: Session = Depends(get_db)):
    user = await auth.get_current_user(request, db_session)
    if user:
        calendar_service.sync_todos_to_calendar(db_session, user)
    return RedirectResponse(url="/", status_code=303)


# --- SEMESTER Endpoints (Phase 2) ---
@app.post("/add-semester", response_class=RedirectResponse)
async def add_semester(
    request: Request,
    tipe: str = Form(...),
    tahun_ajaran: str = Form(...),
    tanggal_mulai: str = Form(...),
    tanggal_selesai: str = Form(...),
    db_session: Session = Depends(get_db)
):
    user = await auth.get_current_user(request, db_session)
    if not user:
         return RedirectResponse(url="/")
         
    try:
        semester_create = schemas.SemesterCreate(
            id_user=user.id_user,
            tipe=tipe,
            tahun_ajaran=tahun_ajaran,
            tanggal_mulai=date.fromisoformat(tanggal_mulai),
            tanggal_selesai=date.fromisoformat(tanggal_selesai)
        )
        new_sem = crud.create_semester(db_session, semester_create)
        
        # Auto-create calendar immediately
        calendar_service.create_semester_calendar(db_session, user, new_sem)
        
    except Exception as e:
        logger.error(f"Error creating semester: {e}")
        logger.error(traceback.format_exc())
        
    return RedirectResponse(url="/", status_code=303)


@app.post("/delete-semester/{semester_id}", response_class=RedirectResponse)
async def delete_semester(semester_id: int, request: Request, db_session: Session = Depends(get_db)):
    user = await auth.get_current_user(request, db_session)
    if not user:
         return RedirectResponse(url="/")
         
    db_semester = crud.get_semester(db_session, semester_id)
    if db_semester:
        # 1. Delete Google Calendar if exists
        if db_semester.google_calendar_id:
            try:
                calendar_service.delete_calendar(user, db_semester.google_calendar_id)
            except Exception as e:
                logger.error(f"Failed to delete Google Calendar: {e}")
        
        # 2. Delete embeddings for all schedules in this semester
        for jadwal in db_semester.jadwal_matkul:
             crud.delete_rags_embedding_by_source_type_and_id(db_session, "jadwal", str(jadwal.id_jadwal))
             
        crud.delete_semester(db_session, semester_id)

    return RedirectResponse(url="/", status_code=303)


@app.post("/update-semester/{semester_id}", response_class=RedirectResponse)
async def update_semester(
    semester_id: int, 
    request: Request, 
    tipe: str = Form(...),
    tahun_ajaran: str = Form(...),
    db_session: Session = Depends(get_db)
):
    user = await auth.get_current_user(request, db_session)
    if not user:
         return RedirectResponse(url="/")
         
    db_semester = crud.get_semester(db_session, semester_id)
    if db_semester:
        db_semester.tipe = tipe
        db_semester.tahun_ajaran = tahun_ajaran
        db_session.commit()
        
        # Sync Calendar Name
        if db_semester.google_calendar_id:
            new_summary = f"My Campus - {tipe} {tahun_ajaran}"
            calendar_service.update_calendar_metadata(user, db_semester.google_calendar_id, new_summary)
            
    return RedirectResponse(url="/", status_code=303)

