from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from datetime import datetime, time
import logging
import traceback

from . import models, schemas, crud, db, rag

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
    ukm = crud.get_all_ukm(db_session)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "rags_embeddings": rags_embeddings,
            "users": users,
            "todos": todos,
            "jadwal_matkul": jadwal_matkul,
            "ukm": ukm
        }
    )


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
        await crud.create_user_embedding(db_session, db_user) # Create embedding for the new user
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
    db_session: Session = Depends(get_db)
):
    try:
        user_update_data = schemas.UserUpdate(
            nama=nama,
            email=email,
            telepon=telepon,
            bio=bio,
            lokasi=lokasi
        )
        db_user = crud.update_user(db_session, user_id, user_update_data)

        if db_user:
            # Re-generate and update user embedding if user data was changed
            user_data_text = f"Nama: {db_user.nama}. Email: {db_user.email}. Telepon: {db_user.telepon or ''}. Bio: {db_user.bio or ''}. Lokasi: {db_user.lokasi or ''}."
            embedding_list = await rag.embed_text_with_gemini(user_data_text)
            
            # Find and update the existing user embedding
            existing_embedding = db_session.query(models.RAGSEmbedding).filter_by(
                source_type="user", source_id=str(db_user.id_user)
            ).first()

            if existing_embedding:
                existing_embedding.text_original = user_data_text
                existing_embedding.embedding = embedding_list
                db_session.add(existing_embedding)
                db_session.commit()
            else:
                # If for some reason the embedding doesn't exist, create it
                crud.create_rags_embedding(db_session, schemas.RAGSEmbeddingCreate(
                    id_user=db_user.id_user,
                    source_type="user",
                    source_id=str(db_user.id_user),
                    text_original=user_data_text
                ), embedding_list)

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
        
        todo_text = f"Todo: {db_todo.nama}. Type: {db_todo.tipe}. Due: {db_todo.tenggat}. Description: {db_todo.deskripsi or ''}."
        embedding_list = await rag.embed_text_with_gemini(todo_text)
        
        embedding_create = schemas.RAGSEmbeddingCreate(
            id_user=id_user,
            source_type="todo",
            source_id=str(db_todo.id_todo),
            text_original=todo_text
        )
        crud.create_rags_embedding(db_session, embedding_create, embedding_list)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-todo/{todo_id}", response_class=RedirectResponse)
async def delete_todo_route(todo_id: int, db_session: Session = Depends(get_db)):
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
            # Re-generate and update embedding
            todo_text = f"Todo: {db_todo.nama}. Type: {db_todo.tipe}. Due: {db_todo.tenggat}. Description: {db_todo.deskripsi or ''}."
            embedding_list = await rag.embed_text_with_gemini(todo_text)
            
            existing_embedding = db_session.query(models.RAGSEmbedding).filter_by(
                source_type="todo", source_id=str(db_todo.id_todo)
            ).first()

            if existing_embedding:
                existing_embedding.text_original = todo_text
                existing_embedding.embedding = embedding_list
                db_session.add(existing_embedding)
                db_session.commit()
            else:
                crud.create_rags_embedding(db_session, schemas.RAGSEmbeddingCreate(
                    id_user=db_todo.id_user,
                    source_type="todo",
                    source_id=str(db_todo.id_todo),
                    text_original=todo_text
                ), embedding_list)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# --- JADWAL MATKUL Endpoints ---
@app.post("/add-jadwal", response_class=RedirectResponse)
async def add_jadwal(
    id_user: int = Form(...),
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
            hari=hari,
            nama=nama,
            jam_mulai=jam_mulai_time,
            jam_selesai=jam_selesai_time,
            sks=sks
        )
        db_jadwal = crud.create_jadwal_matkul(db_session, jadwal_create)
        
        jadwal_text = f"Jadwal Mata Kuliah: {db_jadwal.nama}. Hari: {db_jadwal.hari}. Mulai: {db_jadwal.jam_mulai}. Selesai: {db_jadwal.jam_selesai}. SKS: {db_jadwal.sks}."
        embedding_list = await rag.embed_text_with_gemini(jadwal_text)
        
        embedding_create = schemas.RAGSEmbeddingCreate(
            id_user=id_user,
            source_type="jadwal",
            source_id=str(db_jadwal.id_jadwal),
            text_original=jadwal_text
        )
        crud.create_rags_embedding(db_session, embedding_create, embedding_list)
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-jadwal/{jadwal_id}", response_class=RedirectResponse)
async def delete_jadwal_route(jadwal_id: int, db_session: Session = Depends(get_db)):
    crud.delete_jadwal_matkul(db_session, jadwal_id)
    crud.delete_rags_embedding_by_source_type_and_id(db_session, "jadwal", str(jadwal_id))
    return RedirectResponse(url="/", status_code=303)

@app.post("/update-jadwal/{jadwal_id}", response_class=RedirectResponse)
async def update_jadwal_route(
    jadwal_id: int,
    id_user: Optional[int] = Form(None),
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
            hari=hari,
            nama=nama,
            jam_mulai=jam_mulai_time,
            jam_selesai=jam_selesai_time,
            sks=sks
        )
        db_jadwal = crud.update_jadwal_matkul(db_session, jadwal_id, jadwal_update_data)

        if db_jadwal:
            # Re-generate and update embedding
            jadwal_text = f"Jadwal Mata Kuliah: {db_jadwal.nama}. Hari: {db_jadwal.hari}. Mulai: {db_jadwal.jam_mulai}. Selesai: {db_jadwal.jam_selesai}. SKS: {db_jadwal.sks}."
            embedding_list = await rag.embed_text_with_gemini(jadwal_text)
            
            existing_embedding = db_session.query(models.RAGSEmbedding).filter_by(
                source_type="jadwal", source_id=str(db_jadwal.id_jadwal)
            ).first()

            if existing_embedding:
                existing_embedding.text_original = jadwal_text
                existing_embedding.embedding = embedding_list
                db_session.add(existing_embedding)
                db_session.commit()
            else:
                crud.create_rags_embedding(db_session, schemas.RAGSEmbeddingCreate(
                    id_user=db_jadwal.id_user,
                    source_type="jadwal",
                    source_id=str(db_jadwal.id_jadwal),
                    text_original=jadwal_text
                ), embedding_list)

        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        logger.error(f"Error in endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# --- UKM Endpoints ---
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
        
        ukm_text = f"UKM: {db_ukm.nama}. Jabatan: {db_ukm.jabatan}. Description: {db_ukm.deskripsi or ''}."
        embedding_list = await rag.embed_text_with_gemini(ukm_text)
        
        embedding_create = schemas.RAGSEmbeddingCreate(
            id_user=id_user,
            source_type="ukm",
            source_id=str(db_ukm.id_ukm),
            text_original=ukm_text
        )
        crud.create_rags_embedding(db_session, embedding_create, embedding_list)
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
            # Re-generate and update embedding
            ukm_text = f"UKM: {db_ukm.nama}. Jabatan: {db_ukm.jabatan}. Description: {db_ukm.deskripsi or ''}."
            embedding_list = await rag.embed_text_with_gemini(ukm_text)
            
            existing_embedding = db_session.query(models.RAGSEmbedding).filter_by(
                source_type="ukm", source_id=str(db_ukm.id_ukm)
            ).first()

            if existing_embedding:
                existing_embedding.text_original = ukm_text
                existing_embedding.embedding = embedding_list
                db_session.add(existing_embedding)
                db_session.commit()
            else:
                crud.create_rags_embedding(db_session, schemas.RAGSEmbeddingCreate(
                    id_user=db_ukm.id_user,
                    source_type="ukm",
                    source_id=str(db_ukm.id_ukm),
                    text_original=ukm_text
                ), embedding_list)

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
@app.post("/calendar/create-event")
async def create_calendar_event(event: schemas.CalendarEventCreate):
    """
    Handles the creation of a Google Calendar event.

    TODO:
    1. Authenticate with Google Calendar API.
       - This typically involves setting up OAuth 2.0 credentials in the Google Cloud Console.
       - You might need to store refresh tokens securely and use them to obtain access tokens.
       - Libraries like `google-auth-oauthlib` and `google-api-python-client` can assist.
    2. Construct the event body using the 'event' data.
       - Ensure `start_time` and `end_time` are in the correct format (e.g., RFC3339).
    3. Call the Google Calendar API to insert the event.
    4. Handle potential API errors (e.g., authentication failure, invalid event data).
    5. Return an appropriate response, including the event ID if successful.
    """
    # Placeholder for future implementation
    # Example using google-api-python-client (requires installation and setup):
    # from google.oauth2.credentials import Credentials
    # from googleapiclient.discovery import build

    # creds = ... # Load or refresh credentials
    # service = build('calendar', 'v3', credentials=creds)

    # event_body = {
    #     'summary': event.summary,
    #     'description': event.description,
    #     'start': {'dateTime': event.start_time.isoformat(), 'timeZone': 'UTC'}, # Adjust timezone as needed
    #     'end': {'dateTime': event.end_time.isoformat(), 'timeZone': 'UTC'},     # Adjust timezone as needed
    # }

    # try:
    #     created_event = service.events().insert(calendarId='primary', body=event_body).execute()
    #     return {"message": "Calendar event created successfully", "event_id": created_event.get('id')}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Failed to create calendar event: {e}")
    
    return {"message": "Calendar event creation not yet implemented. Please refer to the code for integration instructions."}

