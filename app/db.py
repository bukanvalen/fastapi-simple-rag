from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.close()

def create_hnsw_index():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS rags_embeddings_hnsw_idx
            ON rags_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m=16, ef_construction=200);
        """))
        conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()